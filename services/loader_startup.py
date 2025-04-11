import logging
from services.llm_service import LLMService
from services.sharepoint_loader import SharePointLoader
from services.youtube_loader import YouTubeLoader
from config.config import Config
from services.youtube_service import YouTubeService
from services.sharepoint_service import SharePointVideoService
from services.document_service import DocumentService
from services.vector_store import VectorStoreService
# from llama_index.embeddings.huggingface import HuggingFaceEmbedding
# from llama_index.vector_stores.pinecone import PineconeVectorStore
# from llama_index.core import Document

def initialize_and_index_all_sources():
    try:
        # embed_model = HuggingFaceEmbedding(model_name= Config.EMBED_MODEL_NAME)
        embed_model = None
        vector_service = VectorStoreService(config=Config, embed_model=embed_model)
        vector_service.initialize_store()

        documents = []
        
        #  # --- Load and convert YouTube data ---
        # try:
        #     yt_service = YouTubeService(api_key=Config.YOUTUBE_API_KEY)
        #     yt_loader = YouTubeLoader(channel_id=Config.YOUTUBE_CHANNEL_ID, youtube_service=yt_service)
        #     yt_documents = yt_loader.load_documents()
        #     documents.extend(yt_documents)
        #     logging.info(f"Loaded and created {len(yt_documents)} YouTube documents.")
        # except Exception as yt_err:
        #     logging.warning(f"YouTube loading failed: {yt_err}", exc_info=True)

        # --- Load and convert SharePoint data ---
        # try:
        #     sp_loader = SharePointLoader(
        #         site_url=Config.SHAREPOINT_SITE_URL,
        #         client_id=Config.SHAREPOINT_CLIENT_ID,
        #         client_secret=Config.SHAREPOINT_CLIENT_SECRET,
        #         folder_path=Config.SHAREPOINT_FOLDER_PATH,
        #         llm_service=LLMService()
        #     )
        #     sp_documents = sp_loader.load_documents()
        #     documents.extend(sp_documents)
        #     logging.info(f"Loaded and created {len(sp_documents)} SharePoint documents.")
        # except Exception as sp_err:
        #     logging.warning(f"SharePoint loading failed: {sp_err}", exc_info=True)


        # ##########################################
        # version 2
        # ##########################################
        # --- Load and convert YouTube data ---
        # try:
        #     yt_service = YouTubeService(api_key=Config.YOUTUBE_API_KEY)
        #     yt_videos = yt_service.get_channel_videos(channel_id=Config.YOUTUBE_CHANNEL_ID)
        #     for vid in yt_videos:
        #         documents.extend(DocumentService.create_from_video(
        #             source=vid,  
        #             transcript=vid['transcript']
        #         ))
        #     logging.info(f"Loaded and created {len(yt_videos)} YouTube documents.")
        # except Exception as yt_err:
        #     logging.warning(f"YouTube loading failed: {yt_err}")

        # # # --- Load and convert SharePoint data ---
        # try:
        #     sp_service = SharePointVideoService(
        #         # tenant_id=Config.SHAREPOINT_TENANT_ID,
        #         client_id=Config.SHAREPOINT_CLIENT_ID,
        #         client_secret=Config.SHAREPOINT_CLIENT_SECRET,
        #         site_url=Config.SHAREPOINT_SITE_URL
        #     )
        #     sp_items = sp_service.fetch_documents()
        #     for item in sp_items:
        #         documents.extend(sp_service.convert_to_documents(item))
        #     logging.info(f"Loaded and created {len(sp_items)} SharePoint documents.")
        # except Exception as sp_err:
        #     logging.warning(f"SharePoint loading failed: {sp_err}")

        # --- Index All ---
        if documents:
            vector_service.create_index(documents)
            logging.info("Indexing complete.")
        else:
            logging.warning("No documents to index.")
    except Exception as e:
        logging.error(f"Startup indexing failed: {str(e)}", exc_info=True)
