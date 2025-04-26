# routes/query_routes.py
from flask import Blueprint, request, jsonify, current_app
from uuid import uuid4
import time

query_bp = Blueprint('query', __name__, url_prefix='/api')

# In-memory storage for conversations (in production, use a proper database)
conversations = {}

@query_bp.route('/query', methods=['POST'])
def query():
    """Query endpoint for RAG responses with conversation memory"""
    start_time = time.time()
    
    try:
        components = current_app.config['COMPONENTS']
        rag_engine = components['rag_engine']
        
        data = request.json
        
        if not data or 'query' not in data:
            return jsonify({
                "error": "Missing 'query' parameter"
            }), 400
        
        query_text = data['query']
        
        # Input validation
        if not query_text or len(query_text.strip()) == 0:
            return jsonify({
                "error": "Query cannot be empty"
            }), 400
            
        if len(query_text) > 1000:
            return jsonify({
                "error": "Query too long (max 1000 characters)"
            }), 400
        
        conversation_id = data.get('conversation_id')
        
        # Create new conversation if no ID provided
        if not conversation_id:
            conversation_id = str(uuid4())
            conversations[conversation_id] = []
        
        # Get conversation history
        conversation_history = conversations.get(conversation_id, [])
        
        # Add timeout check
        if time.time() - start_time > 25:
            return jsonify({
                "query": query_text,
                "response": "Request processing took too long. Please try again with a shorter query.",
                "conversation_id": conversation_id
            })
        
        # Get response using conversation history
        response = rag_engine.answer_query(
            query_text,
            context=conversation_history
        )
        
        # Add timeout check before updating history
        if time.time() - start_time > 28:
            return jsonify({
                "query": query_text,
                "response": "Request processing took too long. Please try again with a shorter query.",
                "conversation_id": conversation_id
            })
        
        # Update conversation history
        conversation_history.extend([
            {"role": "user", "content": query_text},
            {"role": "assistant", "content": response}
        ])
        
        # Limit conversation history to last 10 messages
        conversations[conversation_id] = conversation_history[-10:]
        
        return jsonify({
            "query": query_text,
            "response": response,
            "conversation_id": conversation_id
        })
    except Exception as e:
        # Log the error but return a user-friendly message
        print(f"Error processing query: {str(e)}")
        return jsonify({
            "query": data.get('query', ''),
            "response": "I'm sorry, I encountered an error while processing your question. Please try again.",
            "conversation_id": data.get('conversation_id', str(uuid4())),
            "error": "Internal server error"
        }), 500