# rag_components/rag_engine.py
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import time
import re
import gc

class RAGEngine:
    def __init__(self, embedding_service, vector_store, llm_api_key, use_cache=False):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        
        # Initialize Gemini API
        genai.configure(api_key=llm_api_key)
        # Don't store the model - create it when needed
        self.llm_api_key = llm_api_key
        
        # Cache for embeddings - only used if use_cache is True
        self._embedding_cache = {} if use_cache else None
        self._max_cache_entries = 10  # Further reduced from 20
        self._use_cache = use_cache
        
        # Default generation config with timeouts
        self.generation_config = {
            "max_output_tokens": 1500,  
            "temperature": 0.3,  
            "top_p": 0.92,
            "top_k": 40
        }
    
    def answer_query(self, query: str, course: Optional[str] = None, context: Optional[List[Dict[str, str]]] = None, 
                     top_k: int = 3, source_filter: Optional[str] = None) -> str:
        """
        Answer a query using RAG technique with optional filtering
        
        Args:
            query: The user's question
            course: Optional course ID/name to filter results by
            context: Optional list of previous conversation messages
            top_k: Number of relevant documents to retrieve
            source_filter: Optional filter for source type (e.g., "youtube", "pdf")
        """
        try:
            # Check if the query is specifically about videos
            query_lower = query.lower().strip()
            is_video_query = any(phrase in query_lower for phrase in 
                ["video", "youtube", "watch", "tutorial", "lecture", "recording"])
            
            # Check if the query is specifically about the course
            is_course_query = any(phrase in query_lower for phrase in 
                ["this course", "the course", "course content", "about course"])
            
            # Check if this is a greeting without specific question
            if self._is_greeting(query) and not context:
                if course:
                    return f"Hi there! I'm your Learning Assistant for {course}. What would you like to learn today?"
                else:
                    return "Hi there! I'm your Learning Assistant, ready to help with your course. What would you like to learn today?"
            
            # Generate embedding for the query - use cache if enabled and available
            query_embedding = None
            if self._use_cache and self._embedding_cache is not None and query in self._embedding_cache:
                query_embedding = self._embedding_cache[query]
            else:
                query_embedding = self.embedding_service.get_embedding(query)
                # Cache the embedding if caching is enabled
                if self._use_cache and self._embedding_cache is not None:
                    if len(self._embedding_cache) > self._max_cache_entries:
                        self._embedding_cache.clear()
                    self._embedding_cache[query] = query_embedding
            
            # Create filter parameters
            filter_params = {}
            
            # Add course filter if provided
            if course:
                filter_params["course"] = course
            
            # Add source filter if provided or if query is specifically about videos
            if source_filter:
                filter_params["source"] = source_filter
            elif is_video_query:
                filter_params["source"] = "youtube"
            
            # Add timeout for vector store query
            start_time = time.time()
            
            # Execute query with filters
            results = self.vector_store.query(
                vector=query_embedding, 
                top_k=top_k,
                filter_params=filter_params if filter_params else None
            )
            
            # Special handling for video queries with no results
            if is_video_query and not results['matches']:
                if course:
                    return f"I couldn't find any video content for your question in the {course} course. Either no videos have been added to this course, or your question doesn't match the video content available."
                else:
                    return "I couldn't find any video content that matches your question. Please try a different question or check if videos have been added to the course."
            
            # For course-specific queries, don't do global fallback search
            should_fallback = not (is_course_query or is_video_query)
            
            # If no results and course filter was applied, try checking if course exists
            if not results['matches'] and course:
                # First check if any documents exist for this course
                basic_course_check = self.vector_store.query(
                    vector=query_embedding, 
                    top_k=1,
                    filter_params={"course": course}
                )
                
                # If the course has no documents at all, inform the user
                if not basic_course_check['matches']:
                    return f"The course '{course}' doesn't have any materials available yet. Please check back later when content has been added."
                
                # If we're still here, the course exists but no matches for this specific query and filters
                
                # If this was a video query, we already handled it above
                if is_video_query:
                    pass  # Already handled above
                # If it was a course query, don't fall back
                elif is_course_query:
                    return f"I don't have specific information about the course '{course}' content that matches your query. Please check with your instructor for more details."
                # Otherwise, we can try without source filter but keeping course filter
                elif should_fallback and "source" in filter_params:
                    # Try again without source filter
                    filter_params.pop("source")
                    results = self.vector_store.query(
                        vector=query_embedding, 
                        top_k=top_k,
                        filter_params=filter_params
                    )
            
            # Limit processing time
            if time.time() - start_time > 10:
                return "Sorry, the search took too long. Please try a more specific question."
            
            # Extract contexts from search results
            doc_contexts = []
            sources_used = set()
            
            for match in results['matches']:
                if 'text' in match['metadata']:
                    text = match['metadata']['text']
                    source_type = match['metadata'].get('source', 'unknown')
                    sources_used.add(source_type)
                    
                    # Add source metadata if available
                    if 'doc_name' in match['metadata']:
                        source_info = f"Source: {match['metadata']['doc_name']}"
                        if 'course' in match['metadata']:
                            source_info += f" ({match['metadata']['course']})"
                        if source_type == 'youtube':
                            source_info += " [Video]"
                        text = f"{text}\n[{source_info}]"
                    
                    # Limit text length to reduce memory usage
                    if len(text) > 500:
                        text = text[:500] + "..."
                    doc_contexts.append(text)
            
            # If no contexts found, inform the user
            if not doc_contexts:
                if course:
                    if is_video_query:
                        return f"I couldn't find any video content for your question in the {course} course. Perhaps no videos have been added for this topic."
                    elif is_course_query:
                        return f"I don't have specific information about the course '{course}' yet. Please check with your instructor for course details."
                    else:
                        return f"I couldn't find any relevant information for your question in the {course} course materials. Could you try rephrasing your question or asking about a different topic?"
                else:
                    return "I couldn't find any relevant information for your question in our learning materials. Could you try rephrasing your question or asking about a different topic?"
            
            # Set source type indicator for the prompt
            source_indicator = ""
            if "youtube" in sources_used and len(sources_used) == 1:
                source_indicator = "You are answering based on video content. "
            elif "pdf" in sources_used and len(sources_used) == 1:
                source_indicator = "You are answering based on document content. "
            
            # Create a prompt with the retrieved context and conversation history
            prompt = self._create_prompt(
                query=query, 
                doc_contexts=doc_contexts, 
                conv_context=context, 
                course=course,
                source_indicator=source_indicator
            )
            
            # Initialize model just when needed
            model = genai.GenerativeModel('gemini-1.5-pro')
            
            # Generate response using LLM with timeout
            start_time = time.time()
            response = model.generate_content(
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
            
            # Clean up to save memory
            del prompt
            del model
            gc.collect()
            
            return response.text
            
        except Exception as e:
            # Return a friendly error message
            return f"I'm sorry, I encountered an error while processing your question. Please try again with a different question. If this persists, please contact support."
    
    def clear_cache(self):
        """Clear the embedding cache if it exists"""
        if self._embedding_cache is not None:
            self._embedding_cache.clear()
    
    def _is_greeting(self, text: str) -> bool:
        """
        Check if the message is just a greeting without any specific question
        """
        text = text.lower().strip()
        greetings = [
            r'\bhello\b', r'\bhi\b', r'\bhey\b', r'\bgreetings\b', 
            r'\bgood morning\b', r'\bgood afternoon\b', r'\bgood evening\b',
            r'\bhowdy\b', r'\bola\b', r'\bwhat\'s up\b', r'\byo\b'
        ]
        
        # Check if the message contains only greetings
        if any(re.search(pattern, text) for pattern in greetings):
            # Check if the message is short (likely just a greeting)
            if len(text.split()) < 5:
                return True
            
            # Check if there's a question mark (indicating an actual question)
            if '?' not in text:
                # Look for question keywords
                question_words = ['what', 'why', 'how', 'when', 'where', 'who', 'which', 'can you', 'could you', 'explain']
                # If none of the question words are present, it's likely just a greeting
                return not any(word in text for word in question_words)
        
        return False
    
    def _create_prompt(self, query: str, doc_contexts: List[str], conv_context: Optional[List[Dict[str, str]]] = None, 
                      course: Optional[str] = None, source_indicator: str = "") -> str:
        """
        Create a prompt using the query, retrieved contexts, and conversation history
        
        Args:
            query: The user's question
            doc_contexts: List of relevant document contexts
            conv_context: Optional list of previous conversation messages
            course: Optional course identifier for context
            source_indicator: Optional indicator of source type (video/document)
        """
        # Format document contexts (silently used but not mentioned)
        # Limit the number of contexts to reduce token usage
        if len(doc_contexts) > 2:
            doc_contexts = doc_contexts[:2]
            
        doc_context_str = "\n\n".join([f"{context}" for i, context in enumerate(doc_contexts)])
        
        # Format conversation history if available - limit to last 2 messages to save memory
        conv_history = ""
        if conv_context:
            # Only keep most recent messages - reduced from 3 to 2
            recent_messages = conv_context[-2:] if len(conv_context) > 2 else conv_context
            conv_history = "\nPrevious conversation:\n"
            for msg in recent_messages:
                role = msg["role"].capitalize() if "role" in msg else "Unknown"
                # Truncate content to reduce token usage - reduced from 200 to 150
                content = msg.get("content", "")
                if content and len(content) > 150:
                    content = content[:150] + "..."
                conv_history += f"{role}: {content}\n"
        
        # Add course context if available
        course_context = f"You are answering questions specifically about the '{course}' course. " if course else ""
        
        # Check if the query seems to warrant a detailed response
        is_complex_query = any(word in query.lower() for word in [
            "explain", "describe", "how", "why", "what is", "what are", "difference", "compare", "list", "steps", "process"
        ])
        
        # Customized response formatting guidance based on query type
        response_format_guidance = """
        Response format:
        - For complex topics, use a structured approach with clear explanations
        - Use bullet points or numbered lists when explaining multiple concepts, steps, or examples
        - Include examples where helpful
        - Break down complex ideas into digestible parts
        - Be conversational but thorough
        - Provide comprehensive answers without being overly verbose
        """
        
        # Simplified prompt to save tokens
        prompt = f"""
        You are a dedicated Learning Assistant, committed to helping students excel in their educational journey. {course_context}{source_indicator}Your purpose is to:

        1. Guide students through their academic challenges
        2. Explain concepts clearly and comprehensively

        {response_format_guidance}

        STRICT LIMITATIONS:
        - You can ONLY answer questions directly related to the provided context materials
        - NEVER invent or hallucinate information not present in the context materials
        - If a question is about videos and you don't have video context, say: "I don't have any video content that answers your question."
        - If a question is about politics, sports, entertainment, current events, or anything outside your provided context, respond with: "I'm sorry, I can only assist with questions related to your learning materials. Please ask me something about your course content."
        - NEVER create or fabricate information that is not in your context
        - DO NOT answer general knowledge questions that aren't covered in your learning materials
        - If you don't have enough information to answer a question based on your context, politely say: "I don't have enough information to answer that question based on your learning materials."
        - NEVER mention what materials or knowledge you have access to
        - NEVER list topics you can help with - let the student ask specific questions
        - If asked about the course and you don't have specific course information, say: "I don't have detailed information about this course yet. Please check with your instructor for the course syllabus and requirements."
        - Stay strictly focused on the retrieved context content and don't make up details

        Core principles:
        - Focus exclusively on educational content from your context
        - Use clear, student-friendly language
        - Keep responses focused on ONLY what the student is asking about
        - Never make up information about courses you don't have data for
        - Provide appropriately detailed responses with examples and structured formatting when helpful

        {conv_history}
        Student: {query}

        Assistant: 

        [Use this knowledge to help without explicitly mentioning you're drawing from specific materials: {doc_context_str}]
        """
        
        return prompt