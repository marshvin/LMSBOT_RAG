# rag_components/rag_engine.py
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import time
import re
import gc
import logging
import threading
import json

# Add imports for fallback options - make OpenAI import conditional
import os
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('RAGEngine')

class RAGEngine:
    def __init__(self, embedding_service, vector_store, llm_api_key, use_cache=False, openai_api_key=None, primary_llm="gemini"):
        """
        Initialize the RAG Engine with required services
        
        Args:
            embedding_service: Service for creating embeddings
            vector_store: Vector database for storing and querying embeddings
            llm_api_key: API key for Gemini LLM
            use_cache: Whether to use embedding caching (default: False)
            openai_api_key: Optional API key for OpenAI
            primary_llm: Which LLM to use as primary ("gemini" or "openai")
        """
        try:
            self.embedding_service = embedding_service
            self.vector_store = vector_store
            
            # Initialize Gemini API
            self.gemini_available = False
            if llm_api_key:
                try:
                    genai.configure(api_key=llm_api_key)
                    self.gemini_available = True
                    self.llm_api_key = llm_api_key
                    logger.info("Gemini API initialized successfully")
                except Exception as e:
                    logger.warning(f"Gemini API initialization failed: {str(e)}")
            
            # Initialize OpenAI
            self.openai_available = OPENAI_AVAILABLE and openai_api_key is not None
            self.openai_api_key = openai_api_key
            self.openai_client = None
            if self.openai_available:
                try:
                    self.openai_client = openai.OpenAI(api_key=openai_api_key)
                    logger.info("OpenAI API initialized successfully")
                except Exception as e:
                    logger.warning(f"OpenAI initialization failed: {str(e)}")
                    self.openai_available = False
            
            # Set primary LLM based on availability and preference
            self.primary_llm = primary_llm
            if primary_llm == "openai" and not self.openai_available:
                logger.warning("OpenAI set as primary but not available, falling back to Gemini")
                self.primary_llm = "gemini"
            elif primary_llm == "gemini" and not self.gemini_available:
                logger.warning("Gemini set as primary but not available, falling back to OpenAI")
                self.primary_llm = "openai" if self.openai_available else None
            
            logger.info(f"Using {self.primary_llm} as primary LLM")
            
            # Cache for embeddings - only used if use_cache is True
            self._embedding_cache = {} if use_cache else None
            self._max_cache_entries = 10
            self._use_cache = use_cache
            
            # Default generation config with timeouts
            self.generation_config = {
                "max_output_tokens": 800,  # Reduced from 1500
                "temperature": 0.3,  
                "top_p": 0.92,
                "top_k": 40
            }
            
            # Rate limiting - track last request time
            self._last_request_time = 0
            self._request_spacing = 1.0  # Minimum seconds between requests
            self._request_lock = threading.Lock()
            
            logger.info("RAGEngine initialized successfully with optimized settings")
        except Exception as e:
            logger.error(f"Error initializing RAGEngine: {str(e)}")
            raise
    
    def answer_query(self, query: str, course: Optional[str] = None, context: Optional[List[Dict[str, str]]] = None, 
                     top_k: int = 2, source_filter: Optional[str] = None) -> str:
        """
        Answer a query using RAG technique with optional filtering
        
        Args:
            query: The user's question
            course: Optional course ID/name to filter results by
            context: Optional list of previous conversation messages
            top_k: Number of relevant documents to retrieve (reduced from 3 to 2)
            source_filter: Optional filter for source type (e.g., "youtube", "pdf")
        """
        try:
            logger.info(f"Processing query: '{query}' for course: '{course}'")
            
            # Special handling for "Shule" course - search across all courses
            if course and course.lower() == "shule":
                logger.info("Detected 'Shule' course - searching across all courses")
                # Generate embedding for the query
                query_embedding = self.embedding_service.get_embedding(query)
                
                # Query vector store without course filter to get all relevant courses
                results = self.vector_store.query(
                    vector=query_embedding,
                    top_k=5,  # Increased to get more course variety
                    filter_params={"source": source_filter} if source_filter else None
                )
                
                # Extract unique courses from results
                courses_found = set()
                for match in results.get('matches', []):
                    if 'metadata' in match and 'course' in match['metadata']:
                        course_name = match['metadata']['course']
                        if course_name.lower() != "shule":  # Don't include Shule itself
                            courses_found.add(course_name)
                
                if courses_found:
                    courses_list = "\n".join([f"- {course}" for course in sorted(courses_found)])
                    return f"I found the following courses that might interest you:\n\n{courses_list}\n\nWould you like to know more about any specific course?"
                else:
                    return "I couldn't find any specific courses related to your query. Could you try rephrasing your question?"
            
            # Check if the query is specifically about videos
            query_lower = query.lower().strip()
            is_video_query = any(word in query_lower for word in 
                ["video", "youtube", "watch", "tutorial", "lecture", "recording"])
            
            # Check if the query is specifically about the course
            is_course_query = any(phrase in query_lower for phrase in 
                ["this course", "the course", "course content", "about course"])
            
            # Check if query is about generating H5P content
            is_h5p_query = "h5p" in query_lower or "generate quiz" in query_lower or "create assessment" in query_lower
            
            # Handle H5P content generation
            if is_h5p_query:
                return self.generate_h5p_content(query, course)
            
            # Check if this is a greeting without specific question
            if self._is_greeting(query) and not context:
                if course:
                    return f"Hi there! I'm your Learning Assistant for {course}. What would you like to learn today?"
                else:
                    return "Hi there! I'm your Learning Assistant, ready to help with your course. What would you like to learn today?"
            
            # Generate embedding for the query - use cache if enabled and available
            logger.info("Generating query embedding")
            query_embedding = None
            try:
                if self._use_cache and self._embedding_cache is not None and query in self._embedding_cache:
                    query_embedding = self._embedding_cache[query]
                    logger.info("Using cached embedding")
                else:
                    query_embedding = self.embedding_service.get_embedding(query)
                    logger.info("Generated new embedding")
                    # Cache the embedding if caching is enabled
                    if self._use_cache and self._embedding_cache is not None:
                        if len(self._embedding_cache) > self._max_cache_entries:
                            self._embedding_cache.clear()
                        self._embedding_cache[query] = query_embedding
            except Exception as e:
                logger.error(f"Error generating embedding: {str(e)}")
                return "I'm having trouble processing your question. Please try again later."
            
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
            
            logger.info(f"Querying vector store with filters: {filter_params}")
            
            # Add timeout for vector store query
            start_time = time.time()
            
            # Execute query with filters
            try:
                results = self.vector_store.query(
                    vector=query_embedding, 
                    top_k=top_k,  # Reduced from 3 to 2
                    filter_params=filter_params if filter_params else None
                )
                logger.info(f"Vector store query returned {len(results.get('matches', []))} results")
            except Exception as e:
                logger.error(f"Error querying vector store: {str(e)}")
                return "I'm having trouble searching for information related to your question. Please try again later."
            
            # Special handling for video queries with no results
            if is_video_query and not results.get('matches', []):
                if course:
                    return f"I couldn't find any video content for your question in the {course} course. Either no videos have been added to this course, or your question doesn't match the video content available."
                else:
                    return "I couldn't find any video content that matches your question. Please try a different question or check if videos have been added to the course."
            
            # For course-specific queries, don't do global fallback search
            should_fallback = not (is_course_query or is_video_query)
            
            # If no results and course filter was applied, try checking if course exists
            if not results.get('matches', []) and course:
                logger.info(f"No results found for course '{course}', checking if course exists")
                # First check if any documents exist for this course
                try:
                    basic_course_check = self.vector_store.query(
                        vector=query_embedding, 
                        top_k=1,
                        filter_params={"course": course}
                    )
                    
                    # If the course has no documents at all, inform the user
                    if not basic_course_check.get('matches', []):
                        logger.info(f"No documents found for course '{course}'")
                        return f"The course '{course}' doesn't have any materials available yet. Please check back later when content has been added."
                    
                    # If we're still here, the course exists but no matches for this specific query and filters
                    logger.info(f"Course '{course}' exists but no matches for query")
                    
                    # If this was a video query, we already handled it above
                    if is_video_query:
                        pass  # Already handled above
                    # If it was a course query, don't fall back
                    elif is_course_query:
                        return f"I don't have specific information about the course '{course}' content that matches your query. Please check with your instructor for more details."
                    # Otherwise, we can try without source filter but keeping course filter
                    elif should_fallback and "source" in filter_params:
                        # Try again without source filter
                        logger.info("Attempting fallback search without source filter")
                        filter_params.pop("source")
                        results = self.vector_store.query(
                            vector=query_embedding, 
                            top_k=top_k,
                            filter_params=filter_params
                        )
                except Exception as e:
                    logger.error(f"Error during course existence check: {str(e)}")
                    return "I'm having trouble accessing course information. Please try again later."
            
            # Limit processing time
            if time.time() - start_time > 10:
                logger.warning("Vector store query timeout")
                return "Sorry, the search took too long. Please try a more specific question."
            
            # Extract contexts from search results
            doc_contexts = []
            sources_used = set()
            
            for match in results.get('matches', []):
                if 'metadata' in match and 'text' in match['metadata']:
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
                    
                    # Limit text length more strictly to reduce token usage
                    if len(text) > 300:  # Reduced from 500
                        text = text[:300] + "..."
                    doc_contexts.append(text)
            
            logger.info(f"Extracted {len(doc_contexts)} contexts from search results")
            
            # If no contexts found, inform the user
            if not doc_contexts:
                logger.info("No relevant contexts found")
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
            logger.info("Creating prompt for LLM")
            prompt = self._create_prompt(
                query=query, 
                doc_contexts=doc_contexts, 
                conv_context=context, 
                course=course,
                source_indicator=source_indicator
            )
            
            # Implement rate limiting for API calls
            with self._request_lock:
                current_time = time.time()
                time_since_last_request = current_time - self._last_request_time
                
                if time_since_last_request < self._request_spacing:
                    # Wait if needed to avoid hitting rate limits
                    sleep_time = max(0, self._request_spacing - time_since_last_request)
                    logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                    time.sleep(sleep_time)
                
                # Update last request time
                self._last_request_time = time.time()
            
            # Generate response using configured LLM
            logger.info(f"Generating response with {self.primary_llm}")
            
            # Different LLM handling based on primary choice
            if self.primary_llm == "openai" and self.openai_available:
                return self._generate_openai_response(prompt)
            elif self.primary_llm == "gemini" and self.gemini_available:
                return self._generate_gemini_response(prompt)
            else:
                # If no LLM is available, use simple response
                logger.warning("No LLM is available, using simple response fallback")
                return self._create_simple_response(doc_contexts, query)
            
        except Exception as e:
            logger.error(f"Unhandled exception in answer_query: {str(e)}")
            return f"I'm sorry, I encountered an error while processing your question. Please try again with a different question. If this persists, please contact support."
    
    def _generate_openai_response(self, prompt: str) -> str:
        """Generate response using OpenAI"""
        try:
            start_time = time.time()
            
            # Use gpt-3.5-turbo for better cost efficiency
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # More capable than instruct
                messages=[
                    {"role": "system", "content": "You are a helpful educational assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            # Check for timeout
            if time.time() - start_time > 20:
                logger.warning("OpenAI response timeout")
                return "I apologize, but processing your question took too long. Could you try a simpler question?"
            
            # Clean up to save memory
            del prompt
            gc.collect()
            
            logger.info("Successfully generated OpenAI response")
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {str(e)}")
            
            # If OpenAI fails, try Gemini as fallback
            if self.gemini_available:
                logger.info("Trying Gemini as fallback")
                return self._generate_gemini_response(prompt)
            else:
                return "I'm having trouble generating a response. The AI service is currently experiencing issues."
    
    def _generate_gemini_response(self, prompt: str) -> str:
        """Generate response using Gemini"""
        try:
            # Initialize model just when needed
            model = genai.GenerativeModel('gemini-1.5-pro')
            
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
                logger.warning("Gemini response timeout")
                return "I apologize, but processing your question took too long. Could you try a simpler question?"
            
            # Clean up to save memory
            del prompt
            del model
            gc.collect()
            
            logger.info("Successfully generated Gemini response")
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating Gemini response: {str(e)}")
            
            # Try OpenAI fallback if available
            if self.openai_available:
                logger.info("Trying OpenAI as fallback")
                return self._generate_openai_response(prompt)
            
            # If both fail, use direct context response
            return self._create_simple_response([], "")
    
    def _handle_llm_error(self, error, prompt, doc_contexts, query):
        """Handle LLM errors with appropriate fallback strategies"""
        error_str = str(error).lower()
        logger.error(f"Error generating LLM response: {str(error)}")
                
        # Check if this is a rate limit error (429)
        if "429" in error_str or "quota" in error_str or "rate limit" in error_str:
            logger.info("Detected rate limit error, attempting fallback")
            
            # If primary is Gemini and hit rate limit, try OpenAI
            if self.primary_llm == "gemini" and self.openai_available:
                try:
                    logger.info("Trying OpenAI as fallback")
                    return self._generate_openai_response(prompt)
                except Exception as fallback_error:
                    logger.error(f"OpenAI fallback also failed: {str(fallback_error)}")
            
            # If primary is OpenAI and hit rate limit, try Gemini
            elif self.primary_llm == "openai" and self.gemini_available:
                try:
                    logger.info("Trying Gemini as fallback")
                    return self._generate_gemini_response(prompt)
                except Exception as fallback_error:
                    logger.error(f"Gemini fallback also failed: {str(fallback_error)}")
            
            # If all else fails, use simple response
            logger.info("Using direct context fallback")
            return self._create_simple_response(doc_contexts, query)
        
        # For other types of errors, return a generic message
        return "I'm having trouble generating a response to your question. This might be due to a temporary issue with our AI service. Please try again later."
    
    def _create_simple_response(self, doc_contexts: List[str], query: str) -> str:
        """Create a simple response directly from retrieved contexts when LLM is unavailable"""
        if not doc_contexts:
            return "I found information related to your question, but I'm having trouble processing it right now. Please try again later."
        
        # Use the most relevant context (first one) as basis for response
        context = doc_contexts[0]
        
        # Create a simple disclaimer about service limitations
        disclaimer = "I'm currently operating in lightweight mode. "
        
        # Extract key sentences from the context
        sentences = context.split('.')
        short_context = '. '.join(sentences[:3]) + '.'
        
        return f"{disclaimer}Based on the information I have: {short_context}"
    
    def generate_h5p_content(self, query: str, course: Optional[str] = None) -> str:
        """
        Generate H5P content based on the query and course context
        
        Args:
            query: The user's request for H5P content
            course: Optional course identifier for context
        """
        try:
            # First, extract what type of H5P content is requested
            content_type = self._determine_h5p_content_type(query)
            
            # Get relevant content from the course
            if course:
                # Generate embedding for the query
                query_embedding = self.embedding_service.get_embedding(query)
                
                # Query vector store with course filter
                results = self.vector_store.query(
                    vector=query_embedding,
                    top_k=3,  # Get more context for H5P generation
                    filter_params={"course": course}
                )
                
                # Extract relevant content
                doc_contexts = [match.get('metadata', {}).get('text', '') for match in results.get('matches', [])]
                
                # Create a prompt for the LLM
                prompt = f"""Generate an H5P {content_type} about {query} for the course '{course}'.
                Use the following course content as reference:
                {' '.join(doc_contexts)}
                
                The content should be in H5P JSON format, wrapped in ```json and ``` markers.
                Make sure the content is relevant to the course material and includes proper questions/answers.
                """
            else:
                prompt = f"""Generate an H5P {content_type} about {query}.
                The content should be in H5P JSON format, wrapped in ```json and ``` markers.
                Make sure the content is educational and includes proper questions/answers.
                """
            
            # Generate content using the primary LLM
            if self.primary_llm == "gemini" and self.gemini_available:
                h5p_content = self._generate_gemini_response(prompt)
            elif self.primary_llm == "openai" and self.openai_available:
                h5p_content = self._generate_openai_response(prompt)
            else:
                # Fallback to basic template
                if content_type == "quiz":
                    h5p_content = self._generate_quiz(query)
                elif content_type == "interactive_video":
                    h5p_content = self._generate_interactive_video(query)
                elif content_type == "course_presentation":
                    h5p_content = self._generate_course_presentation(query)
                else:
                    h5p_content = self._generate_quiz(query)
            
            # Ensure the content is properly formatted with JSON markers
            if "```json" not in h5p_content:
                h5p_content = f"```json\n{h5p_content}\n```"
            
            return h5p_content
            
        except Exception as e:
            logger.error(f"Error generating H5P content: {str(e)}")
            # Return a basic template as fallback
            return f"""```json
{{
    "title": "Quiz on {query}",
    "questions": [
        {{
            "question": "What is the main concept of {query}?",
            "type": "multichoice",
            "options": [
                "Option A - First key concept",
                "Option B - Alternative concept",
                "Option C - Related but incorrect concept",
                "Option D - Distractor"
            ],
            "correctAnswer": "Option A - First key concept"
        }}
    ]
}}
```"""
    
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
        if len(doc_contexts) > 1:  # Reduced from 2
            doc_contexts = doc_contexts[:1]  # Only use most relevant context
            
        doc_context_str = "\n\n".join([f"{context}" for i, context in enumerate(doc_contexts)])
        
        # Format conversation history if available - limit to last message to save tokens
        conv_history = ""
        if conv_context:
            # Only keep most recent message - reduced from 2 to 1
            recent_messages = conv_context[-1:] if len(conv_context) > 1 else conv_context
            conv_history = "\nPrevious conversation:\n"
            for msg in recent_messages:
                role = msg["role"].capitalize() if "role" in msg else "Unknown"
                # Truncate content to reduce token usage - reduced from 150 to 100
                content = msg.get("content", "")
                if content and len(content) > 100:
                    content = content[:100] + "..."
                conv_history += f"{role}: {content}\n"
        
        # Add course context if available
        course_context = f"You are answering questions specifically about the '{course}' course. " if course else ""
        
        # Simplified prompt to save tokens - remove unnecessary instructions
        prompt = f"""
        You are a Learning Assistant. {course_context}{source_indicator}Your purpose is to guide students and explain concepts clearly.

        LIMITATIONS:
        - Answer only based on the provided context
        - Don't invent information
        - Keep responses concise and to the point
        - Use structured explanations for complex topics

        {conv_history}
        Student: {query}

        Assistant: 

        [Use this knowledge: {doc_context_str}]
        """
        
        return prompt
    
    def _determine_h5p_content_type(self, query: str) -> str:
        """Determine what type of H5P content to generate based on query"""
        query_lower = query.lower()
        
        if any(term in query_lower for term in ["quiz", "questions", "test", "assessment"]):
            return "quiz"
        elif any(term in query_lower for term in ["video", "interactive video"]):
            return "interactive_video"
        elif any(term in query_lower for term in ["presentation", "slides"]):
            return "course_presentation"
        else:
            return "quiz"  # Default to quiz
    
    def _generate_quiz(self, query: str) -> str:
        """Generate an H5P quiz"""
        topic = query.replace("generate quiz", "").replace("create quiz", "").replace("h5p", "").strip()
        if not topic:
            topic = "the provided materials"
            
        quiz_template = {
            "title": f"Quiz on {topic}",
            "intro": f"Test your knowledge about {topic}",
            "questions": [
                {
                    "library": "H5P.MultiChoice 1.16",
                    "params": {
                        "question": f"What is the main concept of {topic}?",
                        "l10n": {
                            "scoreBarLabel": "You got :num out of :total points"
                        },
                        "answers": [
                            {
                                "text": "Option A - First key concept",
                                "correct": True
                            },
                            {
                                "text": "Option B - Alternative concept",
                                "correct": False
                            },
                            {
                                "text": "Option C - Related but incorrect concept",
                                "correct": False
                            },
                            {
                                "text": "Option D - Distractor",
                                "correct": False
                            }
                        ],
                        "behaviour": {
                            "enableRetry": True,
                            "enableSolutionsButton": True,
                            "enableCheckButton": True,
                            "type": "auto",
                            "singleAnswer": True
                        },
                        "confirmCheck": {
                            "header": "Finish ?",
                            "body": "Are you sure you want to finish ?",
                            "cancelLabel": "Cancel",
                            "confirmLabel": "Finish"
                        },
                        "confirmRetry": {
                            "header": "Retry ?",
                            "body": "Are you sure you want to retry ?",
                            "cancelLabel": "Cancel",
                            "confirmLabel": "Confirm"
                        },
                        "ui": {
                            "checkAnswerButton": "Check",
                            "showSolutionButton": "Show solution",
                            "tryAgainButton": "Retry"
                        }
                    },
                    "metadata": {
                        "contentType": "Multiple Choice",
                        "license": "U",
                        "title": f"Question about {topic}"
                    }
                }
            ],
            "overallFeedback": [
                {
                    "from": 0,
                    "to": 100
                }
            ],
            "text": "Your results:",
            "showSolutionsRequiresInput": True,
            "randomQuestions": False,
            "endGame": {
                "showResultPage": True,
                "showSolutionButton": True,
                "showRetryButton": True,
                "noResultMessage": "Finished",
                "message": "Your result:",
                "overallFeedback": [
                    {
                        "from": 0,
                        "to": 100
                    }
                ],
                "solutionButtonText": "Show solution",
                "retryButtonText": "Retry",
                "finishButtonText": "Finish",
                "showAnimations": False,
                "skipButtonText": "Skip video",
                "previousButtonText": "Previous slide",
                "nextButtonText": "Next slide",
                "closeButtonText": "Close",
                "textualProgress": "Question :num of :total",
                "templates": {
                    "solutionListTemplate": "<ul class='h5p-solution-list'>{{content}}</ul>",
                    "solutionItemTemplate": "<li class='h5p-solution-list-item'>{{content}}</li>"
                }
            }
        }
        
        return json.dumps(quiz_template, indent=2)
    
    def _generate_interactive_video(self, query: str) -> str:
        """Generate H5P interactive video template"""
        topic = query.replace("generate", "").replace("create", "").replace("interactive video", "").replace("h5p", "").strip()
        if not topic:
            topic = "the provided materials"
            
        video_template = {
            "title": f"Interactive Video about {topic}",
            "video": {
                "source": "YOUR_VIDEO_URL_HERE",
                "interactions": [
                    {
                        "time": "00:30",
                        "type": "multichoice",
                        "question": "What is the main concept introduced so far?",
                        "options": [
                            "Option A",
                            "Option B",
                            "Option C",
                            "Option D"
                        ],
                        "correctAnswer": "Option A"
                    },
                    {
                        "time": "01:30",
                        "type": "summary",
                        "content": "Key points covered so far"
                    },
                    {
                        "time": "02:45",
                        "type": "fill-in-blanks",
                        "question": "Complete the sentence about key terminology",
                        "text": "The main concept of [blank] is important because..."
                    }
                ]
            }
        }
        
        return json.dumps(video_template, indent=2)
    
    def _generate_course_presentation(self, query: str) -> str:
        """Generate H5P course presentation template"""
        topic = query.replace("generate", "").replace("create", "").replace("presentation", "").replace("slides", "").replace("h5p", "").strip()
        if not topic:
            topic = "the provided materials"
            
        presentation_template = {
            "title": f"Course Presentation: {topic}",
            "slides": [
                {
                    "title": f"{topic} - Key Concepts",
                    "type": "title"
                },
                {
                    "title": "Introduction",
                    "content": f"Brief overview of {topic}",
                    "type": "content"
                },
                {
                    "title": "Key Concept 1",
                    "content": "First major point about the topic",
                    "type": "interactive",
                    "interaction": {
                        "type": "multichoice",
                        "question": "What is the first key concept?",
                        "options": ["Option A", "Option B", "Option C"],
                        "correctAnswer": "Option A"
                    }
                },
                {
                    "title": "Key Concept 2",
                    "content": "Second major point",
                    "type": "interactive",
                    "interaction": {
                        "type": "drag-and-drop",
                        "question": "Match the terms to their definitions",
                        "items": [
                            {"term": "Term 1", "definition": "Definition 1"},
                            {"term": "Term 2", "definition": "Definition 2"}
                        ]
                    }
                },
                {
                    "title": "Summary",
                    "content": "Review of key points",
                    "type": "summary"
                }
            ]
        }
        
        return json.dumps(presentation_template, indent=2)
    
    def clear_cache(self):
        """Clear the embedding cache if it exists"""
        if self._embedding_cache is not None:
            self._embedding_cache.clear()
            logger.info("Embedding cache cleared")
    
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