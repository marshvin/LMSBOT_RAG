import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    
    # For Context and also for LLM
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Alternative LLM
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # Pinecone Setup
    PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
    PINECONE_ENVIRONMENT = os.getenv('PINECONE_ENVIRONMENT')
    PINECONE_INDEX_NAME = os.getenv('PINECONE_INDEX_NAME') 
    
    # SharePoint Configuration
    SHAREPOINT_SITE_URL = os.getenv("SHAREPOINT_SITE_URL")
    SHAREPOINT_CLIENT_ID = os.getenv("SHAREPOINT_CLIENT_ID")
    SHAREPOINT_CLIENT_SECRET = os.getenv("SHAREPOINT_CLIENT_SECRET")
    
    # RDS Config
    RDS_DB_NAME= os.getenv('RDS_DB_NAME')
    RDS_USER= os.getenv('RDS_USER')
    RDS_PASSWORD= os.getenv('RDS_PASSWORD')
    RDS_HOST= os.getenv('RDS_HOST')
    RDS_PORT=5432  
    
    # Google Slides Configuration
    GOOGLE_SERVICE_ACCOUNT_EMAIL = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
    GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    GOOGLE_SLIDE_IDS = os.getenv("GOOGLE_SLIDE_IDS", "").split(",")
    
    # Transcription Configuration
    WHISPER_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # RAG Parameters
    RAG_TOP_K = 3  # Number of context chunks to retrieve
    MAX_CONTEXT_LENGTH = 4000  # Truncate context if needed