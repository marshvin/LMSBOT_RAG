# app.py
from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv
import gc

# Import components when needed to reduce initial memory load
from rag_components.pinecone_client import PineconeClient

# Load environment variables
load_dotenv()

# Initialize components
def init_components():
    # Create Pinecone client - needed for all operations
    pinecone_client = PineconeClient(
        api_key=os.getenv("PINECONE_API_KEY"),
        environment=os.getenv("PINECONE_ENVIRONMENT"),
        index_name=os.getenv("PINECONE_INDEX_NAME")
    )
    
    # Return minimal components to start with - others will be lazy loaded
    components = {
        "pinecone_client": pinecone_client
    }
    
    # Return components dictionary
    return components

# Lazily load components only when needed
def get_component(name, components):
    """Lazily initialize components only when needed"""
    if name not in components:
        if name == "embedding_service":
            from rag_components.embedding_service import EmbeddingService
            components[name] = EmbeddingService()
        elif name == "document_processor":
            from rag_components.document_processor import DocumentProcessor
            from rag_components.embedding_service import EmbeddingService
            if "embedding_service" not in components:
                components["embedding_service"] = EmbeddingService()
            components[name] = DocumentProcessor(
                embedding_service=components["embedding_service"],
                vector_store=components["pinecone_client"]
            )
        elif name == "youtube_loader":
            from rag_components.youtube_loader import YouTubeLoader
            components[name] = YouTubeLoader(
                api_key=os.getenv("YOUTUBE_API_KEY"),
                channel_id=os.getenv("YOUTUBE_CHANNEL_ID"),
                max_videos=int(os.getenv("YOUTUBE_MAX_VIDEOS", "20"))
            )
        elif name == "rag_engine":
            from rag_components.rag_engine import RAGEngine
            from rag_components.embedding_service import EmbeddingService
            if "embedding_service" not in components:
                components["embedding_service"] = EmbeddingService()
            
            # Explicitly disable caching to prevent memory issues
            use_cache = False  # Set to False to disable caching in production
            
            components[name] = RAGEngine(
                embedding_service=components["embedding_service"],
                vector_store=components["pinecone_client"],
                llm_api_key=os.getenv("GEMINI_API_KEY"),
                use_cache=use_cache
            )
    
    return components[name]

# Create and configure app
app = Flask(__name__)

# Set a smaller size for JSON responses
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max upload

# Get allowed origins from environment or use defaults
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,https://lmsbot-frontend.vercel.app").split(",")

# Enable simple CORS for all routes
CORS(app, origins=allowed_origins)

# Initialize minimal components
components = init_components()

# Run garbage collection to clean up memory
gc.collect()

# Register routes
from routes.health_routes import health_bp
from routes.document_routes import document_bp
from routes.query_routes import query_bp
from routes.youtube_routes import youtube_bp

# Add middleware to provide lazy component loading
@app.before_request
def before_request():
    app.config['GET_COMPONENT'] = lambda name: get_component(name, components)

# Register blueprints
app.register_blueprint(health_bp)
app.register_blueprint(document_bp)
app.register_blueprint(query_bp)
app.register_blueprint(youtube_bp)

# Add components to app context
app.config['COMPONENTS'] = components

# This simplifies deployment - the app can be directly run by Render
if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)