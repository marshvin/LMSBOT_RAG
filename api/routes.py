from flask import Blueprint, request, jsonify
from core.document_loader import DocumentLoader
from core.vector_store import VectorStoreService
from core.llm_service import LLMService

api = Blueprint('api', __name__)
vector_service = VectorStoreService()
llm_service = LLMService()

@api.route('/load-documents', methods=['POST'])
def load_documents():
    try:
        data = request.get_json()
        directory_path = data.get('directory_path')
        
        # Load documents
        documents = DocumentLoader.load_documents(directory_path)
        
        # Initialize vector store and create index
        vector_store = vector_service.initialize_store()
        vector_service.create_index(documents)
        
        return jsonify({"message": "Documents loaded successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/query', methods=['POST'])
def query():
    try:
        data = request.get_json()
        query_text = data.get('query')
        
        # Query the index
        response = vector_service.query_index(query_text)
        
        return jsonify({"response": response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500 