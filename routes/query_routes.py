# routes/query_routes.py
from flask import Blueprint, request, jsonify, current_app
from uuid import uuid4
import time
import gc

query_bp = Blueprint('query', __name__, url_prefix='/api')

# Stateless implementation - no in-memory cache

@query_bp.route('/query', methods=['POST'])
def query():
    """Query endpoint for RAG responses without conversation memory"""
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
        
        # Get course information if provided
        course = data.get('course')
        
        # Input validation
        if not query_text or len(query_text.strip()) == 0:
            return jsonify({
                "error": "Query cannot be empty"
            }), 400
            
        # Limit query length more strictly
        if len(query_text) > 500:  # Reduced from 1000
            return jsonify({
                "error": "Query too long (max 500 characters)"
            }), 400
        
        # Generate a unique ID for this query
        conversation_id = str(uuid4())
        
        # Use empty context - no conversation history
        context = []
        
        # For stateful behavior, client should include previous messages in request
        if data.get('previous_messages') and isinstance(data.get('previous_messages'), list):
            # Limit to max 3 messages from client to prevent memory issues
            context = data['previous_messages'][:3]
        
        # Add timeout check
        if time.time() - start_time > 25:
            return jsonify({
                "query": query_text,
                "response": "Request processing took too long. Please try again with a shorter query.",
                "conversation_id": conversation_id
            })
        
        # Get response with course context if provided
        response = rag_engine.answer_query(
            query_text,
            course=course,
            context=context
        )
        
        # Force garbage collection to free memory
        gc.collect()
        
        # Include course in response if provided
        result = {
            "query": query_text,
            "response": response,
            "conversation_id": conversation_id
        }
        
        if course:
            result["course"] = course
        
        return jsonify(result)
    except Exception as e:
        # Log the error but return a user-friendly message
        print(f"Error processing query: {str(e)}")
        return jsonify({
            "query": data.get('query', ''),
            "response": "I'm sorry, I encountered an error while processing your question. Please try again.",
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