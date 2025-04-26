# rag_components/rag_engine.py
import google.generativeai as genai
from typing import List, Dict, Any, Optional

class RAGEngine:
    def __init__(self, embedding_service, vector_store, llm_api_key):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        
        # Initialize Gemini API
        genai.configure(api_key=llm_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
    
    def answer_query(self, query: str, context: Optional[List[Dict[str, str]]] = None, top_k: int = 5) -> str:
        """
        Answer a query using RAG technique with optional conversation history
        
        Args:
            query: The user's question
            context: Optional list of previous conversation messages
            top_k: Number of relevant documents to retrieve
        """
        # Generate embedding for the query
        query_embedding = self.embedding_service.get_embedding(query)
        
        # Retrieve relevant documents
        results = self.vector_store.query(vector=query_embedding, top_k=top_k)
        
        # Extract contexts from search results
        doc_contexts = []
        for match in results['matches']:
            if 'text' in match['metadata']:
                doc_contexts.append(match['metadata']['text'])
        
        # Create a prompt with the retrieved context and conversation history
        prompt = self._create_prompt(query, doc_contexts, context)
        
        # Generate response using LLM
        response = self.model.generate_content(prompt)
        
        return response.text
    
    def _create_prompt(self, query: str, doc_contexts: List[str], conv_context: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Create a prompt using the query, retrieved contexts, and conversation history
        
        Args:
            query: The user's question
            doc_contexts: List of relevant document contexts
            conv_context: Optional list of previous conversation messages
        """
        # Format document contexts (silently used but not mentioned)
        doc_context_str = "\n\n".join([f"{context}" for i, context in enumerate(doc_contexts)])
        
        # Format conversation history if available
        conv_history = ""
        if conv_context:
            conv_history = "\nPrevious conversation:\n"
            for msg in conv_context:
                role = msg["role"].capitalize()
                content = msg["content"]
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

        Special instructions:
        - Always respond to greetings warmly (like "hello", "hi", "good morning", etc.)
        - For greetings, introduce yourself as a Learning Assistant ready to help with educational questions
        - If a message is just a greeting, respond with a friendly welcome and ask what educational topic they need help with
        - For small talk, respond briefly but always guide the conversation back to educational topics

        {conv_history}
        Student: {query}

        Assistant: 

        [Use this knowledge to help: {doc_context_str}]
        """
        
        return prompt