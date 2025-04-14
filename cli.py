# cli.py
import os
from dotenv import load_dotenv

from rag_components.document_processor import DocumentProcessor
from rag_components.pinecone_client import PineconeClient
from rag_components.embedding_service import EmbeddingService
from rag_components.rag_engine import RAGEngine
from rag_components.chat_interface import ChatInterface
from rag_components.youtube_loader import YouTubeLoader

# Load environment variables
load_dotenv()

def main():
    """Start the CLI interface for the RAG chatbot"""
    print("Initializing RAG components...")
    
    # Initialize components
    pinecone_client = PineconeClient(
        api_key=os.getenv("PINECONE_API_KEY"),
        environment=os.getenv("PINECONE_ENVIRONMENT"),
        index_name=os.getenv("PINECONE_INDEX_NAME")
    )
    
    embedding_service = EmbeddingService()
    
    rag_engine = RAGEngine(
        embedding_service=embedding_service,
        vector_store=pinecone_client,
        llm_api_key=os.getenv("GEMINI_API_KEY")
    )
    
    # Start the chat interface
    chat_interface = ChatInterface(rag_engine=rag_engine)
    chat_interface.start()

if __name__ == "__main__":
    main()