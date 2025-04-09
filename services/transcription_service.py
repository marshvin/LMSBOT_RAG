from openai import OpenAI
import base64

class WhisperTranscriptionService:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
    
    def transcribe_stream(self, file_stream):
        """Transcribe in-memory video stream"""
        file_stream.seek(0)
        transcript = self.client.audio.transcriptions.create(
            file=("video.mp4", file_stream),
            model="whisper-1",
            response_format="verbose_json",
            timestamp_granularities=["segment"]
        )
        return transcript.model_dump()
    
    # Make sure this dump is stored in the database