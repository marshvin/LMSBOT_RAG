import requests
import numpy as np
from typing import List
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('EmbeddingService')

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.error("OpenAI package is not installed. Please install it with 'pip install openai'")

class EmbeddingService:
    def __init__(self, openai_api_key=None):
        """
        Initialize the embedding service with OpenAI
        
        Args:
            openai_api_key: OpenAI API key for embeddings
        """
        # Store API key
        self.openai_api_key = openai_api_key
        
        # Initialize client lazily
        self.openai_client = None
        
        # Check if OpenAI is available
        self.openai_available = OPENAI_AVAILABLE and openai_api_key is not None
        
        if not self.openai_available:
            logger.warning("OpenAI embedding service is not available. Make sure to provide a valid API key.")
        else:
            logger.info("Embedding Service initialized with OpenAI")
    
    def get_embedding(self, text: str) -> list:
        """Get embedding for text using OpenAI's text-embedding-3-small model"""
        # Cap text length to prevent memory spikes
        if len(text) > 8192:
            text = text[:8192]
        
        # Check if OpenAI is available
        if not self.openai_available:
            logger.error("OpenAI is not available. Cannot generate embeddings.")
            # Return zero vector as fallback
            return [0.0] * 384
        
        try:
            # Initialize client on first use
            if self.openai_client is None:
                self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
                logger.info("OpenAI client initialized")
            
            # Generate embedding
            logger.info("Generating embedding with OpenAI text-embedding-3-small")
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding with OpenAI: {str(e)}")
            # Return zero vector as fallback for error cases
            return [0.0] * 384