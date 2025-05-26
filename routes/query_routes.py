# routes/query_routes.py
from flask import Blueprint, request, jsonify, current_app
from uuid import uuid4
import time
import gc

# Import 
import redis
import json
import hashlib
import os



# Initialize Redis client once globally in your app setup
redis_client = redis.Redis(
    host='68.183.83.36',
    port=6379,
    password='@ShuleLMS*',
    db=0,
    decode_responses=True
)


def _make_cache_key(query_text, context):
    # Create a unique key based on query + context to cache results
    context_str = json.dumps(context, sort_keys=True)
    key_raw = f"{query_text}:{context_str}"
    return "rag_response_cache:" + hashlib.sha256(key_raw.encode()).hexdigest()


query_bp = Blueprint('query', __name__, url_prefix='/api')

# Stateless implementation - no in-memory cache

# @query_bp.route('/query', methods=['POST'])
# def query():
#     """Query endpoint for RAG responses without conversation memory"""
#     start_time = time.time()
    
#     try:
#         # Lazy load RAG engine only when needed
#         get_component = current_app.config['GET_COMPONENT']
#         rag_engine = get_component("rag_engine")
        
#         data = request.json
        
#         if not data or 'query' not in data:
#             return jsonify({
#                 "error": "Missing 'query' parameter"
#             }), 400
        
#         query_text = data['query']
        
#         # Get course information if provided
#         course = data.get('course')
        
#         # Get source filter if provided
#         source_filter = data.get('source')
        
#         # Detect video-specific queries
#         query_lower = query_text.lower()
#         is_video_query = any(word in query_lower for word in 
#             ["video", "youtube", "watch", "tutorial", "lecture", "recording"])
        
#         # If query is about videos but no source filter provided, add it
#         if is_video_query and not source_filter:
#             source_filter = "youtube"
        
#         # Input validation
#         if not query_text or len(query_text.strip()) == 0:
#             return jsonify({
#                 "error": "Query cannot be empty"
#             }), 400
            
#         # Limit query length more strictly
#         if len(query_text) > 500:
#             return jsonify({
#                 "error": "Query too long (max 500 characters)"
#             }), 400
        
#         # Generate a unique ID for this query
#         conversation_id = str(uuid4())
        
#         # Use empty context - no conversation history
#         context = []
        
#         # For stateful behavior, client should include previous messages in request
#         if data.get('previous_messages') and isinstance(data.get('previous_messages'), list):
#             # Limit to max 3 messages from client to prevent memory issues
#             context = data['previous_messages'][:3]
        
#         # Add timeout check
#         if time.time() - start_time > 25:
#             return jsonify({
#                 "query": query_text,
#                 "response": "Request processing took too long. Please try again with a shorter query.",
#                 "conversation_id": conversation_id
#             })
        
#         # Get response with course context and source filter if provided
#         response = rag_engine.answer_query(
#             query_text,
#             course=course,
#             context=context,
#             source_filter=source_filter
#         )
        
#         # Force garbage collection to free memory
#         gc.collect()
        
#         # Include course and source in response if provided
#         result = {
#             "query": query_text,
#             "response": response,
#             "conversation_id": conversation_id
#         }
        
#         if course:
#             result["course"] = course
            
#         if source_filter:
#             result["source"] = source_filter
        
#         return jsonify(result)
#     except Exception as e:
#         # Log the error but return a user-friendly message
#         print(f"Error processing query: {str(e)}")
#         return jsonify({
#             "query": data.get('query', ''),
#             "response": "I'm sorry, I encountered an error while processing your question. Please try again.",
#             "conversation_id": str(uuid4()),
#             "error": "Internal server error"
#         }), 500

@query_bp.route('/query', methods=['POST'])

def query():
    start_time = time.time()
    try:
        get_component = current_app.config['GET_COMPONENT']
        rag_engine = get_component("rag_engine")

        data = request.json
        if not data or 'query' not in data:
            return jsonify({"error": "Missing 'query' parameter"}), 400

        query_text = data['query'].strip()
        if not query_text:
            return jsonify({"error": "Query cannot be empty"}), 400
        if len(query_text) > 500:
            return jsonify({"error": "Query too long (max 500 characters)"}), 400

        # Detect special keywords for quiz/test
        lower_q = query_text.lower()
        is_quiz_request = any(word in lower_q for word in ['test', 'quiz', 'questions', 'mcq', 'exam'])

        course = data.get('course')
        source_filter = data.get('source')
        context = data.get('previous_messages', [])[:3] if isinstance(data.get('previous_messages'), list) else []

        conversation_id = str(uuid4())

        # If user is submitting MCQ answers for evaluation
        if data.get('mcq_answers'):
            mcq_answers = data['mcq_answers']
            evaluation = rag_engine.evaluate_mcq_answers(mcq_answers)
            return jsonify({
                "query": query_text,
                "evaluation": evaluation,
                "conversation_id": conversation_id
            })

        # If this is a quiz/test request, generate MCQs instead of normal answer
        if is_quiz_request:
            mcqs = rag_engine.generate_mcqs(query_text, course=course, context=context)
            return jsonify({
                "query": query_text,
                "mcqs": mcqs,
                "conversation_id": conversation_id,
                "is_quiz": True
            })

        # Otherwise normal query path (with Redis cache)

        # Detect video queries
        is_video_query = any(word in lower_q for word in ["video", "youtube", "watch", "tutorial", "lecture", "recording"])
        if is_video_query and not source_filter:
            source_filter = "youtube"

        # Redis caching
        cache_key = _make_cache_key(query_text, context)
        cached_response = redis_client.get(cache_key)
        if cached_response:
            result = json.loads(cached_response)
            result['cached'] = True
            return jsonify(result)

        # Timeout check
        if time.time() - start_time > 25:
            return jsonify({
                "query": query_text,
                "response": "Request processing took too long. Please try again with a shorter query.",
                "conversation_id": conversation_id
            })

        response_text = rag_engine.answer_query(query_text, course=course, context=context, source_filter=source_filter)
        gc.collect()

        result = {
            "query": query_text,
            "response": response_text,
            "conversation_id": conversation_id,
        }
        if course:
            result["course"] = course
        if source_filter:
            result["source"] = source_filter

        redis_client.setex(cache_key, 600, json.dumps(result))
        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Error processing query: {str(e)}")
        return jsonify({
            "query": data.get('query', '') if data else '',
            "response": "I'm sorry, I encountered an error while processing your question. Please try again.",
            "conversation_id": str(uuid4()),
            "error": "Internal server error"
        }), 500
    


# Special endpoint for video-specific queries
@query_bp.route('/query/video', methods=['POST'])
def video_query():
    """Special endpoint for video-specific queries"""
    start_time = time.time()
    
    try:
        # Lazy load RAG engine only when needed
        get_component = current_app.config['GET_COMPONENT']
        rag_engine = get_component("rag_engine")
        
        data = request.json
        
        if not data or 'query' not in data:
            return jsonify({
                "error": "Missing 'query' parameter"
            }), 400
        
        query_text = data['query']
        course = data.get('course')
        
        # Generate a unique ID for this query
        conversation_id = str(uuid4())
        
        # Use empty context - no conversation history
        context = []
        
        # For stateful behavior, client should include previous messages in request
        if data.get('previous_messages') and isinstance(data.get('previous_messages'), list):
            context = data['previous_messages'][:3]
        
        # Get response, forcing source filter to youtube
        response = rag_engine.answer_query(
            query_text,
            course=course,
            context=context,
            source_filter="youtube"
        )
        
        # Force garbage collection to free memory
        gc.collect()
        
        result = {
            "query": query_text,
            "response": response,
            "conversation_id": conversation_id,
            "source": "youtube"
        }
        
        if course:
            result["course"] = course
        
        return jsonify(result)
    except Exception as e:
        print(f"Error processing video query: {str(e)}")
        return jsonify({
            "query": data.get('query', ''),
            "response": "I'm sorry, I encountered an error while processing your video question. Please try again.",
            "conversation_id": str(uuid4()),
            "error": "Internal server error"
        }), 500

@query_bp.route('/clear-cache', methods=['POST'])
def clear_cache():
    """Clear all caches (embedding cache in RAG engine)"""
    try:
        # Clear embedding cache in RAG engine if it exists
        components = current_app.config['COMPONENTS']
        if "rag_engine" in components:
            rag_engine = components["rag_engine"]
            if hasattr(rag_engine, '_embedding_cache'):
                rag_engine._embedding_cache.clear()
        
        # Force garbage collection
        gc.collect()
        
        return jsonify({
            "status": "success",
            "message": "Cache cleared successfully"
        })
    except Exception as e:
        print(f"Error clearing cache: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error clearing cache: {str(e)}"
        }), 500
        

