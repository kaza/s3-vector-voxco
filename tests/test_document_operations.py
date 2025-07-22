import pytest
import numpy as np
from src.document import Document
from src.s3_vectors_client import S3VectorsClient
import os
import uuid


@pytest.fixture
def test_bucket_name():
    """Generate a unique test bucket name"""
    return f"test-vectors-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_index_name():
    """Test index name"""
    return "test-documents"


@pytest.fixture
def s3_client(test_bucket_name, test_index_name):
    """Create S3 Vectors client for testing"""
    return S3VectorsClient(
        bucket_name=test_bucket_name,
        index_name=test_index_name,
        region='us-east-1'
    )


def test_document_creation():
    """Test creating a document with random embedding"""
    doc = Document.create(content="This is a test document")
    
    assert doc.key is not None
    assert len(doc.key) == 36  # UUID length
    assert doc.content == "This is a test document"
    assert len(doc.embedding) == 128
    assert all(0 <= x <= 1 for x in doc.embedding)  # Random values between 0 and 1


def test_document_with_custom_embedding():
    """Test creating a document with custom embedding"""
    custom_embedding = [0.1] * 128
    doc = Document.create(content="Test with custom embedding", embedding=custom_embedding)
    
    assert doc.embedding == custom_embedding
    assert doc.content == "Test with custom embedding"


def test_document_invalid_embedding_size():
    """Test that invalid embedding size raises error"""
    with pytest.raises(ValueError, match="Embedding must be 128 dimensions"):
        Document(key="test", content="test", embedding=[0.1] * 64)


def test_document_to_s3_format():
    """Test converting document to S3 Vectors format"""
    doc = Document.create(content="Convert to S3 format")
    s3_format = doc.to_s3_vector_format()
    
    assert 'key' in s3_format
    assert 'data' in s3_format
    assert 'float32' in s3_format['data']
    assert 'metadata' in s3_format
    assert s3_format['metadata']['content'] == "Convert to S3 format"
    assert len(s3_format['data']['float32']) == 128


@pytest.mark.skip(reason="Requires actual S3 Vectors bucket - run manually")
def test_insert_single_document(s3_client):
    """Test inserting a single document to S3 Vectors"""
    # Create bucket and index first
    s3_client.create_bucket()
    s3_client.create_index(dimensions=128)
    
    # Create and insert document
    doc = Document.create(content="Hello from S3 Vectors!")
    response = s3_client.insert_documents([doc.to_s3_vector_format()])
    
    assert response is not None
    print(f"Inserted document with key: {doc.key}")


@pytest.mark.skip(reason="Requires actual S3 Vectors bucket - run manually")
def test_search_similar_documents(s3_client):
    """Test searching for similar documents"""
    # Create bucket and index
    s3_client.create_bucket()
    s3_client.create_index(dimensions=128)
    
    # Insert some documents
    docs = [
        Document.create(content="Python programming tutorial"),
        Document.create(content="JavaScript web development"),
        Document.create(content="Python data science guide")
    ]
    
    s3_client.insert_documents([doc.to_s3_vector_format() for doc in docs])
    
    # Search with a query embedding
    query_embedding = np.random.rand(128).tolist()
    results = s3_client.search_similar(embedding=query_embedding, k=2)
    
    assert len(results) <= 2
    for result in results:
        print(f"Found: {result.get('metadata', {}).get('content')} (score: {result.get('score')})")