# Modular RAG Chatbot

A modular chatbot implementation with Retrieval Augmented Generation (RAG) capabilities.

## Features

- Document ingestion and processing
- Pinecone vector database integration
- Embedding generation with Sentence Transformers
- RAG query system with Gemini 1.5 Pro
- Simple command-line chat interface
- YouTube content loader

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file based on `.env.example` with your API keys

## Usage

### Start the chatbot
```
python main.py
```

### Load YouTube content
```python
from rag_components.document_processor import DocumentProcessor
from rag_components.pinecone_client import PineconeClient
from rag_components.embedding_service import EmbeddingService
from rag_components.youtube_loader import YouTubeLoader

# Initialize components
pinecone_client = PineconeClient(api_key="YOUR_API_KEY", environment="YOUR_ENV", index_name="YOUR_INDEX")
embedding_service = EmbeddingService()
document_processor = DocumentProcessor(embedding_service=embedding_service, vector_store=pinecone_client)
youtube_loader = YouTubeLoader(api_key="YOUR_API_KEY", channel_id="CHANNEL_ID", max_videos=20)

# Load and process YouTube videos
youtube_loader.load_and_process(document_processor)
```

## System Architecture

The system is built with modularity in mind and consists of the following components:

1. **DocumentProcessor**: Handles text splitting and document processing
2. **PineconeClient**: Interface with Pinecone vector database
3. **EmbeddingService**: Generates embeddings for text
4. **RAGEngine**: Core RAG implementation for answering queries
5. **ChatInterface**: Simple CLI for interacting with the system
6. **YouTubeLoader**: Loads content from YouTube for ingestion

## Extending the System

You can extend this system by:

1. Adding new document loaders (PDFs, web pages, etc.)
2. Implementing different embedding models
3. Creating a web interface instead of CLI
4. Adding conversation history and context management
5. Implementing different LLM providers