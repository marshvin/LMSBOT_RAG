# rag_components/youtube_loader.py
import os
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from typing import List, Dict, Any, Optional

class YouTubeLoader:
    def __init__(self, api_key: str, channel_id: str = None, max_videos: int = 20):
        self.api_key = api_key
        self.channel_id = channel_id
        self.max_videos = max_videos
    
    def fetch_channel_videos(self) -> List[Dict[str, Any]]:
        """Fetch videos from a YouTube channel"""
        if not self.channel_id:
            return []
            
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
    
    def get_video_details(self, video_id: str) -> Dict[str, Any]:
        """Get details for a specific video"""
        url = f"https://www.googleapis.com/youtube/v3/videos"
        params = {
            "key": self.api_key,
            "id": video_id,
            "part": "snippet"
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if "items" in data and len(data["items"]) > 0:
            item = data["items"][0]
            return {
                "video_id": video_id,
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"]
            }
        else:
            raise ValueError(f"Could not find video with ID: {video_id}")
    
    def get_video_transcript(self, video_id: str) -> str:
        """Get transcript for a specific video"""
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = " ".join([item['text'] for item in transcript_list])
            return transcript_text
        except Exception as e:
            print(f"Error fetching transcript for video {video_id}: {str(e)}")
            return ""
    
    def process_single_video(self, video_id: str, document_processor, course: str) -> str:
        """
        Process a single YouTube video by its ID
        
        Args:
            video_id: YouTube video ID
            document_processor: The document processor component
            course: Course identifier to associate with the video
        
        Returns:
            The document ID of the processed video
        """
        if not course:
            raise ValueError("Course information is required for processing YouTube videos")
            
        # Get video details
        video_details = self.get_video_details(video_id)
        
        # Get transcript
        transcript = self.get_video_transcript(video_id)
        if not transcript:
            raise ValueError(f"Could not fetch transcript for video ID: {video_id}")
        
        # Process the transcript
        metadata = {
            "source": "youtube",
            "video_id": video_id,
            "title": video_details["title"],
            "description": video_details["description"],
            "doc_name": video_details["title"],
            "course": course
        }
        
        doc_id = document_processor.process_document(transcript, metadata)
        print(f"Processed video: {video_details['title']} for course: {course}")
        
        return doc_id
    
    def load_and_process(self, document_processor, course: str) -> List[str]:
        """
        Load videos from channel and process them into the RAG system
        
        Args:
            document_processor: The document processor component
            course: Course identifier to associate with these videos
        """
        if not course:
            raise ValueError("Course information is required for processing YouTube videos")
            
        videos = self.fetch_channel_videos()
        processed_ids = []
        
        for video in videos:
            transcript = self.get_video_transcript(video['video_id'])
            if transcript:
                metadata = {
                    "source": "youtube",
                    "video_id": video['video_id'],
                    "title": video['title'],
                    "description": video['description'],
                    "doc_name": video['title'],
                    "course": course
                }
                
                doc_id = document_processor.process_document(transcript, metadata)
                processed_ids.append(doc_id)
                print(f"Processed video: {video['title']} for course: {course}")
        
        return processed_ids