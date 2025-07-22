import numpy as np
from typing import List, Tuple


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    Returns a value between -1 and 1, where 1 means identical direction.
    """
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)
    
    dot_product = np.dot(vec1_np, vec2_np)
    norm1 = np.linalg.norm(vec1_np)
    norm2 = np.linalg.norm(vec2_np)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def cosine_similarity_percentage(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity and return as percentage (0-100%).
    Maps [-1, 1] to [0, 100].
    """
    similarity = cosine_similarity(vec1, vec2)
    # Convert from [-1, 1] to [0, 1] then to percentage
    percentage = (similarity + 1) / 2 * 100
    return percentage


def rank_by_similarity(query_vector: List[float], 
                      documents: List[dict], 
                      top_k: int = 10) -> List[Tuple[dict, float]]:
    """
    Rank documents by cosine similarity to query vector.
    Returns list of (document, similarity_score) tuples.
    """
    results = []
    
    for doc in documents:
        # Extract embedding from S3 Vectors format
        if 'data' in doc and 'float32' in doc['data']:
            doc_embedding = doc['data']['float32']
        else:
            continue
            
        similarity = cosine_similarity(query_vector, doc_embedding)
        results.append((doc, similarity))
    
    # Sort by similarity (descending)
    results.sort(key=lambda x: x[1], reverse=True)
    
    return results[:top_k]