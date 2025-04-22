# routes/query_routes.py
from flask import Blueprint, request, jsonify, current_app
from uuid import uuid4

query_bp = Blueprint('query', __name__, url_prefix='/api')

# In-memory storage for conversations (in production, use a proper database)
conversations = {}

@query_bp.route('/query', methods=['POST'])
def query():
    """Query endpoint for RAG responses with conversation memory"""
    components = current_app.config['COMPONENTS']
    rag_engine = components['rag_engine']
    
    data = request.json
    
    if not data or 'query' not in data:
        return jsonify({
            "error": "Missing 'query' parameter"
        }), 400
    
    query_text = data['query']
    conversation_id = data.get('conversation_id')
    
    # Create new conversation if no ID provided
    if not conversation_id:
        conversation_id = str(uuid4())
        conversations[conversation_id] = []
    
    # Get conversation history
    conversation_history = conversations.get(conversation_id, [])
    
    try:
        # Get response using conversation history
        response = rag_engine.answer_query(
            query_text,
            context=conversation_history
        )
        
        # Update conversation history
        conversation_history.extend([
            {"role": "user", "content": query_text},
            {"role": "assistant", "content": response}
        ])
        conversations[conversation_id] = conversation_history[-10:]  # Keep last 10 messages
        
        return jsonify({
            "query": query_text,
            "response": response,
            "conversation_id": conversation_id
        })
    except Exception as e:
        return jsonify({
            "error": f"Error processing query: {str(e)}"
        }), 500