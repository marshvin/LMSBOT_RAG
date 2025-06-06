# rag_components/pinecone_client.py
from pinecone import Pinecone
from typing import List, Dict, Any, Optional

class PineconeClient:
    def __init__(self, api_key: str, environment: str, index_name: str):
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=api_key)
        
        # Check if index exists, if not create it
        if index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=index_name,
                dimension=1536,  # Default dimension for OpenAI text-embedding-small-3
                metric='cosine'
            )
        
        self.index = self.pc.Index(index_name)
    
    def upsert(self, id: str, vector: List[float], metadata: Dict[str, Any] = None):
        """Insert or update a vector in the index"""
        self.index.upsert(vectors=[(id, vector, metadata)])
    
    def query(self, vector: List[float], top_k: int = 5, filter_params: Optional[Dict[str, Any]] = None):
        """
        Query the index for similar vectors with optional filtering
        
        Args:
            vector: The query vector
            top_k: Number of results to return
            filter_params: Optional filter parameters (e.g., {"course": "math101"})
        """
        return self.index.query(
            vector=vector, 
            top_k=top_k, 
            include_metadata=True,
            filter=filter_params
        )
    
    def delete(self, ids: List[str] = None, filter: Dict = None):
        """Delete vectors from the index"""
        if ids:
            self.index.delete(ids=ids)
        elif filter:
            self.index.delete(filter=filter)