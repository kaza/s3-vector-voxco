"""
Script to populate S3 Vectors with 100 documents with OpenAI embeddings
"""
import sys
import os
import time
from typing import List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webdemo.utils.embeddings import OpenAIEmbeddings
from webdemo.utils.s3_vectors import S3VectorsManager
from src.document import Document
from dotenv import load_dotenv

load_dotenv()

# Sample content topics for generating documents
TOPICS = [
    "Python programming",
    "JavaScript development", 
    "Machine learning",
    "Data science",
    "Web development",
    "Cloud computing",
    "Database management",
    "API design",
    "Software architecture",
    "DevOps practices"
]

SUBTOPICS = [
    "introduction to",
    "advanced techniques in",
    "best practices for",
    "common patterns in",
    "troubleshooting",
    "optimization strategies for",
    "security considerations in",
    "future trends in",
    "getting started with",
    "mastering"
]

def generate_documents(count: int = 100) -> List[str]:
    """Generate UNIQUE document contents"""
    documents = []
    doc_id = 1
    
    # Generate unique combinations
    for topic in TOPICS:
        for subtopic in SUBTOPICS:
            if len(documents) >= count:
                break
                
            # Create unique content with ID
            content = f"Document {doc_id}: {subtopic.capitalize()} {topic} - A comprehensive guide with examples and best practices"
            documents.append(content)
            doc_id += 1
            
            if len(documents) >= count:
                break
    
    # If we need more, add some variations
    variations = [
        "The complete handbook for",
        "Essential skills in",
        "Professional guide to",
        "Modern approaches to",
        "Practical applications of"
    ]
    
    for variation in variations:
        for topic in TOPICS:
            if len(documents) >= count:
                break
                
            content = f"Document {doc_id}: {variation} {topic} - Industry insights and expert recommendations"
            documents.append(content)
            doc_id += 1
    
    return documents[:count]  # Return exactly the requested count

def main():
    print("=== S3 Vectors Data Population Script ===\n")
    
    # Initialize clients
    print("Initializing clients...")
    embeddings_client = OpenAIEmbeddings()
    s3_manager = S3VectorsManager()
    
    # Show current state
    current_count = s3_manager.get_document_count()
    print(f"Current documents in index: {current_count}")
    
    # Delete existing documents
    if current_count > 0:
        print(f"\nDeleting {current_count} existing documents...")
        deleted = s3_manager.delete_all_documents()
        print(f"Deleted {deleted} documents")
        time.sleep(2)  # Give S3 time to process deletions
    
    # Generate document contents
    print("\nGenerating 100 document contents...")
    contents = generate_documents(100)
    
    # Verify uniqueness
    unique_contents = set(contents)
    print(f"Generated {len(contents)} documents ({len(unique_contents)} unique)")
    if len(unique_contents) < len(contents):
        print("WARNING: Duplicate documents detected!")
        return
    
    # Process in batches to avoid rate limits
    batch_size = 10
    total_added = 0
    
    for i in range(0, len(contents), batch_size):
        batch = contents[i:i + batch_size]
        print(f"\nProcessing batch {i//batch_size + 1}/{len(contents)//batch_size}")
        
        # Generate embeddings for batch
        print(f"  Generating embeddings for {len(batch)} documents...")
        try:
            embeddings = embeddings_client.generate_embeddings(batch)
            
            # Add documents to S3 Vectors
            for j, (content, embedding) in enumerate(zip(batch, embeddings)):
                result = s3_manager.add_document(content, embedding)
                print(f"  Added document {i+j+1}: {content[:50]}...")
                total_added += 1
            
            # Small delay to avoid rate limits
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  Error in batch: {e}")
            continue
    
    # Final count
    print(f"\n=== Summary ===")
    print(f"Documents added: {total_added}")
    time.sleep(2)  # Give S3 time to index
    final_count = s3_manager.get_document_count()
    print(f"Final document count: {final_count}")
    
    # Test search
    print("\n=== Testing Search ===")
    test_query = "Python programming"
    print(f"Searching for: '{test_query}'")
    
    try:
        query_embedding = embeddings_client.generate_embedding(test_query)
        results = s3_manager.search_documents(query_embedding, top_k=5)
        
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results):
            print(f"{i+1}. (Distance: {result['distance']:.4f}) {result['content'][:60]}...")
    except Exception as e:
        print(f"Search test failed: {e}")

if __name__ == "__main__":
    main()