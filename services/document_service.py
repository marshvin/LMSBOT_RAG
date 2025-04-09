from typing import List, Dict, Union
from LMSBOT_RAG.services.google_slide import GoogleSlidesService
from llama_index import Document
from pydantic import BaseModel

class ContentSource(BaseModel):
    id: str
    type: str  # "youtube", "sharepoint", or "slides"
    title: str
    url: str
    metadata: Dict

class DocumentService:
    @staticmethod
    def create_from_video(source: ContentSource, transcript: List[Dict]) -> List[Document]:
        """Create documents from video transcripts"""
        documents = []
        chunk_size = 60  # Group into 1-minute segments
        
        for i in range(0, len(transcript), chunk_size):
            chunk = transcript[i:i+chunk_size]
            start_time = chunk[0]['start']
            end_time = chunk[-1]['start'] + chunk[-1]['duration']
            
            documents.append(Document(
                text=" ".join([t['text'] for t in chunk]),
                metadata={
                    **source.metadata,
                    'source_type': source.type,
                    'content_id': source.id,
                    'title': source.title,
                    'url': source.url,
                    'start_time': start_time,
                    'end_time': end_time,
                    'chunk_id': f"{source.type}_{source.id}_{int(start_time)}"
                }
            ))
        
        return documents

    @staticmethod
    def create_from_slides(presentation: Dict) -> List[Document]:
        """Create documents from slides content"""
        documents = []
        
        for slide in presentation['slides']:
            # Combine slide text and notes
            full_text = f"Slide {slide['slide_number']}: {slide['text']}"
            if slide['notes']:
                full_text += f"\nNotes: {slide['notes']}"
            
            documents.append(Document(
                text=full_text,
                metadata={
                    'source_type': 'slides',
                    'content_id': presentation['presentation_id'],
                    'title': presentation['title'],
                    'url': f"https://docs.google.com/presentation/d/{presentation['presentation_id']}",
                    'slide_number': slide['slide_number'],
                    'thumbnail_url': GoogleSlidesService().get_slide_thumbnail_url(
                        presentation['presentation_id'],
                        slide['slide_number']
                    )
                }
            ))
        
        return documents    