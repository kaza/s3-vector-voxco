import uuid
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class Document:
    key: str
    content: str
    embedding: List[float]
    
    def __post_init__(self):
        if len(self.embedding) != 128:
            raise ValueError(f"Embedding must be 128 dimensions, got {len(self.embedding)}")
    
    @classmethod
    def create(cls, content: str, embedding: Optional[List[float]] = None) -> 'Document':
        if embedding is None:
            embedding = np.random.rand(128).tolist()
        
        return cls(
            key=str(uuid.uuid4()),
            content=content,
            embedding=embedding
        )
    
    def to_s3_vector_format(self) -> Dict:
        return {
            'key': self.key,
            'data': {
                'float32': self.embedding
            },
            'metadata': {
                'content': self.content
            }
        }