import requests
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List

class EmbeddingService:
    def __init__(self):
        # Lazy load model only when needed
        self.model = None
    
    def get_embedding(self, text: str) -> list:
        # Initialize model only when needed (lazy loading)
        if self.model is None:
            # Use the original model
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Cap text length to prevent memory spikes
        if len(text) > 8192:
            text = text[:8192]
            
        embedding = self.model.encode(text)
        return embedding.tolist()