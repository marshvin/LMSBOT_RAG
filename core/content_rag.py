from config.config import Config
from llama_index import VectorStoreIndex
from llama_index.vector_stores import PineconeVectorStore
from services.llm_service import LLMService
from services.youtube_service import YouTubeService
from services.sharepoint_service import SharePointVideoService
# from services.slides_service import GoogleSlidesService
# from services.document_service import DocumentService
import pinecone
from typing import List, Dict

class ContentRagPipeline:
    def __init__(self):
        
        # Initialize services
        self.llm_service = LLMService()
        self.youtube = YouTubeService(Config.YOUTUBE_API_KEY) if Config.YOUTUBE_API_KEY else None
        self.sharepoint = SharePointVideoService() if Config.SHAREPOINT_CLIENT_ID else None
        # self.slides = GoogleSlidesService() if Config.GOOGLE_CREDENTIALS_FILE else None
        
        # Initialize vector store
        pinecone.init(
            api_key=Config.PINECONE_API_KEY,
            environment=Config.PINECONE_ENVIRONMENT
        )
        self.vector_store = PineconeVectorStore(
            pinecone.Index(Config.PINECONE_INDEX_NAME),
            embed_model=self.llm_service.get_embedding_model()
        )
        self.index = None

    def build_index(self):
        """Build index using Gemini embeddings"""
        documents = self._load_all_documents()
        self.index = VectorStoreIndex.from_documents(
            documents,
            vector_store=self.vector_store
        )

    def query(self, question: str, top_k: int = 3) -> Dict:
        """Enhanced RAG query with Gemini"""
        if not self.index:
            raise ValueError("Index not built - call build_index() first")
        
        # 1. Retrieve relevant context
        retriever = self.index.as_retriever(similarity_top_k=top_k)
        retrieved_nodes = retriever.retrieve(question)
        
        # 2. Format context with source metadata
        context = "\n\n".join([
            f"Source {i+1} ({node.metadata['source_type']}): {node.text}\n"
            f"Reference: {self._get_source_link(node.metadata)}"
            for i, node in enumerate(retrieved_nodes)
        ])
        
        # 3. Generate response with Gemini
        response = self.llm_service.generate(
            prompt=question,
            context=f"Use these sources to answer:\n{context}"
        )
        
        return {
            "answer": response,
            "sources": [
                {
                    "content": node.text,
                    "title": node.metadata.get('title'),
                    "url": self._get_source_link(node.metadata),
                    "type": node.metadata['source_type'],
                    "confidence": node.score
                }
                for node in retrieved_nodes
            ]
        }

    def _get_source_link(self, metadata: Dict) -> str:
        """Generate source-specific links"""
        if metadata['source_type'] == "youtube":
            return f"{metadata['url']}?t={int(metadata['start_time'])}"
        # elif metadata['source_type'] == "slides":
        #     return f"{metadata['url']}#slide=id.p{metadata['slide_number'] - 1}"
        return metadata['url']