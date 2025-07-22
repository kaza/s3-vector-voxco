import boto3
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
import sys

# Add parent directory to import our core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.s3_vectors_client import S3VectorsClient
from src.document import Document

load_dotenv()


class S3VectorsManager:
    """Simplified S3 Vectors operations for the web demo"""
    
    def __init__(self, bucket_name: Optional[str] = None, index_name: Optional[str] = None):
        self.bucket_name = bucket_name or os.getenv("S3_VECTORS_BUCKET_NAME", "almir-s3-vectors-poc-test")
        self.index_name = index_name or os.getenv("S3_VECTORS_INDEX_NAME", "documents")
        self.client = S3VectorsClient(self.bucket_name, self.index_name)
    
    def get_document_count(self) -> int:
        """Get total number of documents in the index"""
        try:
            # List vectors with max allowed to get accurate count
            all_vectors = []
            next_token = None
            
            while True:
                if next_token:
                    response = self.client.client.list_vectors(
                        vectorBucketName=self.bucket_name,
                        indexName=self.index_name,
                        maxResults=1000,
                        nextToken=next_token
                    )
                else:
                    response = self.client.client.list_vectors(
                        vectorBucketName=self.bucket_name,
                        indexName=self.index_name,
                        maxResults=1000
                    )
                
                vectors = response.get('vectors', [])
                all_vectors.extend(vectors)
                
                # Check if there are more results
                next_token = response.get('nextToken')
                if not next_token:
                    break
                    
            return len(all_vectors)
        except Exception as e:
            print(f"Error getting document count: {e}")
            return 0
    
    def add_document(self, content: str, embedding: List[float]) -> Dict:
        """Add a single document with its embedding"""
        doc = Document.create(content=content, embedding=embedding)
        self.client.insert_documents([doc.to_s3_vector_format()])
        return {
            'id': doc.key,
            'content': content,
            'success': True
        }
    
    def list_documents(self, limit: int = 10) -> List[Dict]:
        """List documents with their metadata"""
        try:
            # Get document IDs
            response = self.client.client.list_vectors(
                vectorBucketName=self.bucket_name,
                indexName=self.index_name,
                maxResults=limit
            )
            
            if not response.get('vectors'):
                return []
            
            # Get full documents with metadata
            keys = [v['key'] for v in response['vectors']]
            return self.client.get_documents(keys)
        except Exception as e:
            print(f"Error listing documents: {e}")
            return []
    
    def search_documents(self, query_embedding: List[float], top_k: int = 10) -> List[Dict]:
        """Search for similar documents using vector similarity"""
        try:
            print(f"\n=== SEARCH DEBUG ===")
            print(f"Bucket: {self.bucket_name}")
            print(f"Index: {self.index_name}")
            print(f"Query embedding sample: {query_embedding[:5]}")
            print(f"Top K: {top_k}")
            
            # Call query_vectors directly
            response = self.client.client.query_vectors(
                vectorBucketName=self.bucket_name,
                indexName=self.index_name,
                queryVector={'float32': query_embedding},
                topK=top_k,
                returnMetadata=True,
                returnDistance=True
            )
            
            # Debug response
            print(f"Response keys: {list(response.keys())}")
            clean_response = {k: v for k, v in response.items() if k != 'ResponseMetadata'}
            print(f"Response (no metadata): {clean_response}")
            
            # Get the actual results from response
            results = response.get('vectors', [])
            print(f"Number of results: {len(results)}")
            print("===================\n")
            
            # Process results - S3 Vectors returns key, metadata, and distance only
            enriched_results = []
            for result in results:
                enriched_results.append({
                    'key': result.get('key'),
                    'content': result.get('metadata', {}).get('content', 'N/A'),
                    'distance': result.get('distance', None),
                    'metadata': result.get('metadata', {})
                })
            
            return enriched_results
        except Exception as e:
            print(f"Error searching documents: {e}")
            return []
    
    def delete_document(self, key: str) -> bool:
        """Delete a single document by key"""
        try:
            self.client.delete_documents([key])
            return True
        except Exception:
            return False
    
    def delete_all_documents(self) -> int:
        """Delete all documents in the index"""
        try:
            response = self.client.client.list_vectors(
                vectorBucketName=self.bucket_name,
                indexName=self.index_name,
                maxResults=1000
            )
            
            if not response.get('vectors'):
                return 0
            
            keys = [v['key'] for v in response['vectors']]
            self.client.delete_documents(keys)
            return len(keys)
        except Exception as e:
            print(f"Error deleting all documents: {e}")
            return 0
    
    def get_index_info(self) -> Dict:
        """Get information about the current index"""
        return {
            'bucket': self.bucket_name,
            'index': self.index_name,
            'region': self.client.region,
            'document_count': self.get_document_count()
        }
    
    def test_query_response(self) -> Dict:
        """Test the query_vectors API to see response format"""
        try:
            test_embedding = [0.1] * 128
            response = self.client.client.query_vectors(
                vectorBucketName=self.bucket_name,
                indexName=self.index_name,
                queryVector={'float32': test_embedding},
                topK=1,
                returnMetadata=True
            )
            # Remove ResponseMetadata for cleaner display
            return {k: v for k, v in response.items() if k != 'ResponseMetadata'}
        except Exception as e:
            return {'error': str(e)}