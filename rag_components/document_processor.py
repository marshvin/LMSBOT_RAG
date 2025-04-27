import hashlib
import uuid
from typing import List, Dict, Any

class DocumentProcessor:
    def __init__(self, embedding_service, vector_store):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
    
    def process_document(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """Process a document and store it in the vector database"""
        # Generate a unique ID for the document
        doc_id = str(uuid.uuid4())
        
        # Ensure metadata contains required fields
        if metadata is None:
            metadata = {}
        
        # Validate that course information is provided
        if "course" not in metadata:
            raise ValueError("Course information is required in metadata")
            
        # Ensure doc_name is present in metadata
        if "doc_name" not in metadata and "filename" in metadata:
            metadata["doc_name"] = metadata["filename"]
        elif "doc_name" not in metadata:
            metadata["doc_name"] = f"document_{doc_id}"
        
        # Split the document into chunks (simplified version)
        chunks = self._chunk_text(text)
        
        # Process each chunk
        for i, chunk in enumerate(chunks):
            # Generate embedding
            embedding = self.embedding_service.get_embedding(chunk)
            
            # Create metadata
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update({
                "chunk_id": i,
                "document_id": doc_id,
                "text": chunk
            })
            
            # Store in vector database
            self.vector_store.upsert(
                id=f"{doc_id}_{i}",
                vector=embedding,
                metadata=chunk_metadata
            )
        
        return doc_id
    
    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            # Adjust end to avoid cutting words
            if end < text_length:
                # Find the last space in this chunk
                while end > start and text[end] != ' ':
                    end -= 1
                if end == start:  # No spaces found, just cut at chunk_size
                    end = min(start + chunk_size, text_length)
            
            # Add the chunk to our list
            chunks.append(text[start:end])
            
            # Move the start position for the next chunk
            start = end - overlap if end < text_length else text_length
        
        return chunks