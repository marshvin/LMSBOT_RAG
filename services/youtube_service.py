from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled
from googleapiclient.discovery import build
from typing import List, Dict, Optional
import logging
from config.config import Config

class YouTubeService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or Config.YOUTUBE_API_KEY
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    def get_channel_videos(self, channel_id: str, max_results: int = 20) -> List[Dict]:
        """Get videos with full transcripts for RAG context"""
        try:
            # Get uploads playlist ID
            channels_response = self.youtube.channels().list(
                id=channel_id,
                part='contentDetails'
            ).execute()
            
            uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Get video list
            videos = []
            next_page_token = None
            
            while len(videos) < max_results:
                request = self.youtube.playlistItems().list(
                    playlistId=uploads_playlist_id,
                    part='snippet',
                    maxResults=min(50, max_results - len(videos)),
                    pageToken=next_page_token
                )
                response = request.execute()
                
                for item in response['items']:
                    video_id = item['snippet']['resourceId']['videoId']
                    try:
                        transcript = self._get_video_transcript(video_id)
                        videos.append({
                            'id': video_id,
                            'title': item['snippet']['title'],
                            'url': f"https://youtu.be/{video_id}",
                            'transcript': transcript,
                            'metadata': self._get_video_metadata(video_id)
                        })
                    except TranscriptsDisabled:
                        logging.warning(f"No transcript available for video {video_id}")
                        continue
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
            
            return videos[:max_results]
            
        except Exception as e:
            logging.error(f"YouTube API Error: {str(e)}")
            raise

    def _get_video_transcript(self, video_id: str) -> List[Dict]:
        """Get structured transcript with timestamps"""
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id,
            languages=['en'],
            preserve_formatting=True
        )
        return [
            {
                'text': entry['text'],
                'start': entry['start'],
                'duration': entry['duration']
            }
            for entry in transcript
        ]

    def _get_video_metadata(self, video_id: str) -> Dict:
        """Get additional video context"""
        response = self.youtube.videos().list(
            id=video_id,
            part='snippet,statistics'
        ).execute()
        
        item = response['items'][0]
        return {
            'published_at': item['snippet']['publishedAt'],
            'channel': item['snippet']['channelTitle'],
            'views': int(item['statistics'].get('viewCount', 0)),
            'likes': int(item['statistics'].get('likeCount', 0)),
            'thumbnail': item['snippet']['thumbnails']['high']['url']
        }