# routes/youtube_routes.py
from flask import Blueprint, request, jsonify, current_app

youtube_bp = Blueprint('youtube', __name__, url_prefix='/api')

@youtube_bp.route('/youtube/load', methods=['POST'])
def load_youtube():
    """Load videos from YouTube channel"""
    components = current_app.config['COMPONENTS']
    youtube_loader = components['youtube_loader']
    document_processor = components['document_processor']
    
    data = request.json
    
    # Override default YouTube settings if provided
    if data and 'channel_id' in data:
        youtube_loader.channel_id = data['channel_id']
    
    if data and 'max_videos' in data:
        youtube_loader.max_videos = data['max_videos']
    
    try:
        processed_ids = youtube_loader.load_and_process(document_processor)
        
        return jsonify({
            "message": f"Processed {len(processed_ids)} videos",
            "document_ids": processed_ids
        })
    except Exception as e:
        return jsonify({
            "error": f"Error loading YouTube videos: {str(e)}"
        }), 500