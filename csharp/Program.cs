using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Amazon;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace S3VectorsExample
{
    class Program
    {
        static async Task Main(string[] args)
        {
            // Set up configuration
            var configuration = new ConfigurationBuilder()
                .AddEnvironmentVariables()
                .Build();

            // Set up dependency injection and logging
            var serviceProvider = new ServiceCollection()
                .AddLogging(builder =>
                {
                    builder.AddConsole();
                    builder.SetMinimumLevel(LogLevel.Information);
                })
                .AddSingleton<IConfiguration>(configuration)
                .BuildServiceProvider();

            var logger = serviceProvider.GetRequiredService<ILogger<Program>>();

            try
            {
                // Configuration
                const string bucketName = "hello-vectors-csharp";
                const string indexName = "hello-index";
                const int dimension = 128;
                var region = RegionEndpoint.USWest2; // Use one of the preview regions

                logger.LogInformation("=== S3 Vectors C# Example ===");
                
                // Create client
                var clientLogger = serviceProvider.GetRequiredService<ILogger<S3VectorsClient>>();
                var client = new S3VectorsClient(bucketName, indexName, region, clientLogger);

                // Step 1: Create vector bucket
                logger.LogInformation("Step 1: Creating vector bucket...");
                await client.CreateVectorBucketAsync();

                // Step 2: Create index
                logger.LogInformation("Step 2: Creating vector index...");
                await client.CreateIndexAsync(dimension);

                // Step 3: Generate and insert sample vectors
                logger.LogInformation("Step 3: Generating and inserting sample vectors...");
                var documents = GenerateSampleVectors(10, dimension);
                var insertedCount = await client.BulkInsertAsync(documents);
                logger.LogInformation($"Inserted {insertedCount} vectors");

                // Step 4: Retrieve vectors by keys
                logger.LogInformation("\nStep 4: Retrieving vectors by keys...");
                var keysToRetrieve = new List<string> { "vector_0", "vector_1", "vector_2" };
                var retrievedDocs = await client.BulkSelectAsync(keysToRetrieve);
                
                foreach (var doc in retrievedDocs)
                {
                    logger.LogInformation($"Retrieved: {doc.Key} - Metadata: {string.Join(", ", doc.Metadata?.Select(kv => $"{kv.Key}={kv.Value}") ?? new string[0])}");
                }

                // Step 5: Search for similar vectors
                logger.LogInformation("\nStep 5: Searching for similar vectors...");
                var queryVector = documents[0].Embedding!; // Use first vector as query
                var searchResults = await client.GetNeighboursAsync(queryVector, topK: 5);
                
                logger.LogInformation("Search results:");
                foreach (var result in searchResults.OrderBy(r => r.Distance))
                {
                    logger.LogInformation($"  Key: {result.Key}, Distance: {result.Distance:F4}");
                }

                // Step 6: Demonstrate batch processing
                logger.LogInformation("\nStep 6: Demonstrating batch processing...");
                var largeBatch = GenerateSampleVectors(1500, dimension); // More than batch limit
                var batchInsertedCount = await client.BulkInsertAsync(largeBatch);
                logger.LogInformation($"Successfully inserted {batchInsertedCount} vectors in batches");

                // Step 7: Clean up - delete all vectors
                logger.LogInformation("\nStep 7: Cleaning up...");
                var allKeys = documents.Concat(largeBatch).Select(d => d.Key).ToList();
                var deletedCount = await client.BulkDeleteAsync(allKeys);
                logger.LogInformation($"Deleted {deletedCount} vectors");

                logger.LogInformation("\n=== Example completed successfully! ===");
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "An error occurred during the example");
                Environment.Exit(1);
            }
        }

        private static List<VectorDocument> GenerateSampleVectors(int count, int dimension)
        {
            var random = new Random(42); // Fixed seed for reproducibility
            var documents = new List<VectorDocument>();

            for (int i = 0; i < count; i++)
            {
                // Generate random normalized vector
                var vector = new List<float>();
                float magnitude = 0;
                
                for (int j = 0; j < dimension; j++)
                {
                    var value = (float)(random.NextDouble() * 2 - 1); // Random between -1 and 1
                    vector.Add(value);
                    magnitude += value * value;
                }

                // Normalize the vector
                magnitude = (float)Math.Sqrt(magnitude);
                for (int j = 0; j < dimension; j++)
                {
                    vector[j] /= magnitude;
                }

                documents.Add(new VectorDocument
                {
                    Key = $"vector_{i}",
                    Embedding = vector,
                    Metadata = new Dictionary<string, object>
                    {
                        { "id", i.ToString() },
                        { "type", "sample" },
                        { "category", i % 3 == 0 ? "A" : i % 3 == 1 ? "B" : "C" },
                        { "created", DateTime.UtcNow.ToString("yyyy-MM-dd") }
                    }
                });
            }

            return documents;
        }
    }
}