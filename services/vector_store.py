from pinecone import Pinecone
from llama_index.vector_stores.pinecone.base import PineconeVectorStore
from llama_index.core import VectorStoreIndex, StorageContext

class VectorStoreService:
    def __init__(self, config, embed_model=None):
        self.config = config
        self.pc = Pinecone(api_key=self.config.PINECONE_API_KEY)
        self.index_name = self.config.PINECONE_INDEX_NAME
        self.embed_model = embed_model
        self.vector_store = None
        self.index = None

    def initialize_store(self):
        """Initialize Pinecone vector store."""
        pinecone_index = self.pc.Index(self.index_name)
        self.vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
        return self.vector_store

    def create_index(self, documents):
        """Create index from documents."""
        storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        self.index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            embed_model=self.embed_model
        )
        return self.index

    def query_index(self, query_text: str, top_k: int = 5, filters: dict = None) -> list:
        """Query the index with optional filters and top_k results."""
        if not self.index:
            raise Exception("Index not initialized")

        query_engine = self.index.as_query_engine(similarity_top_k=top_k, filters=filters)
        response = query_engine.query(query_text)
        return response.source_nodes 









# ####################################################################
# ORIGINAL CODE
# ####################################################################
# 
# 
# from pinecone import Pinecone
# from llama_index.vector_stores.pinecone.base import PineconeVectorStore
# from llama_index.core import VectorStoreIndex, StorageContext
# from config.config import Config

# class VectorStoreService:
#     def __init__(self):
#         self.pc = Pinecone(api_key=Config.PINECONE_API_KEY)  
#         self.index_name = Config.PINECONE_INDEX_NAME
#         self.vector_store = None
#         self.index = None

#     def initialize_store(self, embed_model):
#         """Initialize Pinecone vector store."""
#         pinecone_index = self.pc.Index(self.index_name)
#         self.vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
#         self.embed_model = embed_model
        
#         return self.vector_store

#     def create_index(self, documents):
#         """Create index from documents."""
#         storage_context = StorageContext.from_defaults(
#             vector_store=self.vector_store
#         )
#         self.index = VectorStoreIndex.from_documents(
#             documents,
#             storage_context=storage_context
#         )
#         return self.index

#     def query_index(self, query_text: str) -> str:
#         """Query the index."""
#         if not self.index:
#             raise Exception("Index not initialized")
        
#         query_engine = self.index.as_query_engine()
#         response = query_engine.query(query_text)
#         return str(response) 