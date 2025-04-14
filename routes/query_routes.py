# routes/query_routes.py
from flask import Blueprint, request, jsonify, current_app

query_bp = Blueprint('query', __name__, url_prefix='/api')

@query_bp.route('/query', methods=['POST'])
def query():
    """Query endpoint for RAG responses"""
    components = current_app.config['COMPONENTS']
    rag_engine = components['rag_engine']
    
    data = request.json
    
    if not data or 'query' not in data:
        return jsonify({
            "error": "Missing 'query' parameter"
        }), 400
    
    query_text = data['query']
    top_k = data.get('top_k', 5)  # Default to 5 if not provided
    
    try:
        response = rag_engine.answer_query(query_text, top_k=top_k)
        
        return jsonify({
            "query": query_text,
            "response": response
        })
    except Exception as e:
        return jsonify({
            "error": f"Error processing query: {str(e)}"
        }), 500

@query_bp.route('/chat', methods=['POST'])
def chat():
    """Chat endpoint with history tracking"""
    components = current_app.config['COMPONENTS']
    rag_engine = components['rag_engine']
    
    data = request.json
    
    if not data or 'message' not in data:
        return jsonify({
            "error": "Missing 'message' parameter"
        }), 400
    
    message = data['message']
    session_id = data.get('session_id', 'default')
    
    # In a real implementation, you would store chat history in a database or cache
    
    try:
        response = rag_engine.answer_query(message)
        
        return jsonify({
            "message": message,
            "response": response,
            "session_id": session_id
        })
    except Exception as e:
        return jsonify({
            "error": f"Error processing message: {str(e)}"
        }), 500