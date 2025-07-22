# S3 Vectors C#/.NET Implementation

This directory contains a C#/.NET Core implementation for Amazon S3 Vectors using the official `AWSSDK.S3Vectors` NuGet package (version 4.0.0).

## Prerequisites

- .NET 8.0 SDK or later
- AWS Account with access to S3 Vectors (available in preview regions)
- AWS credentials configured (via AWS CLI, environment variables, or IAM role)

## Setup

1. **Install .NET SDK** (if not already installed):
   - Download from [https://dotnet.microsoft.com/download](https://dotnet.microsoft.com/download)

2. **Configure AWS Credentials**:
   ```bash
   # Using AWS CLI
   aws configure

   # Or using environment variables
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_REGION=us-west-2
   ```

3. **Restore NuGet packages**:
   ```bash
   cd csharp
   dotnet restore
   ```

## Project Structure

```
csharp/
├── S3VectorsExample.csproj      # Main project file
├── S3VectorsClient.cs          # S3 Vectors client wrapper
├── Program.cs                  # Example usage program
├── S3VectorsExample.Tests.csproj # Test project
├── S3VectorsClientTests.cs    # Unit tests
└── README.md                   # This file
```

## Running the Example

```bash
# From the csharp directory
dotnet run
```

The example program demonstrates:
1. Creating a vector bucket
2. Creating a vector index with 128 dimensions
3. Inserting sample vectors with metadata
4. Retrieving vectors by keys
5. Searching for similar vectors
6. Batch processing (handling more than 500/100 item limits)
7. Deleting vectors

## Using the S3VectorsClient

### Basic Usage

```csharp
using Amazon;
using Microsoft.Extensions.Logging;

// Create client
var logger = // ... get ILogger<S3VectorsClient>
var client = new S3VectorsClient("my-bucket", "my-index", RegionEndpoint.USWest2, logger);

// Create bucket and index
await client.CreateVectorBucketAsync();
await client.CreateIndexAsync(dimension: 1536, distanceMetric: "COSINE");

// Insert vectors
var documents = new List<VectorDocument>
{
    new VectorDocument
    {
        Key = "doc1",
        Embedding = new List<float> { /* 1536 dimensions */ },
        Metadata = new Dictionary<string, object>
        {
            { "title", "Document 1" },
            { "category", "A" }
        }
    }
};
await client.BulkInsertAsync(documents);

// Search for similar vectors
var queryVector = new List<float> { /* 1536 dimensions */ };
var results = await client.GetNeighboursAsync(queryVector, topK: 10);

foreach (var result in results)
{
    Console.WriteLine($"Key: {result.Key}, Distance: {result.Distance}");
}
```

### Batch Processing

The client automatically handles S3 Vectors batch limits:
- **Insert/Delete**: Maximum 500 items per request
- **Select**: Maximum 100 items per request

```csharp
// Insert 1500 vectors - automatically split into 3 batches
var largeDocumentSet = GenerateManyDocuments(1500);
await client.BulkInsertAsync(largeDocumentSet);

// Retrieve 250 vectors - automatically split into 3 batches
var manyKeys = Enumerable.Range(0, 250).Select(i => $"vector_{i}").ToList();
var retrieved = await client.BulkSelectAsync(manyKeys);
```

## Running Tests

```bash
# From the csharp directory
dotnet test
```

## Key Features

1. **Automatic Batch Processing**: Handles S3 Vectors batch limits transparently
2. **Comprehensive Logging**: Uses Microsoft.Extensions.Logging for detailed operation logs
3. **Error Handling**: Graceful handling of common errors (bucket/index already exists)
4. **Type Safety**: Strongly typed models for vectors and metadata
5. **Async/Await**: All operations are asynchronous for better performance

## Cost Considerations

- **Storage**: $0.04/GB/month
- **Queries**: $0.0004 per 1K queries
- **Write Operations**: Rate limited to 5+ requests/second per index

For detailed pricing, see the [AWS S3 Vectors pricing page](https://aws.amazon.com/s3/pricing/).

## Supported Regions (Preview)

S3 Vectors is currently available in:
- US East (N. Virginia) - us-east-1
- US East (Ohio) - us-east-2
- US West (Oregon) - us-west-2
- Europe (Frankfurt) - eu-central-1
- Asia Pacific (Sydney) - ap-southeast-2

## Dependencies

- `AWSSDK.S3Vectors` (4.0.0) - Official AWS SDK for S3 Vectors
- `Microsoft.Extensions.Configuration` - Configuration management
- `Microsoft.Extensions.Logging` - Logging infrastructure
- `Microsoft.Extensions.DependencyInjection` - Dependency injection

## Troubleshooting

1. **Authentication Errors**: Ensure AWS credentials are properly configured
2. **Region Errors**: Make sure you're using one of the preview regions
3. **Rate Limiting**: Implement exponential backoff for production use
4. **Dimension Mismatch**: Ensure all vectors match the index dimension

## Next Steps

1. Integrate with your embedding model (e.g., Amazon Bedrock, OpenAI)
2. Implement exponential backoff for production workloads
3. Add metrics and monitoring
4. Consider hybrid search with OpenSearch for latency-critical applications

## References

- [Amazon S3 Vectors Documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-getting-started.html)
- [AWS SDK for .NET Documentation](https://docs.aws.amazon.com/sdk-for-net/v3/developer-guide/)
- [S3 Vectors Announcement Blog](https://aws.amazon.com/blogs/aws/introducing-amazon-s3-vectors-first-cloud-storage-with-native-vector-support-at-scale/)