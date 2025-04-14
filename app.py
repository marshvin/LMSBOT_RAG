# app.py
from flask import Flask
import os
from dotenv import load_dotenv

from rag_components.document_processor import DocumentProcessor
from rag_components.pinecone_client import PineconeClient
from rag_components.embedding_service import EmbeddingService
from rag_components.rag_engine import RAGEngine
from rag_components.youtube_loader import YouTubeLoader

# Load environment variables
load_dotenv()

# Initialize components
def init_components():
    pinecone_client = PineconeClient(
        api_key=os.getenv("PINECONE_API_KEY"),
        environment=os.getenv("PINECONE_ENVIRONMENT"),
        index_name=os.getenv("PINECONE_INDEX_NAME")
    )
    
    embedding_service = EmbeddingService()
    
    document_processor = DocumentProcessor(
        embedding_service=embedding_service,
        vector_store=pinecone_client
    )
    
    youtube_loader = YouTubeLoader(
        api_key=os.getenv("YOUTUBE_API_KEY"),
        channel_id=os.getenv("YOUTUBE_CHANNEL_ID"),
        max_videos=int(os.getenv("YOUTUBE_MAX_VIDEOS", "20"))
    )
    
    rag_engine = RAGEngine(
        embedding_service=embedding_service,
        vector_store=pinecone_client,
        llm_api_key=os.getenv("GEMINI_API_KEY")
    )
    
    return {
        "pinecone_client": pinecone_client,
        "embedding_service": embedding_service,
        "document_processor": document_processor,
        "youtube_loader": youtube_loader,
        "rag_engine": rag_engine
    }

# Create and configure app
def create_app():
    app = Flask(__name__)
    
    # Initialize components
    components = init_components()
    
    # Register routes
    from routes.health_routes import health_bp
    from routes.document_routes import document_bp
    from routes.query_routes import query_bp
    from routes.youtube_routes import youtube_bp
    
    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(document_bp)
    app.register_blueprint(query_bp)
    app.register_blueprint(youtube_bp)
    
    # Add components to app context
    app.config['COMPONENTS'] = components
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)