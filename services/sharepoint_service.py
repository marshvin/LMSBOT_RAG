# Share Point video service for LMSBOT_RAG
# Accessing the sharepoint videos via the public url    

from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.client_credential import ClientCredential
from typing import List, Dict, Optional, IO
import io
import logging
from config.config import Config
from urllib.parse import urljoin

class SharePointVideoService:
    def __init__(self,
                 site_url: str = None,
                 client_id: str = None,
                 client_secret: str = None):
        """
        Initialize SharePoint service for video access
        
        Args:
            site_url: SharePoint site URL (e.g., "https://company.sharepoint.com/sites/training")
            client_id: Azure AD app client ID
            client_secret: Azure AD app client secret
        """
        self.site_url = site_url or Config.SHAREPOINT_SITE_URL
        self.client_id = client_id or Config.SHAREPOINT_CLIENT_ID
        self.client_secret = client_secret or Config.SHAREPOINT_CLIENT_SECRET
        self.ctx = self._authenticate()

    def _authenticate(self):
        """Authenticate using app credentials"""
        credentials = ClientCredential(
            self.client_id,
            self.client_secret
        )
        return ClientContext(self.site_url).with_credentials(credentials)

    def list_videos(self, library_name: str = "Videos") -> List[Dict]:
        """List all videos in a document library"""
        try:
            lib = self.ctx.web.lists.get_by_title(library_name)
            items = lib.items.select(["FileRef", "FileLeafRef", "Modified"]).get().execute_query()
            
            return [{
                'id': item.id,
                'name': item.file_leaf_ref,
                'path': item.file_ref,
                'modified': item.modified,
                'url': urljoin(self.site_url, item.file_ref)
            } for item in items if item.file_leaf_ref.lower().endswith(('.mp4', '.mov', '.avi'))]
            
        except Exception as e:
            logging.error(f"SharePoint list error: {str(e)}")
            raise SharePointError(f"Failed to list videos: {str(e)}")

    def get_video_stream(self, server_path: str) -> IO[bytes]:
        """Get video as in-memory file stream"""
        try:
            file = self.ctx.web.get_file_by_server_relative_url(server_path)
            file_bytes = file.read()
            return io.BytesIO(file_bytes)
        except Exception as e:
            logging.error(f"Video stream error: {str(e)}")
            raise SharePointError(f"Failed to get video stream: {str(e)}")

    def get_video_metadata(self, server_path: str) -> Dict:
        """Get extended video metadata"""
        try:
            file = self.ctx.web.get_file_by_server_relative_url(server_path)
            self.ctx.load(file, ["Length", "TimeLastModified", "Author"])
            self.ctx.execute_query()
            
            return {
                'size': file.length,
                'modified': file.time_last_modified,
                'author': file.author.login_name,
                'path': server_path
            }
        except Exception as e:
            logging.error(f"Metadata error: {str(e)}")
            raise SharePointError(f"Failed to get metadata: {str(e)}")

class SharePointError(Exception):
    """Custom SharePoint service exceptions"""
    pass