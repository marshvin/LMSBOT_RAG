from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import List, Dict
import logging
from config.config import Config
import re

class GoogleSlidesService:
    def __init__(self, credentials_file: str = None):
        """
        Initialize Google Slides service
        
        Args:
            credentials_file: Path to service account JSON credentials
        """
        self.credentials_file = credentials_file or Config.GOOGLE_CREDENTIALS_FILE
        self.service = self._authenticate()

    def _authenticate(self):
        """Authenticate using service account credentials"""
        credentials = service_account.Credentials.from_service_account_file(
            self.credentials_file,
            scopes=['https://www.googleapis.com/auth/presentations.readonly']
        )
        return build('slides', 'v1', credentials=credentials)

    def get_presentation_text(self, presentation_id: str) -> Dict:
        """
        Extract all text from a Google Slides presentation
        
        Returns:
            {
                "presentation_id": "abc123",
                "title": "Presentation Title",
                "slides": [
                    {
                        "slide_number": 1,
                        "text": "Slide content...",
                        "notes": "Speaker notes..."
                    },
                    ...
                ]
            }
        """
        try:
            presentation = self.service.presentations().get(
                presentationId=presentation_id
            ).execute()
            
            slides_content = []
            for i, slide in enumerate(presentation.get('slides', [])):
                slide_text = []
                notes_text = []
                
                # Extract slide elements
                for element in slide.get('pageElements', []):
                    if 'shape' in element:
                        for paragraph in element['shape'].get('text', {}).get('textElements', []):
                            if 'textRun' in paragraph:
                                slide_text.append(paragraph['textRun']['content'])
                
                # Extract speaker notes
                notes_id = slide.get('slideProperties', {}).get('notesPage', {}).get('notesId')
                if notes_id:
                    notes_page = self.service.presentations().pages().get(
                        presentationId=presentation_id,
                        pageObjectId=notes_id
                    ).execute()
                    for element in notes_page.get('pageElements', []):
                        if 'shape' in element:
                            for paragraph in element['shape'].get('text', {}).get('textElements', []):
                                if 'textRun' in paragraph:
                                    notes_text.append(paragraph['textRun']['content'])
                
                slides_content.append({
                    "slide_number": i + 1,
                    "text": " ".join(slide_text),
                    "notes": " ".join(notes_text)
                })
            
            return {
                "presentation_id": presentation_id,
                "title": presentation.get('title', 'Untitled'),
                "slides": slides_content
            }
            
        except Exception as e:
            logging.error(f"Google Slides error: {str(e)}")
            raise SlidesServiceError(f"Failed to get presentation: {str(e)}")

    def get_slide_thumbnail_url(self, presentation_id: str, slide_number: int) -> str:
        """Generate thumbnail URL for a specific slide"""
        return (f"https://docs.google.com/presentation/d/{presentation_id}"
                f"/pub?slide=id.p.{slide_number - 1}")

class SlidesServiceError(Exception):
    """Custom Google Slides service exceptions"""
    pass