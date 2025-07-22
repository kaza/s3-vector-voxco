using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Threading.Tasks;
using Amazon;
using Amazon.Runtime.Documents;
using Amazon.S3Vectors;
using Amazon.S3Vectors.Model;
using Microsoft.Extensions.Logging;

namespace S3VectorsExample
{
    public class S3VectorsClient
    {
        private readonly IAmazonS3Vectors _client;
        private readonly ILogger<S3VectorsClient> _logger;
        private readonly string _bucketName;
        private readonly string _indexName;

        public S3VectorsClient(string bucketName, string indexName, RegionEndpoint region, ILogger<S3VectorsClient> logger)
            : this(bucketName, indexName, new AmazonS3VectorsClient(region), logger)
        {
        }

        // Constructor for testing with mock client
        public S3VectorsClient(string bucketName, string indexName, IAmazonS3Vectors client, ILogger<S3VectorsClient> logger)
        {
            _bucketName = bucketName;
            _indexName = indexName;
            _client = client;
            _logger = logger;
        }

        public async Task<bool> CreateVectorBucketAsync()
        {
            try
            {
                var request = new CreateVectorBucketRequest
                {
                    VectorBucketName = _bucketName
                };

                var response = await _client.CreateVectorBucketAsync(request);
                _logger.LogInformation($"Created vector bucket: {_bucketName}");
                return response.HttpStatusCode == HttpStatusCode.OK;
            }
            catch (ConflictException ex) when (ex.Message.Contains("already exists"))
            {
                _logger.LogInformation($"Vector bucket already exists: {_bucketName}");
                return true;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Failed to create vector bucket: {_bucketName}");
                throw;
            }
        }

        public async Task<bool> CreateIndexAsync(int dimension, string distanceMetric = "COSINE")
        {
            try
            {
                var request = new CreateIndexRequest
                {
                    VectorBucketName = _bucketName,
                    IndexName = _indexName,
                    Dimension = dimension,
                    DistanceMetric = distanceMetric,
                    DataType = "FLOAT32"
                };

                var response = await _client.CreateIndexAsync(request);
                _logger.LogInformation($"Created index: {_indexName} with dimension {dimension}");
                return response.HttpStatusCode == HttpStatusCode.OK;
            }
            catch (ConflictException ex) when (ex.Message.Contains("already exists"))
            {
                _logger.LogInformation($"Index already exists: {_indexName}");
                return true;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Failed to create index: {_indexName}");
                throw;
            }
        }

        public async Task<int> BulkInsertAsync(List<VectorDocument> documents)
        {
            if (documents == null || documents.Count == 0)
            {
                _logger.LogWarning("No documents to insert");
                return 0;
            }

            int totalInserted = 0;
            const int batchSize = 500; // S3 Vectors batch limit

            // Process in batches
            for (int i = 0; i < documents.Count; i += batchSize)
            {
                var batch = documents.Skip(i).Take(batchSize).ToList();
                
                try
                {
                    var vectors = batch.Select(doc => new PutInputVector
                    {
                        Key = doc.Key,
                        Data = new VectorData { Float32 = doc.Embedding },
                        Metadata = DocumentHelper.ConvertToDocument(doc.Metadata)
                    }).ToList();

                    var request = new PutVectorsRequest
                    {
                        VectorBucketName = _bucketName,
                        IndexName = _indexName,
                        Vectors = vectors
                    };

                    var response = await _client.PutVectorsAsync(request);
                    totalInserted += batch.Count;
                    
                    _logger.LogInformation($"Inserted batch of {batch.Count} vectors");
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, $"Failed to insert batch starting at index {i}");
                    throw;
                }
            }

            return totalInserted;
        }

        public async Task<List<VectorDocument>> BulkSelectAsync(List<string> keys, bool returnData = true, bool returnMetadata = true)
        {
            if (keys == null || keys.Count == 0)
            {
                _logger.LogWarning("No keys provided for selection");
                return new List<VectorDocument>();
            }

            var allResults = new List<VectorDocument>();
            const int batchSize = 100; // S3 Vectors batch limit for select

            // Process in batches
            for (int i = 0; i < keys.Count; i += batchSize)
            {
                var batch = keys.Skip(i).Take(batchSize).ToList();
                
                try
                {
                    var request = new GetVectorsRequest
                    {
                        VectorBucketName = _bucketName,
                        IndexName = _indexName,
                        Keys = batch,
                        ReturnData = returnData,
                        ReturnMetadata = returnMetadata
                    };

                    var response = await _client.GetVectorsAsync(request);
                    
                    foreach (var vector in response.Vectors)
                    {
                        allResults.Add(new VectorDocument
                        {
                            Key = vector.Key,
                            Embedding = vector.Data?.Float32,
                            Metadata = DocumentHelper.ConvertFromDocument(vector.Metadata)
                        });
                    }
                    
                    _logger.LogInformation($"Retrieved batch of {response.Vectors.Count} vectors");
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, $"Failed to retrieve batch starting at index {i}");
                    throw;
                }
            }

            return allResults;
        }

        public async Task<List<SearchResult>> GetNeighboursAsync(List<float> queryVector, int topK = 10, Dictionary<string, object>? filter = null)
        {
            try
            {
                var request = new QueryVectorsRequest
                {
                    VectorBucketName = _bucketName,
                    IndexName = _indexName,
                    QueryVector = new VectorData { Float32 = queryVector },
                    TopK = topK,
                    ReturnDistance = true,
                    ReturnMetadata = true
                };

                if (filter != null && filter.Count > 0)
                {
                    request.Filter = DocumentHelper.ConvertToDocument(filter);
                }

                var response = await _client.QueryVectorsAsync(request);
                
                var results = response.Vectors.Select(v => new SearchResult
                {
                    Key = v.Key,
                    Distance = v.Distance ?? 0,
                    Metadata = DocumentHelper.ConvertFromDocument(v.Metadata)
                }).ToList();

                _logger.LogInformation($"Found {results.Count} similar vectors");
                return results ?? new List<SearchResult>();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to search for similar vectors");
                throw;
            }
        }

        public async Task<int> BulkDeleteAsync(List<string> keys)
        {
            if (keys == null || keys.Count == 0)
            {
                _logger.LogWarning("No keys provided for deletion");
                return 0;
            }

            int totalDeleted = 0;
            const int batchSize = 500; // S3 Vectors batch limit

            // Process in batches
            for (int i = 0; i < keys.Count; i += batchSize)
            {
                var batch = keys.Skip(i).Take(batchSize).ToList();
                
                try
                {
                    var request = new DeleteVectorsRequest
                    {
                        VectorBucketName = _bucketName,
                        IndexName = _indexName,
                        Keys = batch
                    };

                    var response = await _client.DeleteVectorsAsync(request);
                    totalDeleted += batch.Count;
                    
                    _logger.LogInformation($"Deleted batch of {batch.Count} vectors");
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, $"Failed to delete batch starting at index {i}");
                    throw;
                }
            }

            return totalDeleted;
        }
    }

    // Data models
    public class VectorDocument
    {
        public required string Key { get; set; }
        public List<float>? Embedding { get; set; }
        public Dictionary<string, object>? Metadata { get; set; }
    }

    public class SearchResult
    {
        public required string Key { get; set; }
        public float Distance { get; set; }
        public Dictionary<string, object>? Metadata { get; set; }
    }

    // Helper methods for Document conversion
    internal static class DocumentHelper
    {
        public static Document ConvertToDocument(Dictionary<string, object>? dict)
        {
            if (dict == null || dict.Count == 0) return new Document();
            
            var doc = new Document();
            foreach (var kvp in dict)
            {
                doc.Add(kvp.Key, kvp.Value switch
                {
                    string s => s,
                    int i => i,
                    long l => l,
                    float f => f,
                    double d => d,
                    bool b => b,
                    _ => kvp.Value?.ToString() ?? ""
                });
            }
            return doc;
        }

        public static Dictionary<string, object>? ConvertFromDocument(Document? doc)
        {
            if (doc == null) return null;
            
            // For now, return an empty dictionary since Document doesn't expose its contents
            // In a real implementation, you would use reflection or wait for SDK updates
            return new Dictionary<string, object>();
        }
    }
}