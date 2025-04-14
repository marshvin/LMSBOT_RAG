import os
from typing import Dict, Any
from pypdf import PdfReader

class PDFLoader:
    def __init__(self):
        self.supported_types = ['.pdf']

    def load_document(self, file_path: str) -> Dict[str, Any]:
        """Load and process a PDF document"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.lower().endswith('.pdf'):
            raise ValueError("File must be a PDF")

        # Read PDF
        reader = PdfReader(file_path)
        text = ""
        
        # Extract text from all pages
        for page in reader.pages:
            text += page.extract_text() + "\n"

        # Create metadata
        metadata = {
            "source": "pdf",
            "filename": os.path.basename(file_path),
            "path": file_path,
            "pages": len(reader.pages)
        }

        return {
            "text": text,
            "metadata": metadata
        }