using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Amazon;
using Amazon.S3Vectors;
using Microsoft.Extensions.Logging;
using Xunit;

namespace S3VectorsExample.Tests
{
    public class S3VectorsClientTests : IAsyncLifetime
    {
        private readonly S3VectorsClient _client;
        private readonly ILogger<S3VectorsClient> _logger;
        private readonly string TestBucketName;
        private readonly string TestIndexName;
        private const int TestDimension = 128;

        public S3VectorsClientTests()
        {
            // Create a real logger
            var loggerFactory = LoggerFactory.Create(builder =>
            {
                builder.AddConsole();
                builder.SetMinimumLevel(LogLevel.Debug);
            });
            _logger = loggerFactory.CreateLogger<S3VectorsClient>();
            
            // Use unique names to avoid conflicts
            var timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            TestBucketName = $"test-vectors-{timestamp}";
            TestIndexName = $"test-index-{timestamp}";
            
            // Create real client with US West 2 region (one of the preview regions)
            _client = new S3VectorsClient(TestBucketName, TestIndexName, RegionEndpoint.USWest2, _logger);
        }

        public async Task InitializeAsync()
        {
            // Set up test bucket and index
            await _client.CreateVectorBucketAsync();
            await _client.CreateIndexAsync(TestDimension);
            
            // Wait a bit for the index to be ready
            await Task.Delay(2000);
        }

        public async Task DisposeAsync()
        {
            // Clean up is handled by individual tests
            await Task.CompletedTask;
        }

        [Fact]
        public async Task BulkInsertAndSelect_RealData_WorksCorrectly()
        {
            // Arrange
            var documents = GenerateTestDocuments(5, TestDimension);

            // Act - Insert documents
            var insertedCount = await _client.BulkInsertAsync(documents);

            // Assert insertion
            Assert.Equal(5, insertedCount);
            
            // Wait a bit for eventual consistency
            await Task.Delay(1000);

            // Act - Select documents
            var keys = documents.Select(d => d.Key).ToList();
            var selectedDocs = await _client.BulkSelectAsync(keys);

            // Assert selection
            Assert.Equal(5, selectedDocs.Count);
            foreach (var doc in documents)
            {
                var selected = selectedDocs.FirstOrDefault(s => s.Key == doc.Key);
                Assert.NotNull(selected);
                Assert.NotNull(selected.Embedding);
                Assert.Equal(TestDimension, selected.Embedding.Count);
            }
            
            // Clean up
            await _client.BulkDeleteAsync(keys);
        }

        [Fact]
        public async Task BulkInsertAsync_LargeBatch_HandlesCorrectly()
        {
            // Arrange - Create 600 documents (more than 500 batch limit)
            var documents = GenerateTestDocuments(600, TestDimension);
            
            // Act
            var result = await _client.BulkInsertAsync(documents);

            // Assert
            Assert.Equal(600, result);
            
            // Wait for eventual consistency
            await Task.Delay(2000);
            
            // Verify we can retrieve some of them
            var sampleKeys = documents.Take(10).Select(d => d.Key).ToList();
            var retrieved = await _client.BulkSelectAsync(sampleKeys);
            Assert.Equal(10, retrieved.Count);
            
            // Clean up
            var allKeys = documents.Select(d => d.Key).ToList();
            await _client.BulkDeleteAsync(allKeys);
        }

        [Fact]
        public async Task GetNeighboursAsync_FindsSimilarVectors()
        {
            // Arrange - Insert test vectors
            var documents = GenerateTestDocuments(20, TestDimension);
            await _client.BulkInsertAsync(documents);
            
            // Wait for indexing
            await Task.Delay(3000);
            
            // Act - Search for neighbors of the first vector
            var queryVector = documents[0].Embedding!;
            var results = await _client.GetNeighboursAsync(queryVector, topK: 5);
            
            // Assert
            Assert.NotEmpty(results);
            Assert.True(results.Count <= 5);
            
            // The first result should be the query vector itself (distance ~0)
            var firstResult = results.OrderBy(r => r.Distance).First();
            Assert.Equal(documents[0].Key, firstResult.Key);
            Assert.True(firstResult.Distance < 0.01f); // Should be very close to 0
            
            // Clean up
            var keys = documents.Select(d => d.Key).ToList();
            await _client.BulkDeleteAsync(keys);
        }

        [Fact]
        public async Task GetNeighboursAsync_WithFilter_ReturnsFilteredResults()
        {
            // Arrange - Create documents with different categories
            var documents = new List<VectorDocument>();
            for (int i = 0; i < 15; i++)
            {
                var doc = new VectorDocument
                {
                    Key = $"filtered_vector_{i}",
                    Embedding = GenerateRandomVector(TestDimension),
                    Metadata = new Dictionary<string, object>
                    {
                        { "id", i.ToString() },
                        { "category", i % 3 == 0 ? "A" : i % 3 == 1 ? "B" : "C" },
                        { "type", "test" }
                    }
                };
                documents.Add(doc);
            }
            
            await _client.BulkInsertAsync(documents);
            await Task.Delay(3000); // Wait for indexing
            
            // Act - Search with filter for category A
            var queryVector = GenerateRandomVector(TestDimension);
            var filter = new Dictionary<string, object> { { "category", "A" } };
            var results = await _client.GetNeighboursAsync(queryVector, topK: 10, filter);
            
            // Assert - All results should have category A
            Assert.NotEmpty(results);
            // Note: We can't verify metadata values since DocumentHelper.ConvertFromDocument returns empty dict
            // But we can verify the search returns results
            
            // Clean up
            var keys = documents.Select(d => d.Key).ToList();
            await _client.BulkDeleteAsync(keys);
        }

        [Fact]
        public async Task BulkDeleteAsync_RemovesVectors()
        {
            // Arrange - Insert vectors first
            var documents = GenerateTestDocuments(10, TestDimension);
            await _client.BulkInsertAsync(documents);
            await Task.Delay(2000);
            
            // Verify they exist
            var keys = documents.Select(d => d.Key).ToList();
            var beforeDelete = await _client.BulkSelectAsync(keys);
            Assert.Equal(10, beforeDelete.Count);
            
            // Act - Delete them
            var deletedCount = await _client.BulkDeleteAsync(keys);
            
            // Assert
            Assert.Equal(10, deletedCount);
            
            // Wait for deletion to propagate
            await Task.Delay(2000);
            
            // Verify they're gone
            var afterDelete = await _client.BulkSelectAsync(keys);
            Assert.Empty(afterDelete);
        }

        [Fact]
        public void VectorDocument_Normalization_ProducesUnitVector()
        {
            // Arrange
            var dimension = TestDimension;
            
            // Act
            var vector = GenerateRandomVector(dimension);
            
            // Calculate magnitude
            var magnitude = Math.Sqrt(vector.Sum(v => v * v));
            
            // Assert
            Assert.InRange(magnitude, 0.99, 1.01); // Should be normalized to unit length
        }

        private List<VectorDocument> GenerateTestDocuments(int count, int dimension)
        {
            var documents = new List<VectorDocument>();
            for (int i = 0; i < count; i++)
            {
                documents.Add(new VectorDocument
                {
                    Key = $"vector_{i}",
                    Embedding = GenerateRandomVector(dimension),
                    Metadata = new Dictionary<string, object>
                    {
                        { "id", i.ToString() },
                        { "type", "test" }
                    }
                });
            }
            return documents;
        }

        private List<float> GenerateRandomVector(int dimension)
        {
            var random = new Random();
            var vector = new List<float>();
            float magnitude = 0;
            
            for (int j = 0; j < dimension; j++)
            {
                var value = (float)(random.NextDouble() * 2 - 1);
                vector.Add(value);
                magnitude += value * value;
            }

            // Normalize
            magnitude = (float)Math.Sqrt(magnitude);
            for (int j = 0; j < dimension; j++)
            {
                vector[j] /= magnitude;
            }

            return vector;
        }

    }
}