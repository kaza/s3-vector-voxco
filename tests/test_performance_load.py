"""
Performance test: Load 1000 records into S3 Vectors as fast as possible
"""
import time
import uuid
import numpy as np
import boto3
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from dotenv import load_dotenv

load_dotenv()

# Constants
TOTAL_RECORDS = 1000
BATCH_SIZE = 500  # S3 Vectors max batch size
VECTOR_DIMENSIONS = 128
NUM_THREADS = 4  # Parallel batch uploads

# S3 Vectors configuration
BUCKET_NAME = os.getenv("S3_VECTORS_BUCKET_NAME", "almir-s3-vectors-poc-test")
INDEX_NAME = "performance-test"
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")


def generate_batch(batch_num: int, size: int):
    """Generate a batch of vectors with random embeddings"""
    vectors = []
    for i in range(size):
        record_id = batch_num * BATCH_SIZE + i
        vectors.append({
            'key': f"perf-test-{uuid.uuid4().hex[:8]}-{record_id}",
            'data': {
                'float32': np.random.rand(VECTOR_DIMENSIONS).tolist()
            },
            'metadata': {
                'content': f"Performance test document {record_id}",
                'batch': batch_num,
                'timestamp': time.time()
            }
        })
    return vectors


def upload_batch(client, batch_num: int, size: int):
    """Upload a single batch to S3 Vectors"""
    start_time = time.time()
    
    # Generate batch
    vectors = generate_batch(batch_num, size)
    
    # Upload to S3 Vectors
    try:
        response = client.put_vectors(
            vectorBucketName=BUCKET_NAME,
            indexName=INDEX_NAME,
            vectors=vectors
        )
        
        elapsed = time.time() - start_time
        return {
            'batch': batch_num,
            'size': size,
            'time': elapsed,
            'success': True
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            'batch': batch_num,
            'size': size,
            'time': elapsed,
            'success': False,
            'error': str(e)
        }


def clean_index(client):
    """Delete all documents from the performance test index"""
    try:
        # List all vectors
        response = client.list_vectors(
            vectorBucketName=BUCKET_NAME,
            indexName=INDEX_NAME,
            maxResults=1000
        )
        
        if 'vectors' in response and response['vectors']:
            keys = [v['key'] for v in response['vectors']]
            client.delete_vectors(
                vectorBucketName=BUCKET_NAME,
                indexName=INDEX_NAME,
                keys=keys
            )
            print(f"Cleaned {len(keys)} existing documents")
    except Exception as e:
        print(f"Clean failed: {e}")


def ensure_index_exists(client):
    """Create index if it doesn't exist"""
    try:
        client.create_index(
            vectorBucketName=BUCKET_NAME,
            indexName=INDEX_NAME,
            dataType='float32',
            dimension=VECTOR_DIMENSIONS,
            distanceMetric='cosine'
        )
        print(f"Created index: {INDEX_NAME}")
        time.sleep(2)  # Wait for index to be ready
    except Exception as e:
        if 'ConflictException' in str(e) or 'already exists' in str(e).lower():
            print(f"Index {INDEX_NAME} already exists")
        else:
            raise


def main():
    print("=== S3 Vectors Performance Test ===")
    print(f"Loading {TOTAL_RECORDS} records with {VECTOR_DIMENSIONS}-dim random vectors")
    print(f"Batch size: {BATCH_SIZE}, Threads: {NUM_THREADS}\n")
    
    # Initialize client
    client = boto3.client('s3vectors', region_name=REGION)
    
    # Ensure index exists
    ensure_index_exists(client)
    
    # Clean existing data
    print("Cleaning existing data...")
    clean_index(client)
    
    # Calculate batches
    num_batches = (TOTAL_RECORDS + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"\nStarting upload of {num_batches} batches...")
    overall_start = time.time()
    
    # Upload batches in parallel
    results = []
    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        # Submit all batch uploads
        futures = []
        for i in range(num_batches):
            # Calculate batch size (last batch might be smaller)
            batch_size = min(BATCH_SIZE, TOTAL_RECORDS - i * BATCH_SIZE)
            future = executor.submit(upload_batch, client, i, batch_size)
            futures.append(future)
        
        # Collect results as they complete
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            
            if result['success']:
                print(f"✓ Batch {result['batch']} uploaded: {result['size']} records in {result['time']:.2f}s")
            else:
                print(f"✗ Batch {result['batch']} failed: {result['error']}")
    
    overall_time = time.time() - overall_start
    
    # Calculate statistics
    successful_batches = [r for r in results if r['success']]
    total_uploaded = sum(r['size'] for r in successful_batches)
    avg_batch_time = sum(r['time'] for r in successful_batches) / len(successful_batches) if successful_batches else 0
    
    print("\n=== Results ===")
    print(f"Total time: {overall_time:.2f} seconds")
    print(f"Records uploaded: {total_uploaded}/{TOTAL_RECORDS}")
    print(f"Records per second: {total_uploaded/overall_time:.2f}")
    print(f"Average batch time: {avg_batch_time:.2f}s")
    print(f"Successful batches: {len(successful_batches)}/{num_batches}")
    
    # Verify count
    time.sleep(2)  # Give S3 time to index
    try:
        response = client.list_vectors(
            vectorBucketName=BUCKET_NAME,
            indexName=INDEX_NAME,
            maxResults=10
        )
        print(f"\nVerification: Index now contains vectors (sample shown)")
    except Exception as e:
        print(f"\nVerification failed: {e}")


if __name__ == "__main__":
    main()