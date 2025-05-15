# app.py
from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv
import gc

# Import components when needed to reduce initial memory load
from rag_components.pinecone_client import PineconeClient

# Configure logging
import logging
logger = logging.getLogger('app')
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# API keys - with fallbacks
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyD4GzXELi3SNSc_ARm1fX_iaF0bh9nTv9g")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Required for embeddings and optional for LLM
PRIMARY_LLM = os.getenv("PRIMARY_LLM", "openai").lower()  # Default to OpenAI if not specified

# Check for required API keys
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not found in environment variables! The embedding service will not work properly.")
    logger.warning("Please set OPENAI_API_KEY in your .env file.")

# Validate PRIMARY_LLM setting
if PRIMARY_LLM not in ["openai", "gemini"]:
    logger.warning(f"Invalid PRIMARY_LLM value: {PRIMARY_LLM}. Must be 'openai' or 'gemini'. Defaulting to 'openai'.")
    PRIMARY_LLM = "openai"

logger.info(f"Configuration: Primary LLM set to {PRIMARY_LLM}")

# Initialize components
def init_components():
    # Create Pinecone client - needed for all operations
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    pinecone_env = os.getenv("PINECONE_ENVIRONMENT")
    pinecone_index = os.getenv("PINECONE_INDEX_NAME")
    
    if not pinecone_api_key or not pinecone_env or not pinecone_index:
        logger.warning("Missing Pinecone configuration. Please check your .env file.")
    
    pinecone_client = PineconeClient(
        api_key=pinecone_api_key,
        environment=pinecone_env,
        index_name=pinecone_index
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
            # OpenAI API key is required for the embedding service
            components[name] = EmbeddingService(openai_api_key=OPENAI_API_KEY)
        elif name == "document_processor":
            from rag_components.document_processor import DocumentProcessor
            from rag_components.embedding_service import EmbeddingService
            if "embedding_service" not in components:
                components["embedding_service"] = EmbeddingService(openai_api_key=OPENAI_API_KEY)
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
                components["embedding_service"] = EmbeddingService(openai_api_key=OPENAI_API_KEY)
            
            # Explicitly disable caching to prevent memory issues
            use_cache = False  # Set to False to disable caching in production
            
            # Determine which API to use primarily based on configured preference
            # Fallback to available API if preferred one is not available
            primary_llm = PRIMARY_LLM
            
            # Override if OpenAI is preferred but not available
            if primary_llm == "openai" and not OPENAI_API_KEY:
                primary_llm = "gemini"
                logger.warning("OpenAI preferred but API key not available. Falling back to Gemini.")
            
            # Override if Gemini is preferred but not available
            if primary_llm == "gemini" and not GEMINI_API_KEY:
                primary_llm = "openai" if OPENAI_API_KEY else None
                logger.warning("Gemini preferred but API key not available. Falling back to OpenAI.")
            
            logger.info(f"Initializing RAG engine with {primary_llm} as primary LLM")
            
            components[name] = RAGEngine(
                embedding_service=components["embedding_service"],
                vector_store=components["pinecone_client"],
                llm_api_key=GEMINI_API_KEY,  # Gemini API key
                use_cache=use_cache,
                openai_api_key=OPENAI_API_KEY,  # OpenAI API key
                primary_llm=primary_llm  # Which API to use primarily
            )
        elif name == "moodle_client":
            # Initialize Moodle client if credentials are available
            moodle_url = os.getenv("MOODLE_URL")
            moodle_token = os.getenv("MOODLE_TOKEN")
            
            if not moodle_url or not moodle_token:
                logger.warning("Moodle integration not configured. Set MOODLE_URL and MOODLE_TOKEN in your .env file.")
                return None
                
            from rag_components.moodle_client import MoodleClient
            components[name] = MoodleClient(
                base_url=moodle_url,
                token=moodle_token
            )
            logger.info(f"Initialized Moodle client for {moodle_url}")
    
    return components[name]

# Create and configure app
app = Flask(__name__, static_folder='static')

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
from routes.h5p_routes import h5p_bp  # Import the new H5P routes
from flask import send_from_directory

# Add middleware to provide lazy component loading
@app.before_request
def before_request():
    app.config['GET_COMPONENT'] = lambda name: get_component(name, components)

# Register blueprints
app.register_blueprint(health_bp)
app.register_blueprint(document_bp)
app.register_blueprint(query_bp)
app.register_blueprint(youtube_bp)
app.register_blueprint(h5p_bp)  # Register the H5P blueprint

# Add components to app context
app.config['COMPONENTS'] = components

# Add route for chatbot interface
@app.route('/chatbot')
def chatbot():
    return send_from_directory('static', 'chatbot.html')

# This simplifies deployment - the app can be directly run by Render
if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)