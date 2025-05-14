import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('PineconeSetup')

def create_index():
    """Create Pinecone index with 384 dimensions for OpenAI embeddings"""
    # Load environment variables
    load_dotenv()
    
    # Initialize Pinecone with new syntax
    api_key = os.getenv('PINECONE_API_KEY')
    if not api_key:
        logger.error("Missing PINECONE_API_KEY in environment variables")
        return
        
    pc = Pinecone(api_key=api_key)
    
    # Get index name from environment
    index_name = os.getenv('PINECONE_INDEX_NAME')
    if not index_name:
        logger.error("Missing PINECONE_INDEX_NAME in environment variables")
        return
    
    # Check if index already exists
    if index_name in pc.list_indexes().names():
        logger.info(f"Index '{index_name}' already exists")
        return
    
    # Get region from environment
    region = os.getenv('PINECONE_ENVIRONMENT')
    if not region:
        logger.error("Missing PINECONE_ENVIRONMENT in environment variables")
        return
    
    try:
        # Create the index with new syntax - 384 dimensions for text-embedding-small-3
        logger.info(f"Creating Pinecone index '{index_name}' with 384 dimensions for OpenAI embeddings")
        pc.create_index(
            name=index_name,
            dimension=1536,  # OpenAI text-embedding-3-small dimension
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region=region
            )
        )
        logger.info(f"Successfully created index: {index_name}")
    except Exception as e:
        logger.error(f"Error creating index: {str(e)}")

if __name__ == "__main__":
    create_index()