# from flask import Blueprint, request, jsonify
# from core.document_loader import DocumentLoader
# from core.vector_store import VectorStoreService
# from core.llm_service import LLMService

# api = Blueprint('api', __name__)
# vector_service = VectorStoreService()
# llm_service = LLMService()

# @api.route('/load-documents', methods=['POST'])
# def load_documents():
#     try:
#         data = request.get_json()
#         directory_path = data.get('directory_path')
        
#         # Load documents
#         documents = DocumentLoader.load_documents(directory_path)
        
#         # Initialize vector store and create index
#         vector_store = vector_service.initialize_store(
#             embed_model=llm_service.get_embedding_model()
#         )
#         vector_service.create_index(documents)
        
#         return jsonify({"message": "Documents loaded successfully"}), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @api.route('/query', methods=['POST'])
# def query():
#     try:
#         data = request.get_json()
#         query_text = data.get('query')
        
#         # 1. Retrieve relevant context
#         search_results = vector_service.query_index(query_text, top_k=3)
        
#         # 2. Generate LLM response with context
#         context = "\n\n".join([doc.text for doc in search_results])
#         response = llm_service.generate_content(
#             f"Context:\n{context}\n\nQuestion: {query_text}"
#         )
        
#         # 3. Format response with sources
#         return jsonify({
#             "answer": response.text,
#             "sources": [doc.metadata for doc in search_results]
#         }), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
    
# from flask import Blueprint, request, jsonify
# from office365.sharepoint.client_context import ClientContext
# from office365.runtime.auth.client_credential import ClientCredential
# from core.document_loader import SharePointLoader
# from LMSBOT_RAG.services.vector_store import VectorStoreService
# from LMSBOT_RAG.services.llm_service import LLMService
# from config.config import Config
# import tempfile

# api = Blueprint('api', __name__)
# vector_service = VectorStoreService()
# llm_service = LLMService()

# # # SharePoint Client Setup
# # def get_sharepoint_client():
# #     credentials = ClientCredential(
# #         Config.SHAREPOINT_CLIENT_ID,
# #         Config.SHAREPOINT_CLIENT_SECRET
# #     )
# #     return ClientContext(Config.SHAREPOINT_SITE_URL).with_credentials(credentials)

# # @api.route('/load-sharepoint', methods=['POST'])
# # def load_sharepoint_documents():
# #     try:
# #         client = get_sharepoint_client()
# #         data = request.get_json()
# #         folder_path = data.get('folder_path', "/Shared Documents/Training Materials")
        
# #         # Load documents from SharePoint
# #         loader = SharePointLoader(
# #             client=client,
# #             llm_service=llm_service,
# #             temp_dir=tempfile.mkdtemp()
# #         )
        
# #         # Process different file types
# #         documents = loader.load_folder(folder_path)
        
# #         # Create/update vector index
# #         vector_service.create_index(documents)
        
# #         return jsonify({
# #             "message": f"Processed {len(documents)} items from SharePoint",
# #             "details": loader.get_processing_stats()
# #         }), 200
        
# #     except Exception as e:
# #         return jsonify({"error": str(e)}), 500

# @api.route('/query', methods=['POST'])
# def query():
#     try:
#         data = request.get_json()
#         query_text = data.get('query')
        
#         # 1. Retrieve relevant context from vector store
#         search_results = vector_service.query_index(query_text, top_k=3)
        
#         # 2. Generate enhanced response with multimedia references
#         context = format_multimedia_context(search_results)
#         response = llm_service.generate_content(
#             f"Use these training materials to answer: {context}\n\nQuestion: {query_text}"
#         )
        
#         # 3. Format response with timecodes/slide numbers
#         return jsonify({
#             "answer": enhance_with_references(response.text, search_results), # type: ignore
#             "sources": format_sources(search_results)
#         }), 200
        
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# def format_multimedia_context(results):
#     context = []
#     for doc in results:
#         if doc.metadata['type'] == 'video':
#             context.append(f"Video Transcript Excerpt ({doc.metadata['timecodes']}): {doc.text}")
#         elif doc.metadata['type'] == 'slide':
#             context.append(f"Slide {doc.metadata['slide_number']}: {doc.text}")
#     return "\n\n".join(context)

# def format_sources(results):
#     return [{
#         'title': doc.metadata['title'],
#         'type': doc.metadata['type'],
#         'url': doc.metadata['sharepoint_url'],
#         'timestamp': doc.metadata.get('timecodes'),
#         'slide': doc.metadata.get('slide_number')
#     } for doc in results]

from flask import Blueprint, request, jsonify
from services.llm_service import GeminiLLMService
from services.document_service import DocumentService
from services.vector_store import VectorStoreService
from config.config import Config
import logging

api = Blueprint('rag_api', __name__)
llm_service = GeminiLLMService()
vector_service = VectorStoreService(
    api_key=Config.PINECONE_API_KEY,
    index_name=Config.PINECONE_INDEX_NAME,
    embed_model=llm_service.get_embedding_model()
)

@api.route('/query', methods=['POST'])
def handle_query():
    try:
        # Validate input
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Missing 'query' in request body"}), 400
        
        query_text = data['query'].strip()
        if not query_text:
            return jsonify({"error": "Query cannot be empty"}), 400
        
        # Retrieve context
        search_results = vector_service.query_index(
            query_text=query_text,
            top_k=Config.RAG_TOP_K,
            filters=data.get('filters')  
        )
        
        # Format context with metadata
        context_parts = []
        for i, doc in enumerate(search_results, 1):
            context_parts.append(
                f"SOURCE {i} ({doc.metadata['source_type'].upper()}):\n"
                f"Content: {doc.text}\n"
                f"Reference: {_format_source_link(doc.metadata)}"
            )
        formatted_context = "\n\n".join(context_parts)
        
        # Generate response
        response = llm_service.generate(
            prompt=query_text,
            context=f"Use these sources to answer. If unsure, say so.\n\n{formatted_context}"
        )
        
        # Format response
        return jsonify({
            "answer": response,
            "sources": [_format_source(doc) for doc in search_results],
            "query_id": _generate_query_id()  # For tracking
        }), 200
        
    except Exception as e:
        logging.error(f"Query failed: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Failed to process query",
            "details": str(e)
        }), 500

def _format_source_link(metadata: dict) -> str:
    """Generate clickable links based on source type"""
    if metadata['source_type'] == "youtube":
        return f"{metadata['url']}?t={int(metadata.get('start_time', 0))}"
    elif metadata['source_type'] == "slides":
        return f"{metadata['url']}#slide=id.p{metadata.get('slide_number', 1) - 1}"
    return metadata['url']

def _format_source(doc) -> dict:
    """Standardize source output format"""
    return {
        "content": doc.text[:500] + "..." if len(doc.text) > 500 else doc.text,
        "type": doc.metadata['source_type'],
        "title": doc.metadata.get('title', 'Untitled'),
        "url": _format_source_link(doc.metadata),
        "timestamp": doc.metadata.get('start_time'),
        "confidence": doc.score,
        "metadata": {k:v for k,v in doc.metadata.items() 
                    if k not in ['text', 'url']}  # Exclude redundant fields
    }

def _generate_query_id() -> str:
    """Generate unique ID for query tracking"""
    import uuid
    return str(uuid.uuid4())