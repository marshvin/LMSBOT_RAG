import os
from typing import Dict, Any, Optional
from pypdf import PdfReader

class PDFLoader:
    def __init__(self):
        self.supported_types = ['.pdf']

    def load_document(self, file_path: str, course: Optional[str] = None) -> Dict[str, Any]:
        """
        Load and process a PDF document
        
        Args:
            file_path: Path to the PDF file
            course: Course identifier this document belongs to
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.lower().endswith('.pdf'):
            raise ValueError("File must be a PDF")
            
        # Validate course information
        if not course:
            raise ValueError("Course information is required for document processing")

        # Read PDF
        reader = PdfReader(file_path)
        text = ""
        
        # Extract text from all pages
        for page in reader.pages:
            text += page.extract_text() + "\n"

        # Create metadata
        filename = os.path.basename(file_path)
        metadata = {
            "source": "pdf",
            "filename": filename,
            "doc_name": filename,
            "path": file_path,
            "pages": len(reader.pages),
            "course": course
        }

        return {
            "text": text,
            "metadata": metadata
        }