# routes/youtube_routes.py
from flask import Blueprint, request, jsonify, current_app
import gc

youtube_bp = Blueprint('youtube', __name__, url_prefix='/api')

@youtube_bp.route('/youtube/load', methods=['POST'])
def load_youtube():
    """Load videos from YouTube channel"""
    # Lazy load components when needed
    get_component = current_app.config['GET_COMPONENT']
    youtube_loader = get_component("youtube_loader")
    document_processor = get_component("document_processor")
    
    data = request.json
    
    # Require course information
    if not data or 'course' not in data:
        return jsonify({
            "error": "Course information is required"
        }), 400
    
    course = data['course']
    
    # Override default YouTube settings if provided
    if 'channel_id' in data:
        youtube_loader.channel_id = data['channel_id']
    
    if 'max_videos' in data:
        # Limit max videos for memory reasons
        youtube_loader.max_videos = min(data.get('max_videos', 20), 20)  # Max 20 videos
    
    try:
        processed_ids = youtube_loader.load_and_process(document_processor, course=course)
        
        # Run garbage collection
        gc.collect()
        
        return jsonify({
            "message": f"Processed {len(processed_ids)} videos for course: {course}",
            "document_ids": processed_ids,
            "course": course
        })
    except Exception as e:
        return jsonify({
            "error": f"Error loading YouTube videos: {str(e)}"
        }), 500