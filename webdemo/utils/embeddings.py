import openai
import numpy as np
from typing import List, Optional
import os
from dotenv import load_dotenv

load_dotenv()


class OpenAIEmbeddings:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = "text-embedding-3-small"
        self.target_dimension = 128
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text using OpenAI API"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.target_dimension  # OpenAI supports dimension reduction
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            # Fallback to random embedding if API fails
            return np.random.rand(self.target_dimension).tolist()
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                dimensions=self.target_dimension
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            # Fallback to random embeddings
            return [np.random.rand(self.target_dimension).tolist() for _ in texts]