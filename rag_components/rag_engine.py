# rag_components/rag_engine.py
import google.generativeai as genai
from typing import List, Dict, Any

class RAGEngine:
    def __init__(self, embedding_service, vector_store, llm_api_key):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        
        # Initialize Gemini API
        genai.configure(api_key=llm_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
    
    def answer_query(self, query: str, top_k: int = 5) -> str:
        """Answer a query using RAG technique"""
        # Generate embedding for the query
        query_embedding = self.embedding_service.get_embedding(query)
        
        # Retrieve relevant documents
        results = self.vector_store.query(vector=query_embedding, top_k=top_k)
        
        # Extract contexts from search results
        contexts = []
        for match in results['matches']:
            if 'text' in match['metadata']:
                contexts.append(match['metadata']['text'])
        
        # Create a prompt with the retrieved context
        prompt = self._create_prompt(query, contexts)
        
        # Generate response using LLM
        response = self.model.generate_content(prompt)
        
        return response.text
    
    def _create_prompt(self, query: str, contexts: List[str]) -> str:
        """Create a prompt using the query and retrieved contexts"""
        context_str = "\n\n".join([f"Context {i+1}: {context}" for i, context in enumerate(contexts)])
        
        prompt = f"""
        You are a helpful assistant providing accurate information based on the given contexts.
        
        CONTEXTS:
        {context_str}
        
        QUESTION: {query}
        
        Based only on the contexts provided, please answer the question. If the answer cannot be determined from the contexts, say so clearly.
        """
        
        return prompt