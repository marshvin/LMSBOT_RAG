import requests
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List

class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def get_embedding(self, text: str) -> list:
        embedding = self.model.encode(text)
        return embedding.tolist()