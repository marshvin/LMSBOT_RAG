import requests
import json
import logging
from typing import Optional, Dict, Any
import os
from urllib.parse import urljoin

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MoodleClient')

class MoodleClient:
    def __init__(self, base_url: str, token: str):
        """
        Initialize the Moodle API client
        
        Args:
            base_url: The base URL of the Moodle instance (e.g., https://moodle.example.com)
            token: The API token for authentication
        """
        # Ensure base_url doesn't end with a slash
        self.base_url = base_url.rstrip('/')
        self.token = token
        
        # Construct the webservice URL properly
        self.webservice_url = urljoin(self.base_url, '/webservice/rest/server.php')
        
        logger.info(f"Initialized Moodle client for {self.base_url}")
        logger.info(f"Webservice URL: {self.webservice_url}")
        
        # Test connection and validate token
        self._test_connection()
        self._validate_token()
    
    def _test_connection(self):
        """Test the connection to Moodle"""
        try:
            # Make a simple request to check connection
            response = requests.get(self.base_url)
            response.raise_for_status()
            logger.info("Successfully connected to Moodle server")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Moodle server at {self.base_url}: {str(e)}")
            raise ConnectionError(f"Could not connect to Moodle server at {self.base_url}. Please verify the server is running and the URL is correct.")
    
    def _validate_token(self):
        """Validate the token by making a test request"""
        try:
            # Try to get site info as a token validation test
            response = self._make_request('core_webservice_get_site_info')
            logger.info("Token validation successful")
            return response
        except Exception as e:
            error_msg = str(e)
            if "Invalid token" in error_msg:
                logger.error("Invalid token. Please check if the token is correct and has not expired.")
                raise ValueError("Invalid Moodle token. Please verify the token is correct and has not expired.")
            elif "Access control exception" in error_msg:
                logger.error("Token does not have required permissions. Please check token capabilities.")
                raise PermissionError("Token does not have required permissions. Please check token capabilities.")
            else:
                logger.error(f"Error validating token: {error_msg}")
                raise
    
    def _make_request(self, function: str, params: Dict[str, Any] = None) -> Dict:
        """Make a request to the Moodle API"""
        if params is None:
            params = {}
            
        # Add required parameters
        params.update({
            'wstoken': self.token,
            'wsfunction': function,
            'moodlewsrestformat': 'json'
        })
        
        try:
            logger.info(f"Making request to {self.webservice_url} with function {function}")
            response = requests.post(self.webservice_url, params)
            response.raise_for_status()
            
            # Check for Moodle-specific errors in the response
            result = response.json()
            if isinstance(result, dict) and 'exception' in result:
                error_msg = result.get('message', 'Unknown error')
                if 'Invalid token' in error_msg:
                    raise ValueError(f"Invalid token: {error_msg}")
                elif 'Access control exception' in error_msg:
                    raise PermissionError(f"Permission denied: {error_msg}")
                else:
                    raise Exception(f"Moodle error: {error_msg}")
                    
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to Moodle API: {str(e)}")
            if "Connection refused" in str(e):
                logger.error("Connection refused. Please check if Moodle server is running and web services are enabled.")
            raise
    
    def get_courses(self) -> Dict:
        """Get all courses from Moodle"""
        return self._make_request('core_course_get_courses')
    
    def get_course_by_name(self, course_name: str) -> Optional[Dict]:
        """Get a course by name"""
        courses = self.get_courses()
        for course in courses:
            if course['fullname'].lower() == course_name.lower() or course['shortname'].lower() == course_name.lower():
                return course
        return None
    
    def create_h5p_activity(self, course_id: int, name: str, intro: str, h5p_content: str, section: int = 0) -> Dict:
        """
        Create an H5P activity in a Moodle course
        
        Args:
            course_id: The ID of the course
            name: The name of the H5P activity
            intro: Introduction text
            h5p_content: The H5P content in JSON format
            section: The section number (0-based)
        """
        try:
            # First, create an H5P activity instance
            activity_params = {
                'courseids[0]': course_id,
                'h5pactivities[0][name]': name,
                'h5pactivities[0][intro]': intro,
                'h5pactivities[0][introformat]': 1,  # 1 = HTML format
                'h5pactivities[0][course]': course_id,
                'h5pactivities[0][section]': section,
                'h5pactivities[0][visible]': 1,
                'h5pactivities[0][displayoptions]': 0
            }
            
            result = self._make_request('mod_h5pactivity_add_instance', activity_params)
            
            # Note: Uploading the actual H5P content requires additional steps
            # that may depend on your Moodle version and configuration
            
            return result
        except Exception as e:
            logger.error(f"Error creating H5P activity: {str(e)}")
            raise
    
    def upload_h5p_content(self, activity_id: int, h5p_content: str) -> Dict:
        """
        Upload H5P content to an existing activity
        
        Note: This is a placeholder method - actual implementation
        depends on your Moodle version and configuration
        """
        # This is a simplified version - actual implementation would require:
        # 1. Converting the H5P content to a valid H5P package file
        # 2. Uploading the file via Moodle's file API
        # 3. Associating the file with the H5P activity
        
        logger.warning("H5P content upload not fully implemented - requires Moodle-specific handling")
        
        # For now, we just log the content that would be uploaded
        logger.info(f"Would upload H5P content to activity {activity_id}")
        return {"status": "not_implemented", "message": "H5P content upload requires Moodle-specific handling"} 