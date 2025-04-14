# rag_components/youtube_loader.py
import os
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from typing import List, Dict, Any

class YouTubeLoader:
    def __init__(self, api_key: str, channel_id: str, max_videos: int = 20):
        self.api_key = api_key
        self.channel_id = channel_id
        self.max_videos = max_videos
    
    def fetch_channel_videos(self) -> List[Dict[str, Any]]:
        """Fetch videos from a YouTube channel"""
        url = f"https://www.googleapis.com/youtube/v3/search"
        params = {
            "key": self.api_key,
            "channelId": self.channel_id,
            "part": "snippet",
            "order": "date",
            "maxResults": self.max_videos,
            "type": "video"
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        videos = []
        if "items" in data:
            for item in data["items"]:
                video_id = item["id"]["videoId"]
                title = item["snippet"]["title"]
                description = item["snippet"]["description"]
                
                videos.append({
                    "video_id": video_id,
                    "title": title,
                    "description": description
                })
        
        return videos
    
    def get_video_transcript(self, video_id: str) -> str:
        """Get transcript for a specific video"""
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = " ".join([item['text'] for item in transcript_list])
            return transcript_text
        except Exception as e:
            print(f"Error fetching transcript for video {video_id}: {str(e)}")
            return ""
    
    def load_and_process(self, document_processor) -> List[str]:
        """Load videos from channel and process them into the RAG system"""
        videos = self.fetch_channel_videos()
        processed_ids = []
        
        for video in videos:
            transcript = self.get_video_transcript(video['video_id'])
            if transcript:
                metadata = {
                    "source": "youtube",
                    "video_id": video['video_id'],
                    "title": video['title'],
                    "description": video['description']
                }
                
                doc_id = document_processor.process_document(transcript, metadata)
                processed_ids.append(doc_id)
                print(f"Processed video: {video['title']}")
        
        return processed_ids