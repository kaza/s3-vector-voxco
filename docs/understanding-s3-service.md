# Amazon S3 Vectors: Understanding the service and implementing bulk operations

Amazon S3 Vectors, announced in July 2025, introduces native vector storage to S3 with up to 90% cost reduction compared to traditional vector databases. The service provides dedicated vector buckets and indexes optimized for storing and querying embeddings at scale, making it ideal for RAG applications, semantic search, and AI agent memory systems.

## How S3 Vectors works: Architecture and key concepts

S3 Vectors operates differently from standard S3, using a dedicated namespace (`s3vectors`) and specialized APIs. Data is organized in **vector buckets** containing up to 10,000 **vector indexes**, with each index supporting 50 million vectors of fixed dimensionality (1-4,096 dimensions). Unlike regular S3 objects, vectors are accessed through purpose-built APIs optimized for similarity search operations.

**Important note about primary keys**: S3 Vectors uses **string keys** rather than integers. While your requirement mentions integer primary keys (1, 2, 3), you'll need to convert these to strings ("1", "2", "3") when working with the S3 Vectors API. Each vector is identified by a unique string key within its index, along with the vector data and optional metadata.

The service guarantees **strong consistency** - vectors are immediately accessible after writes - and provides sub-second query performance (typically hundreds of milliseconds). It automatically optimizes vector data storage for cost-performance balance, making it suitable for applications where cost matters more than ultra-low latency.

## API operations and SDK setup

S3 Vectors provides five core operations through the AWS SDK:
- **PutVectors**: Insert/update up to 500 vectors per call
- **GetVectors**: Retrieve up to 100 vectors by key
- **DeleteVectors**: Remove up to 500 vectors by key
- **QueryVectors**: Find up to 30 nearest neighbors
- **ListVectors**: Paginate through all vectors in an index

To get started, initialize the S3 Vectors client:

```python
import boto3
from botocore.exceptions import ClientError

# Initialize S3 Vectors client
s3vectors = boto3.client('s3vectors', region_name='us-east-1')

# Create a vector bucket and index (one-time setup)
bucket_name = 'my-vector-storage'
index_name = 'embeddings-index'

# Note: Vector bucket creation is done through standard S3 console/API
# with vectorStore configuration enabled
```

## Operation 1: bulk_insert - Insert vectors with primary keys

The `bulk_insert` operation uses the PutVectors API to insert multiple vectors with their embeddings and metadata. Since S3 Vectors requires string keys, convert integer primary keys to strings:

```python
def bulk_insert(s3vectors_client, bucket_name, index_name, items):
    """
    Insert multiple items with primary keys and vector embeddings.
    
    Args:
        items: List of dicts with 'id' (int), 'embedding' (float[]), 
               and optional 'metadata' (dict)
    
    Returns:
        dict: Summary of insertion results
    """
    results = {'success': 0, 'failed': 0, 'errors': []}
    
    # Process in batches of 500 (API limit)
    batch_size = 500
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        try:
            # Convert items to S3 Vectors format
            vectors = []
            for item in batch:
                # Convert integer ID to string key
                vector = {
                    'key': str(item['id']),
                    'data': {'float32': item['embedding']},
                }
                # Add metadata if provided
                if 'metadata' in item:
                    vector['metadata'] = item['metadata']
                    
                vectors.append(vector)
            
            # Insert batch
            response = s3vectors_client.put_vectors(
                vectorBucketName=bucket_name,
                indexName=index_name,
                vectors=vectors
            )
            
            results['success'] += len(vectors)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            results['failed'] += len(batch)
            results['errors'].append({
                'batch_start': i,
                'error': error_code,
                'message': str(e)
            })
            
            # Handle specific errors
            if error_code == 'TooManyRequestsException':
                # Implement exponential backoff
                import time
                time.sleep(2 ** len(results['errors']))
    
    return results

# Usage example
items = [
    {
        'id': 1,
        'embedding': [0.1, 0.2, 0.3] * 341,  # 1023-dimensional vector
        'metadata': {'type': 'document', 'category': 'technical'}
    },
    {
        'id': 2,
        'embedding': [0.4, 0.5, 0.6] * 341,
        'metadata': {'type': 'document', 'category': 'general'}
    },
    # ... more items
]

result = bulk_insert(s3vectors, bucket_name, index_name, items)
print(f"Inserted: {result['success']}, Failed: {result['failed']}")
```

## Operation 2: bulk_select - Retrieve vectors by primary keys

The `bulk_select` operation retrieves multiple vectors using their integer primary keys (converted to strings):

```python
def bulk_select(s3vectors_client, bucket_name, index_name, ids):
    """
    Retrieve multiple items by their primary key integers.
    
    Args:
        ids: List of integers representing primary keys
    
    Returns:
        dict: Mapping of id -> {'embedding': float[], 'metadata': dict}
    """
    results = {}
    not_found = []
    
    # Convert integer IDs to string keys
    keys = [str(id) for id in ids]
    
    # Process in batches of 100 (API limit)
    batch_size = 100
    
    for i in range(0, len(keys), batch_size):
        batch_keys = keys[i:i + batch_size]
        batch_ids = ids[i:i + batch_size]
        
        try:
            response = s3vectors_client.get_vectors(
                vectorBucketName=bucket_name,
                indexName=index_name,
                keys=batch_keys
            )
            
            # Map results back to integer IDs
            returned_keys = {v['key'] for v in response.get('vectors', [])}
            
            for vector in response.get('vectors', []):
                id_int = int(vector['key'])
                results[id_int] = {
                    'embedding': vector['data']['float32'],
                    'metadata': vector.get('metadata', {}),
                    'timestamp': vector.get('lastModified')
                }
            
            # Track missing vectors
            for key, id_int in zip(batch_keys, batch_ids):
                if key not in returned_keys:
                    not_found.append(id_int)
                    
        except ClientError as e:
            print(f"Error retrieving batch starting at index {i}: {e}")
            # Could implement retry logic here
    
    if not_found:
        print(f"Vectors not found for IDs: {not_found}")
    
    return results

# Usage example
ids_to_retrieve = [1, 2, 3, 100, 200]
vectors = bulk_select(s3vectors, bucket_name, index_name, ids_to_retrieve)

for id, data in vectors.items():
    print(f"ID {id}: {len(data['embedding'])} dimensions, metadata: {data['metadata']}")
```

## Operation 3: bulk_delete - Remove vectors by primary keys

The `bulk_delete` operation removes vectors using their integer identifiers:

```python
def bulk_delete(s3vectors_client, bucket_name, index_name, ids):
    """
    Delete multiple items by their primary key integers.
    
    Args:
        ids: List of integers representing primary keys to delete
    
    Returns:
        dict: Summary of deletion results
    """
    results = {
        'deleted': 0,
        'failed': 0,
        'errors': []
    }
    
    # Convert integer IDs to string keys
    keys = [str(id) for id in ids]
    
    # Process in batches of 500 (API limit)
    batch_size = 500
    
    for i in range(0, len(keys), batch_size):
        batch_keys = keys[i:i + batch_size]
        
        try:
            response = s3vectors_client.delete_vectors(
                vectorBucketName=bucket_name,
                indexName=index_name,
                keys=batch_keys
            )
            
            results['deleted'] += len(batch_keys)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            results['failed'] += len(batch_keys)
            results['errors'].append({
                'batch_start': i,
                'batch_ids': ids[i:i + batch_size],
                'error': error_code
            })
            
            # Rate limiting handling
            if error_code == 'TooManyRequestsException':
                import time
                time.sleep(1)  # Simple backoff
    
    return results

# Usage example with error handling
ids_to_delete = list(range(1, 101))  # Delete IDs 1-100
result = bulk_delete(s3vectors, bucket_name, index_name, ids_to_delete)

print(f"Successfully deleted: {result['deleted']}")
if result['failed'] > 0:
    print(f"Failed to delete: {result['failed']}")
    for error in result['errors']:
        print(f"  Error in batch starting at {error['batch_start']}: {error['error']}")
```

## Operation 4: get_neighbours - Find nearest neighbors

The `get_neighbours` operation performs similarity search to find the closest vectors to a query embedding:

```python
def get_neighbours(s3vectors_client, bucket_name, index_name, embedding, 
                   k=10, metadata_filter=None, include_embeddings=False):
    """
    Find nearest neighbors for a given embedding vector.
    
    Args:
        embedding: Query vector (float array)
        k: Number of neighbors to return (max 30)
        metadata_filter: Optional dict for filtering results
        include_embeddings: Whether to return full embeddings
    
    Returns:
        list: Nearest neighbors with IDs, distances, and metadata
    """
    try:
        # Build query parameters
        query_params = {
            'vectorBucketName': bucket_name,
            'indexName': index_name,
            'queryVector': {'float32': embedding},
            'topK': min(k, 30),  # API limit
            'returnMetadata': True,
            'returnDistance': True
        }
        
        # Add optional parameters
        if metadata_filter:
            query_params['filter'] = metadata_filter
            
        if include_embeddings:
            query_params['returnVector'] = True
        
        # Execute query
        response = s3vectors_client.query_vectors(**query_params)
        
        # Process results
        neighbors = []
        for vector in response.get('vectors', []):
            neighbor = {
                'id': int(vector['key']),  # Convert string key back to int
                'distance': vector['distance'],
                'metadata': vector.get('metadata', {})
            }
            
            if include_embeddings and 'data' in vector:
                neighbor['embedding'] = vector['data']['float32']
                
            neighbors.append(neighbor)
        
        # Sort by distance (lower is more similar)
        neighbors.sort(key=lambda x: x['distance'])
        
        return neighbors
        
    except ClientError as e:
        print(f"Error querying vectors: {e}")
        return []

# Usage example with metadata filtering
query_embedding = [0.15, 0.25, 0.35] * 341  # Must match index dimensionality

# Find technical documents similar to query
neighbors = get_neighbours(
    s3vectors, 
    bucket_name, 
    index_name,
    query_embedding,
    k=5,
    metadata_filter={'category': 'technical'}
)

print(f"Found {len(neighbors)} similar vectors:")
for i, neighbor in enumerate(neighbors, 1):
    print(f"{i}. ID: {neighbor['id']}")
    print(f"   Distance: {neighbor['distance']:.4f}")
    print(f"   Metadata: {neighbor['metadata']}")
```

## Best practices and performance optimization

**Batch processing efficiency** is crucial for S3 Vectors operations. Always use maximum batch sizes (500 for insert/delete, 100 for select) to minimize API calls and costs. For large datasets, implement parallel processing with multiple threads, but respect the 5+ requests/second write limit per index.

**Error handling strategies** should include exponential backoff for rate limiting (TooManyRequestsException), validation of vector dimensions before insertion, and graceful handling of missing vectors in bulk operations. Consider implementing a retry mechanism with jitter for transient failures.

**Metadata optimization** can significantly impact costs and performance. Mark fields as non-filterable when they're only for reference (saves on filterable metadata costs), keep total metadata under 40KB per vector, and use consistent field names across vectors for better query performance.

For **primary key management**, establish a clear conversion strategy between integer IDs and string keys. Consider zero-padding for sortable keys (e.g., "000001" instead of "1") or using UUID strings for distributed systems. Maintain an external mapping if complex key transformations are needed.

## Integration with embedding models

S3 Vectors integrates seamlessly with Amazon Bedrock for embedding generation:

```python
import boto3
import json

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

def generate_and_store_embeddings(texts, ids):
    """Generate embeddings and store in S3 Vectors"""
    items = []
    
    for text, id in zip(texts, ids):
        # Generate embedding
        response = bedrock.invoke_model(
            modelId='amazon.titan-embed-text-v2:0',
            body=json.dumps({"inputText": text})
        )
        embedding = json.loads(response['body'].read())['embedding']
        
        items.append({
            'id': id,
            'embedding': embedding,
            'metadata': {'text_preview': text[:100]}
        })
    
    # Bulk insert
    return bulk_insert(s3vectors, bucket_name, index_name, items)
```

## Performance considerations and limitations

S3 Vectors optimizes for **cost over latency**, providing sub-second query times (typically 200-500ms) suitable for batch processing and offline analytics. The service handles hundreds of queries per second per index, with write throughput limited to 5+ requests/second per index.

Key **operational limits** include 50 million vectors per index, 4,096 maximum dimensions per vector, 30 maximum results per query, and 40KB total metadata per vector. Plan your architecture around these constraints, using multiple indexes for larger datasets or multi-tenancy scenarios.

The service excels for **RAG applications**, long-term vector storage, and cost-sensitive workloads but isn't ideal for real-time recommendations or applications requiring consistent sub-100ms latency. Consider hybrid architectures using S3 Vectors for cold storage and traditional vector databases for hot data.

## Conclusion

Amazon S3 Vectors provides a cost-effective solution for large-scale vector storage with native S3 integration. By understanding the string-based key system and leveraging bulk operations effectively, you can build efficient vector storage systems that balance cost and performance. The code examples provided demonstrate practical implementations of all requested operations, with proper error handling and optimization techniques for production use.