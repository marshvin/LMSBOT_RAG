# routes/document_routes.py
from flask import Blueprint, request, jsonify, current_app
import os
import gc
from rag_components.pdf_loader import PDFLoader  # Add this import

document_bp = Blueprint('document', __name__, url_prefix='/api')

@document_bp.route('/documents', methods=['POST'])
def add_document():
    """Add a document to the RAG system"""
    # Lazy load document processor
    get_component = current_app.config['GET_COMPONENT']
    document_processor = get_component("document_processor")
    
    data = request.json
    
    if not data or 'text' not in data:
        return jsonify({
            "error": "Missing 'text' parameter"
        }), 400
    
    # Require course information
    if 'course' not in data:
        return jsonify({
            "error": "Course information is required"
        }), 400
    
    document_text = data['text']
    metadata = data.get('metadata', {})
    
    # Add course information to metadata
    metadata['course'] = data['course']
    
    # Add doc_name if provided separately or use a default
    if 'doc_name' in data:
        metadata['doc_name'] = data['doc_name']
    
    try:
        doc_id = document_processor.process_document(document_text, metadata)
        
        # Run garbage collection
        gc.collect()
        
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
    # Lazy load pinecone client
    get_component = current_app.config['GET_COMPONENT']
    pinecone_client = get_component("pinecone_client")
    
    try:
        # Delete the document by ID
        pinecone_client.delete(ids=[f"{doc_id}_*"])
        
        # Run garbage collection
        gc.collect()
        
        return jsonify({
            "message": f"Document {doc_id} deleted successfully"
        })
    except Exception as e:
        return jsonify({
            "error": f"Error deleting document: {str(e)}"
        }), 500

@document_bp.route('/documents/pdf', methods=['POST'])
def upload_pdf():
    """Upload and process a PDF document"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
        
    if not file.filename.endswith('.pdf'):
        return jsonify({"error": "File must be a PDF"}), 400
    
    # Require course information
    course = request.form.get('course')
    if not course:
        return jsonify({"error": "Course information is required"}), 400
    
    # Limit PDF size
    MAX_PDF_SIZE = 5 * 1024 * 1024  # 5MB
    if file.content_length and file.content_length > MAX_PDF_SIZE:
        return jsonify({"error": "PDF file too large (max 5MB)"}), 400
    
    # Save the file temporarily
    temp_path = f"temp_{file.filename}"
    try:
        file.save(temp_path)
        
        # Process the PDF with course information
        pdf_loader = PDFLoader()
        document = pdf_loader.load_document(temp_path, course=course)
        
        # Add any additional metadata from form
        additional_metadata = {}
        if request.form.get('doc_name'):
            additional_metadata['doc_name'] = request.form.get('doc_name')
        
        # Merge with document metadata
        document["metadata"].update(additional_metadata)
        
        # Process through RAG system
        get_component = current_app.config['GET_COMPONENT']
        document_processor = get_component("document_processor")
        
        doc_id = document_processor.process_document(
            text=document["text"],
            metadata=document["metadata"]
        )
        
        # Run garbage collection
        gc.collect()
        
        return jsonify({
            "message": "PDF processed successfully",
            "document_id": doc_id
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)