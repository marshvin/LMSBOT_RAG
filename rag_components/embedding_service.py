import requests
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List

class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Using sentence-transformers for embeddings
        self.model = SentenceTransformer(model_name)
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for the given text"""
        embedding = self.model.encode(text)
        return embedding.tolist()