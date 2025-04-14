# routes/document_routes.py
from flask import Blueprint, request, jsonify, current_app

document_bp = Blueprint('document', __name__, url_prefix='/api')

@document_bp.route('/documents', methods=['POST'])
def add_document():
    """Add a document to the RAG system"""
    components = current_app.config['COMPONENTS']
    document_processor = components['document_processor']
    
    data = request.json
    
    if not data or 'text' not in data:
        return jsonify({
            "error": "Missing 'text' parameter"
        }), 400
    
    document_text = data['text']
    metadata = data.get('metadata', {})
    
    try:
        doc_id = document_processor.process_document(document_text, metadata)
        
        return jsonify({
            "message": "Document added successfully",
            "document_id": doc_id
        })
    except Exception as e:
        return jsonify({
            "error": f"Error adding document: {str(e)}"
        }), 500

@document_bp.route('/documents/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """Delete a document from the RAG system"""
    components = current_app.config['COMPONENTS']
    pinecone_client = components['pinecone_client']
    
    try:
        # Delete the document by ID
        pinecone_client.delete(ids=[f"{doc_id}_*"])
        
        return jsonify({
            "message": f"Document {doc_id} deleted successfully"
        })
    except Exception as e:
        return jsonify({
            "error": f"Error deleting document: {str(e)}"
        }), 500