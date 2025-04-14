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

## Document Upload Guide

### 1. PDF Documents

Use the REST API endpoint:
```bash
curl -X POST -F "file=@/path/to/your/document.pdf" http://localhost:5000/api/documents/pdf
```

Or using Python requests:
```python
import requests

url = "http://localhost:5000/api/documents/pdf"
files = {'file': open('path/to/document.pdf', 'rb')}
response = requests.post(url, files=files)
print(response.json())
```

### 2. Text Documents

Using the REST API:
```bash
curl -X POST -H "Content-Type: application/json" \
     -d '{"text": "Your text content", "metadata": {"title": "Document Title"}}' \
     http://localhost:5000/api/documents
```

Using Python requests:
```python
import requests

url = "http://localhost:5000/api/documents"
data = {
    "text": "Your text content",
    "metadata": {
        "title": "Document Title",
        "source": "manual_upload"
    }
}
response = requests.post(url, json=data)
print(response.json())
```

### 3. YouTube Content

```python
from rag_components.youtube_loader import YouTubeLoader
from rag_components.document_processor import DocumentProcessor

# Initialize components
document_processor = current_app.config['COMPONENTS']['document_processor']
youtube_loader = YouTubeLoader(
    api_key=os.getenv('YOUTUBE_API_KEY')
)

# Load from video URL
video_url = "https://youtube.com/watch?v=your_video_id"
doc_id = youtube_loader.load_video(
    url=video_url,
    document_processor=document_processor
)

# Load from channel
channel_id = "YOUR_CHANNEL_ID"
doc_ids = youtube_loader.load_channel(
    channel_id=channel_id,
    max_videos=10,
    document_processor=document_processor
)
```

### 4. Setting Up Vector Store

Before uploading documents, ensure your Pinecone index is created:

```bash
# From project root
python scripts/create_pinecone_index.py
```

Required environment variables in `.env`:
```plaintext
PINECONE_API_KEY=your_api_key
PINECONE_ENVIRONMENT=your_region # e.g., us-east-1
PINECONE_INDEX_NAME=your_index_name
YOUTUBE_API_KEY=your_youtube_key  # Only for YouTube loader
```

### 5. Managing Documents

Delete a document:
```bash
curl -X DELETE http://localhost:5000/api/documents/{document_id}
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