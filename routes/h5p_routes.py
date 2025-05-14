# routes/h5p_routes.py
from flask import Blueprint, request, jsonify, current_app
import time
import gc

h5p_bp = Blueprint('h5p', __name__, url_prefix='/api/h5p')

@h5p_bp.route('/generate', methods=['POST'])
def generate_h5p():
    """Endpoint for generating H5P content"""
    try:
        # Lazy load RAG engine
        get_component = current_app.config['GET_COMPONENT']
        rag_engine = get_component("rag_engine")
        
        data = request.json
        
        if not data or 'query' not in data:
            return jsonify({
                "error": "Missing 'query' parameter"
            }), 400
        
        query_text = data['query']
        course = data.get('course')
        content_type = data.get('content_type', 'quiz')  # Default to quiz if not specified
        
        # Input validation
        if not query_text or len(query_text.strip()) == 0:
            return jsonify({
                "error": "Query cannot be empty"
            }), 400
            
        # Limit query length
        if len(query_text) > 500:
            return jsonify({
                "error": "Query too long (max 500 characters)"
            }), 400
        
        # Add content type to query if not present
        if content_type not in query_text.lower():
            query_text = f"generate {content_type} about {query_text}"
        
        # Generate H5P content
        h5p_content = rag_engine.generate_h5p_content(query_text, course)
        
        # Force garbage collection
        gc.collect()
        
        result = {
            "query": query_text,
            "h5p_content": h5p_content,
            "content_type": content_type
        }
        
        if course:
            result["course"] = course
        
        return jsonify(result)
    except Exception as e:
        print(f"Error generating H5P content: {str(e)}")
        return jsonify({
            "query": data.get('query', ''),
            "response": "I'm sorry, I encountered an error while generating H5P content. Please try again.",
            "error": "Internal server error"
        }), 500

@h5p_bp.route('/types', methods=['GET'])
def get_h5p_types():
    """Return available H5P content types"""
    return jsonify({
        "types": [
            {
                "id": "quiz",
                "name": "Quiz",
                "description": "Multiple choice questions with feedback"
            },
            {
                "id": "interactive_video",
                "name": "Interactive Video",
                "description": "Add interactivity to videos with questions and annotations"
            },
            {
                "id": "course_presentation",
                "name": "Course Presentation",
                "description": "Create a slideshow with interactive elements"
            }
        ]
    }) 