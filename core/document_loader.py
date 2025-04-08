from llama_index.core import SimpleDirectoryReader
from typing import List
from llama_index.core import Document

class DocumentLoader:
    @staticmethod
    def load_documents(directory_path: str) -> List[Document]:
        """Load documents from a directory."""
        try:
            documents = SimpleDirectoryReader(directory_path).load_data()
            return documents
        except Exception as e:
            raise Exception(f"Error loading documents: {str(e)}") 