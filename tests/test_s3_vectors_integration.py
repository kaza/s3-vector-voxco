import pytest
import numpy as np
from src.document import Document
from src.s3_vectors_client import S3VectorsClient
import time
import uuid


# Use a fixed bucket name for testing (you can change this)
TEST_BUCKET_NAME = "almir-s3-vectors-poc-test"
TEST_INDEX_NAME = "documents"


@pytest.fixture(scope="module")
def s3_client():
    """Create S3 Vectors client for integration tests"""
    return S3VectorsClient(
        bucket_name=TEST_BUCKET_NAME,
        index_name=TEST_INDEX_NAME,
        region='us-east-1'
    )


def test_create_bucket_and_index(s3_client):
    """Test creating a vector bucket and index"""
    print(f"\n1. Creating bucket: {TEST_BUCKET_NAME}")
    response = s3_client.create_bucket()
    assert response is not None
    
    print(f"2. Creating index: {TEST_INDEX_NAME} with 128 dimensions")
    response = s3_client.create_index(dimensions=128)
    assert response is not None
    
    # Wait a bit for index to be ready
    print("3. Waiting for index to be ready...")
    time.sleep(3)


def test_insert_sample_documents(s3_client):
    """Test inserting sample documents with fake embeddings"""
    print("\n4. Creating sample documents...")
    
    # Create sample documents with different content
    documents = [
        Document.create(content="Introduction to Python programming"),
        Document.create(content="Advanced machine learning techniques"),
        Document.create(content="Building scalable web applications"),
        Document.create(content="Python data science tutorial"),
        Document.create(content="Cloud computing with AWS"),
    ]
    
    # Convert to S3 format
    s3_documents = [doc.to_s3_vector_format() for doc in documents]
    
    print(f"5. Inserting {len(documents)} documents...")
    for doc in documents:
        print(f"   - {doc.key[:8]}... : {doc.content}")
    
    response = s3_client.insert_documents(s3_documents)
    assert response is not None
    
    # Store keys for later tests
    pytest.document_keys = [doc.key for doc in documents]
    print(f"✓ Successfully inserted {len(documents)} documents")


def test_retrieve_documents(s3_client):
    """Test retrieving documents by key"""
    if not hasattr(pytest, 'document_keys'):
        pytest.skip("No documents inserted yet")
    
    print("\n6. Retrieving documents by key...")
    # Get first two document keys
    keys_to_retrieve = pytest.document_keys[:2]
    
    documents = s3_client.get_documents(keys_to_retrieve)
    print(f"✓ Retrieved {len(documents)} documents")
    
    for doc in documents:
        print(f"   - {doc['key'][:8]}... : {doc['metadata']['content']}")
    
    assert len(documents) == 2


def test_search_similar_documents(s3_client):
    """Test searching for similar documents"""
    print("\n7. Searching for similar documents...")
    
    # Create a query embedding (in real use, this would come from encoding a query)
    query_embedding = np.random.rand(128).tolist()
    
    results = s3_client.search_similar(embedding=query_embedding, k=3)
    print(f"✓ Found {len(results)} similar documents")
    
    for i, result in enumerate(results):
        content = result.get('metadata', {}).get('content', 'N/A')
        score = result.get('score', 0)
        print(f"   {i+1}. {content} (similarity: {score:.4f})")
    
    assert len(results) <= 3


def test_delete_sample_document(s3_client):
    """Test deleting a document"""
    if not hasattr(pytest, 'document_keys'):
        pytest.skip("No documents inserted yet")
    
    print("\n8. Deleting a document...")
    key_to_delete = pytest.document_keys[0]
    
    response = s3_client.delete_documents([key_to_delete])
    assert response is not None
    print(f"✓ Deleted document: {key_to_delete[:8]}...")


if __name__ == "__main__":
    # Run tests in order
    pytest.main([__file__, "-v", "-s", "--tb=short"])