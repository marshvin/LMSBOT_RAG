# rag_components/rag_engine.py
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import time

class RAGEngine:
    def __init__(self, embedding_service, vector_store, llm_api_key):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        
        # Initialize Gemini API
        genai.configure(api_key=llm_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Cache for embeddings to reduce API calls
        self._embedding_cache = {}
        
        # Default generation config with timeouts
        self.generation_config = {
            "max_output_tokens": 1024, 
            "temperature": 0.2,
            "top_p": 0.9,
            "top_k": 40
        }
    
    def answer_query(self, query: str, context: Optional[List[Dict[str, str]]] = None, top_k: int = 3) -> str:
        """
        Answer a query using RAG technique with optional conversation history
        
        Args:
            query: The user's question
            context: Optional list of previous conversation messages
            top_k: Number of relevant documents to retrieve
        """
        try:
            # Generate embedding for the query - use cache if available
            if query in self._embedding_cache:
                query_embedding = self._embedding_cache[query]
            else:
                query_embedding = self.embedding_service.get_embedding(query)
                # Cache the embedding (limit cache size)
                if len(self._embedding_cache) > 100:
                    self._embedding_cache.clear()
                self._embedding_cache[query] = query_embedding
            
            # Add timeout for vector store query
            start_time = time.time()
            results = self.vector_store.query(vector=query_embedding, top_k=top_k)
            
            # Limit processing time
            if time.time() - start_time > 10:
                return "Sorry, the search took too long. Please try a more specific question."
            
            # Extract contexts from search results - limit length to reduce memory usage
            doc_contexts = []
            for match in results['matches']:
                if 'text' in match['metadata']:
                    text = match['metadata']['text']
                    # Limit text length to reduce memory usage
                    if len(text) > 1000:
                        text = text[:1000] + "..."
                    doc_contexts.append(text)
            
            # Create a prompt with the retrieved context and conversation history
            prompt = self._create_prompt(query, doc_contexts, context)
            
            # Generate response using LLM with timeout
            start_time = time.time()
            response = self.model.generate_content(
                prompt, 
                generation_config=self.generation_config,
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
                ]
            )
            
            # Check for timeout
            if time.time() - start_time > 20:
                return "I apologize, but processing your question took too long. Could you try a simpler question?"
            
            return response.text
            
        except Exception as e:
            # Return a friendly error message
            return f"I'm sorry, I encountered an error while processing your question. Please try again with a different question. If this persists, please contact support."
    
    def _create_prompt(self, query: str, doc_contexts: List[str], conv_context: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Create a prompt using the query, retrieved contexts, and conversation history
        
        Args:
            query: The user's question
            doc_contexts: List of relevant document contexts
            conv_context: Optional list of previous conversation messages
        """
        # Format document contexts (silently used but not mentioned)
        # Limit the number of contexts to reduce token usage
        if len(doc_contexts) > 2:
            doc_contexts = doc_contexts[:2]
            
        doc_context_str = "\n\n".join([f"{context}" for i, context in enumerate(doc_contexts)])
        
        # Format conversation history if available - limit to last 3 messages
        conv_history = ""
        if conv_context:
            # Only keep most recent messages
            recent_messages = conv_context[-3:] if len(conv_context) > 3 else conv_context
            conv_history = "\nPrevious conversation:\n"
            for msg in recent_messages:
                role = msg["role"].capitalize()
                # Truncate content to reduce token usage
                content = msg["content"]
                if len(content) > 200:
                    content = content[:200] + "..."
                conv_history += f"{role}: {content}\n"
        
        prompt = f"""
        You are a dedicated Learning Assistant, committed to helping students excel in their educational journey. Your purpose is to:

        1. Guide students through their academic challenges
        2. Explain concepts clearly and comprehensively
        3. Help students understand complex topics
        4. Provide relevant examples and practice problems
        5. Foster critical thinking and deep understanding

        Core principles:
        - Focus exclusively on educational content
        - Use clear, student-friendly language
        - Provide structured, easy-to-follow explanations
        - Encourage active learning and engagement
        - Maintain a supportive and patient teaching approach
        - Politely decline non-academic questions

        {conv_history}
        Student: {query}

        Assistant: 

        [Use this knowledge to help: {doc_context_str}]
        """
        
        return prompt