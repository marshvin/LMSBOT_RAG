# RAG pipeline service

from typing import Dict, Any
from config.config import Config

from LMSBOT_RAG.services.vector_store import VectorStoreService
from LMSBOT_RAG.services.history_service import ConversationHistoryService
from LMSBOT_RAG.services.sharepoint_service import SharePointVideoService
from LMSBOT_RAG.services.transcription_service import WhisperTranscriptionService

class TrainingPipeline:
    def __init__(self, config: Dict[str, Any]):
               
        self.sharepoint = SharePointVideoService(
            config["SHAREPOINT_SITE"],
            config["SHAREPOINT_USER"],
            config["SHAREPOINT_PASSWORD"]
        )
        self.transcriber = WhisperTranscriptionService(
            config["OPENAI_API_KEY"]
        )
        self.vector_store = VectorStoreService(
            config["PINECONE_API_KEY"],
            config["PINECONE_INDEX"]
        )
        self.history = ConversationHistoryService(
            config["RDS_CONFIG"]
        )
    
    async def process_query(self, user_id: str, current_video_path: str, query: str):
        
        # 1. Get current video stream
        video_stream = self.sharepoint.get_video_stream(current_video_path)
        
        # 2. Transcribe in memory
        transcript = self.transcriber.transcribe_stream(video_stream)
        
        # 3. Update vector store
        self.vector_store.upsert_transcript(transcript, {
            "video_url": current_video_path,
            "user_id": user_id
        })
        
        # 4. Get conversation history
        history = self.history.get_history(user_id)
        
        # 5. Build augmented query
        augmented_query = f"""
        Conversation History:
        {self._format_history(history)}
        
        Current Video Context:
        {transcript['text']}
        
        User Question: {query}
        """
        
        # 6. Query vector store
        results = self.vector_store.query_context(augmented_query)
        
        # 7. Generate response
        response = self._generate_response(results)
        
        # 8. Log interaction
        self.history.log_interaction(
            user_id, query, response, 
            self._get_sources(results)
        )
        
        return response
    
    def _format_history(self, history):
        return "\n".join([f"Q: {q}\nA: {a}" for q, a in history])
    
    def _generate_response(self, results):
        context = "\n".join([n.text for n in results.nodes])
        # Use your preferred LLM here
        return f"Based on training materials: {context}"
    
    def _get_sources(self, results):
        return [{
            "video": n.metadata["video_url"],
            "timestamp": n.metadata["start"],
            "confidence": n.score
        } for n in results.nodes]