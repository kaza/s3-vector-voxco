import boto3
from typing import List, Dict, Optional
import time
from botocore.exceptions import ClientError


class S3VectorsClient:
    def __init__(self, bucket_name: str, index_name: str, region: str = 'us-east-1'):
        self.bucket_name = bucket_name
        self.index_name = index_name
        self.region = region
        self.client = boto3.client('s3vectors', region_name=region)
    
    def create_bucket(self) -> Dict:
        """Create a vector bucket"""
        try:
            response = self.client.create_vector_bucket(
                vectorBucketName=self.bucket_name
            )
            print(f"✓ Created vector bucket: {self.bucket_name}")
            return response
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in ['BucketAlreadyExists', 'ConflictException']:
                print(f"! Bucket {self.bucket_name} already exists")
                return {'Status': 'AlreadyExists'}
            raise
    
    def create_index(self, dimensions: int = 128) -> Dict:
        """Create a vector index"""
        try:
            response = self.client.create_index(
                vectorBucketName=self.bucket_name,
                indexName=self.index_name,
                dataType='float32',
                dimension=dimensions,
                distanceMetric='cosine'
            )
            print(f"✓ Created vector index: {self.index_name} with {dimensions} dimensions")
            # Wait for index to be ready
            time.sleep(2)
            return response
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in ['IndexAlreadyExists', 'ConflictException']:
                print(f"! Index {self.index_name} already exists")
                return {'Status': 'AlreadyExists'}
            raise
    
    def insert_documents(self, documents: List[Dict]) -> Dict:
        """Insert documents in batches"""
        try:
            response = self.client.put_vectors(
                vectorBucketName=self.bucket_name,
                indexName=self.index_name,
                vectors=documents
            )
            print(f"✓ Inserted {len(documents)} documents")
            return response
        except ClientError as e:
            print(f"✗ Error inserting documents: {e}")
            raise
    
    def get_documents(self, keys: List[str]) -> List[Dict]:
        """Retrieve documents by keys"""
        try:
            response = self.client.get_vectors(
                vectorBucketName=self.bucket_name,
                indexName=self.index_name,
                keys=keys,
                returnData=True,
                returnMetadata=True
            )
            return response.get('vectors', [])
        except ClientError as e:
            print(f"✗ Error retrieving documents: {e}")
            raise
    
    def search_similar(self, embedding: List[float], k: int = 10) -> List[Dict]:
        """Search for similar documents"""
        try:
            response = self.client.query_vectors(
                vectorBucketName=self.bucket_name,
                indexName=self.index_name,
                queryVector={'float32': embedding},
                topK=k
            )
            return response.get('matches', [])
        except ClientError as e:
            print(f"✗ Error searching: {e}")
            raise
    
    def delete_documents(self, keys: List[str]) -> Dict:
        """Delete documents by keys"""
        try:
            response = self.client.delete_vectors(
                vectorBucketName=self.bucket_name,
                indexName=self.index_name,
                keys=keys
            )
            print(f"✓ Deleted {len(keys)} documents")
            return response
        except ClientError as e:
            print(f"✗ Error deleting documents: {e}")
            raise