import pytest
import boto3
import numpy as np
import json
import os
from dotenv import load_dotenv

load_dotenv()

# This test file is to figure out what the fuck S3 Vectors API actually returns


@pytest.fixture
def s3_vectors_client():
    """Create S3 Vectors client"""
    return boto3.client('s3vectors', region_name='us-east-1')


@pytest.fixture
def test_bucket():
    return os.getenv("S3_VECTORS_BUCKET_NAME", "almir-s3-vectors-poc-test")


@pytest.fixture
def test_index():
    return os.getenv("S3_VECTORS_INDEX_NAME", "documents")


def test_what_does_query_vectors_actually_return(s3_vectors_client, test_bucket, test_index):
    """Test to see what query_vectors ACTUALLY returns"""
    
    # First, let's insert a test document with known content and embedding
    test_key = "test-query-response"
    test_content = "This is a test document for query response"
    test_embedding = [0.5] * 128  # Simple embedding for testing
    
    try:
        # Insert test document
        s3_vectors_client.put_vectors(
            vectorBucketName=test_bucket,
            indexName=test_index,
            vectors=[{
                'key': test_key,
                'data': {'float32': test_embedding},
                'metadata': {'content': test_content}
            }]
        )
        
        print("\n=== TESTING QUERY_VECTORS API ===")
        
        # Test 1: Basic query with no return flags
        print("\n1. Basic query (no flags):")
        response = s3_vectors_client.query_vectors(
            vectorBucketName=test_bucket,
            indexName=test_index,
            queryVector={'float32': test_embedding},
            topK=1
        )
        print_response(response)
        
        # Test 2: Query with returnMetadata=True
        print("\n2. Query with returnMetadata=True:")
        response = s3_vectors_client.query_vectors(
            vectorBucketName=test_bucket,
            indexName=test_index,
            queryVector={'float32': test_embedding},
            topK=1,
            returnMetadata=True
        )
        print_response(response)
        
        # Test 3: Query with returnDistance=True
        print("\n3. Query with returnDistance=True:")
        response = s3_vectors_client.query_vectors(
            vectorBucketName=test_bucket,
            indexName=test_index,
            queryVector={'float32': test_embedding},
            topK=1,
            returnDistance=True
        )
        print_response(response)
        
        # Test 4: Query with both flags
        print("\n4. Query with returnMetadata=True AND returnDistance=True:")
        response = s3_vectors_client.query_vectors(
            vectorBucketName=test_bucket,
            indexName=test_index,
            queryVector={'float32': test_embedding},
            topK=1,
            returnMetadata=True,
            returnDistance=True
        )
        print_response(response)
        
        # Clean up
        s3_vectors_client.delete_vectors(
            vectorBucketName=test_bucket,
            indexName=test_index,
            keys=[test_key]
        )
        
    except Exception as e:
        print(f"Error: {e}")
        pytest.fail(f"Test failed: {e}")


def test_check_api_parameters(s3_vectors_client):
    """Check what parameters query_vectors actually accepts"""
    import inspect
    
    print("\n=== CHECKING API PARAMETERS ===")
    
    # Get the method signature
    method = s3_vectors_client.query_vectors
    
    # Try to get help
    try:
        import pydoc
        help_text = pydoc.render_doc(method, "Help on %s")
        
        # Extract parameter information
        if "returnData" in help_text:
            print("✓ returnData parameter exists")
        else:
            print("✗ returnData parameter NOT found")
            
        if "returnMetadata" in help_text:
            print("✓ returnMetadata parameter exists")
        else:
            print("✗ returnMetadata parameter NOT found")
            
        if "returnDistance" in help_text:
            print("✓ returnDistance parameter exists")
        else:
            print("✗ returnDistance parameter NOT found")
            
        # Print all parameters
        print("\nAll parameters mentioned in help:")
        lines = help_text.split('\n')
        for line in lines:
            if 'return' in line.lower() and '=' in line:
                print(f"  - {line.strip()}")
                
    except Exception as e:
        print(f"Could not get help: {e}")


def print_response(response):
    """Helper to print response structure"""
    # Remove ResponseMetadata for clarity
    clean_response = {k: v for k, v in response.items() if k != 'ResponseMetadata'}
    
    print(f"Response keys: {list(clean_response.keys())}")
    
    if 'vectors' in clean_response and clean_response['vectors']:
        print(f"Number of results: {len(clean_response['vectors'])}")
        print(f"First result keys: {list(clean_response['vectors'][0].keys())}")
        print(f"First result: {json.dumps(clean_response['vectors'][0], indent=2)}")
    else:
        print("No results returned")
        print(f"Full response: {json.dumps(clean_response, indent=2)}")


if __name__ == "__main__":
    # Run specific test to understand the API
    pytest.main([__file__, "-v", "-s", "-k", "test_what_does_query_vectors_actually_return"])