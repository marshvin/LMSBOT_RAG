import logging
from services.document_service import DocumentService, ContentSource
from llama_index.core import Document
from typing import List
from services.youtube_service import YouTubeService

class YouTubeLoader:
    def __init__(self, youtube_service: YouTubeService, vector_service, config):
        self.youtube_service = youtube_service
        self.vector_service = vector_service
        self.config = config

    def load_and_index(self) -> List[Document]:
        documents = []

        try:
            videos = self.youtube_service.get_channel_videos(
                channel_id=self.config.YOUTUBE_CHANNEL_ID,
                max_results=self.config.YOUTUBE_MAX_VIDEOS or 10
            )

            for video in videos:
                source = ContentSource(
                    id=video["id"],
                    type="youtube",
                    title=video["title"],
                    url=video["url"],
                    metadata=video["metadata"]
                )
                video_docs = DocumentService.create_from_video(source, video["transcript"])
                documents.extend(video_docs)

            if documents:
                self.vector_service.create_index(documents)
                logging.info(f"Indexed {len(documents)} YouTube transcript documents.")
            else:
                logging.info("No YouTube transcripts found to index.")
        
        except Exception as e:
            logging.warning(f"YouTube transcript indexing failed: {e}")
        
        return documents
