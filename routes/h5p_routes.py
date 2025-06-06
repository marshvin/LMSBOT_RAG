# routes/h5p_routes.py
from flask import Blueprint, request, jsonify, current_app, send_file
import time
import gc
import os
import logging
import json
import uuid

h5p_bp = Blueprint('h5p', __name__, url_prefix='/api/h5p')

@h5p_bp.route('/generate', methods=['POST'])
def generate_h5p():
    """Endpoint for generating H5P content"""
    try:
        # Lazy load RAG engine
        get_component = current_app.config['GET_COMPONENT']
        rag_engine = get_component("rag_engine")
        
        data = request.json
        
        if not data or 'query' not in data:
            return jsonify({
                "error": "Missing 'query' parameter"
            }), 400
        
        query_text = data['query']
        content_type = data.get('content_type', 'quiz')  # Default to quiz if not specified
        course = data.get('course')  # Get course information
        
        if not course:
            return jsonify({
                "error": "Course information is required"
            }), 400
        
        # Input validation
        if not query_text or len(query_text.strip()) == 0:
            return jsonify({
                "error": "Query cannot be empty"
            }), 400
            
        # Limit query length
        if len(query_text) > 500:
            return jsonify({
                "error": "Query too long (max 500 characters)"
            }), 400
        
        # Add content type to query if not present
        if content_type not in query_text.lower():
            query_text = f"generate {content_type} about {query_text}"
        
        print(f"Generating H5P content for query: {query_text}")
        
        # Generate H5P content
        try:
            h5p_content = rag_engine.generate_h5p_content(query_text, course)
            print(f"Generated H5P content: {h5p_content[:200]}...")  # Print first 200 chars
        except Exception as e:
            print(f"Error generating H5P content: {str(e)}")
            return jsonify({
                "error": f"Failed to generate H5P content: {str(e)}"
            }), 500
        
        # Extract JSON content from the response
        try:
            # Find JSON content between ```json and ```
            json_start = h5p_content.find('```json')
            if json_start == -1:
                print("No ```json marker found in content")
                return jsonify({
                    "error": "Invalid H5P content format: No JSON content found"
                }), 500
                
            json_start += 7  # Length of ```json
            json_end = h5p_content.find('```', json_start)
            
            if json_end == -1:
                print("No closing ``` marker found in content")
                return jsonify({
                    "error": "Invalid H5P content format: No closing JSON marker"
                }), 500
            
            json_content = h5p_content[json_start:json_end].strip()
            print(f"Extracted JSON content: {json_content[:200]}...")  # Print first 200 chars
            
            quiz_data = json.loads(json_content)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {str(e)}")
            return jsonify({
                "error": f"Failed to parse H5P JSON content: {str(e)}"
            }), 500
        except Exception as e:
            print(f"Error extracting JSON content: {str(e)}")
            return jsonify({
                "error": f"Failed to extract H5P content: {str(e)}"
            }), 500
        
        # Generate a unique filename and content ID
        timestamp = int(time.time())
        content_id = str(uuid.uuid4())
        filename = f"{content_type}_{timestamp}.h5p"
        
        # Create temp directory if it doesn't exist
        temp_dir = os.path.join(current_app.root_path, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create H5P package structure
        package_dir = os.path.join(temp_dir, f"package_{timestamp}")
        os.makedirs(package_dir, exist_ok=True)
        
        # Create content directory
        content_dir = os.path.join(package_dir, 'content')
        os.makedirs(content_dir, exist_ok=True)
        
        try:
            # Add content ID to quiz data
            quiz_data['contentId'] = content_id
            
            # Write content.json
            with open(os.path.join(content_dir, 'content.json'), 'w', encoding='utf-8') as f:
                json.dump(quiz_data, f, indent=2)
            
            # Create h5p.json with required fields
            h5p_json = {
                "title": quiz_data.get('title', 'Quiz'),
                "language": "en",
                "mainLibrary": "H5P.QuestionSet",
                "embedTypes": ["div"],
                "license": "U",
                "authors": [{"name": "RAG System", "role": "Author"}],
                "preloadedDependencies": [
                    {
                        "machineName": "H5P.QuestionSet",
                        "majorVersion": "1",
                        "minorVersion": "0"
                    },
                    {
                        "machineName": "H5P.MultiChoice",
                        "majorVersion": "1",
                        "minorVersion": "0"
                    }
                ],
                "contentId": content_id
            }
            
            with open(os.path.join(package_dir, 'h5p.json'), 'w', encoding='utf-8') as f:
                json.dump(h5p_json, f, indent=2)
            
            # Create the H5P package (zip file)
            import zipfile
            zip_path = os.path.join(temp_dir, filename)
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(package_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, package_dir)
                        zipf.write(file_path, arcname)
            
            print(f"Created H5P package at: {zip_path}")
            
            # Clean up package directory
            import shutil
            shutil.rmtree(package_dir)
            
            # Force garbage collection
            gc.collect()
            
            # Generate full URL for download
            download_url = f"{request.host_url}api/h5p/download/{filename}"
            
            result = {
                "query": query_text,
                "h5p_content": h5p_content,
                "content_type": content_type,
                "course": course,
                "download_url": download_url,
                "filename": filename,
                "content_id": content_id
            }
            
            return jsonify(result)
            
        except Exception as e:
            print(f"Error creating H5P package: {str(e)}")
            # Clean up any temporary files
            try:
                if os.path.exists(package_dir):
                    shutil.rmtree(package_dir)
                if os.path.exists(zip_path):
                    os.remove(zip_path)
            except:
                pass
            return jsonify({
                "error": f"Failed to create H5P package: {str(e)}"
            }), 500
            
    except Exception as e:
        print(f"Unexpected error in generate_h5p: {str(e)}")
        return jsonify({
            "query": data.get('query', ''),
            "response": "I'm sorry, I encountered an error while generating H5P content. Please try again.",
            "error": f"Internal server error: {str(e)}"
        }), 500

@h5p_bp.route('/structured-generate', methods=['POST'])
def structured_generate_h5p():
    """Endpoint for structured H5P content generation with detailed parameters"""
    try:
        # Lazy load RAG engine
        get_component = current_app.config['GET_COMPONENT']
        rag_engine = get_component("rag_engine")
        
        data = request.json
        
        # Validate required fields
        if not data:
            return jsonify({"error": "Missing request body"}), 400
            
        if 'query' not in data:
            return jsonify({"error": "Missing 'query' field in request"}), 400
        
        # Extract request parameters
        query = data['query']
        content_type = data.get('content_type', 'quiz')
        course = data.get('course')  # Use course name/id consistent with other endpoints
        name = data.get('name', f"{content_type.capitalize()} on {query[:20]}")
        intro = data.get('intro', f"Auto-generated {content_type} about {query[:50]}")
        
        # Advanced parameters (optional)
        parameters = {}
        if 'parameters' in data:
            if isinstance(data['parameters'], str):
                try:
                    parameters = json.loads(data['parameters'])
                except:
                    parameters = {}
            elif isinstance(data['parameters'], dict):
                parameters = data['parameters']
        
        # Extract source filter if provided
        source_filter = data.get('source_filter')
        
        # Generate H5P content
        h5p_content = rag_engine.generate_h5p_content(query, course)
        
        # Prepare success response
        result = {
            "success": True,
            "message": "H5P content generated successfully.",
            "activity_id": int(time.time()),  # Mock ID, would be real in production
            "download_url": f"{request.host_url}api/h5p/download/{content_type}_{int(time.time())}.h5p",
            "content_info": _generate_content_info(content_type, query, parameters),
            "h5p_content": h5p_content
        }
        
        # Force garbage collection
        gc.collect()
        
        return jsonify(result)
    except Exception as e:
        print(f"Error in structured H5P generation: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error generating H5P content: {str(e)}",
            "error": "Internal server error"
        }), 500

@h5p_bp.route('/publish-to-moodle', methods=['POST'])
def publish_to_moodle():
    """Endpoint for generating H5P content and publishing directly to Moodle"""
    try:
        # Lazy load components
        get_component = current_app.config['GET_COMPONENT']
        rag_engine = get_component("rag_engine")
        
        # Initialize Moodle client if not already available
        if "moodle_client" not in current_app.config['COMPONENTS']:
            # Get Moodle configuration from environment variables
            moodle_url = os.getenv('MOODLE_URL')
            moodle_token = os.getenv('MOODLE_TOKEN')
            
            if not moodle_url or not moodle_token:
                return jsonify({
                    "error": "Moodle integration not configured. Please set MOODLE_URL and MOODLE_TOKEN environment variables."
                }), 400
            
            # Initialize Moodle client
            from rag_components.moodle_client import MoodleClient
            moodle_client = MoodleClient(moodle_url, moodle_token)
            current_app.config['COMPONENTS']["moodle_client"] = moodle_client
        else:
            moodle_client = current_app.config['COMPONENTS']["moodle_client"]
        
        # Extract request data
        data = request.json
        
        if not data or 'query' not in data or 'course' not in data:
            return jsonify({
                "error": "Missing required parameters: 'query' and 'course' are required"
            }), 400
        
        query_text = data['query']
        course_name = data['course']
        content_type = data.get('content_type', 'quiz')
        activity_name = data.get('activity_name', f"{content_type.capitalize()} on {query_text[:30]}")
        section = data.get('section', 0)
        
        # Input validation
        if not query_text or len(query_text.strip()) == 0:
            return jsonify({
                "error": "Query cannot be empty"
            }), 400
            
        # Limit query length
        if len(query_text) > 500:
            return jsonify({
                "error": "Query too long (max 500 characters)"
            }), 400
        
        # Add content type to query if not present
        if content_type not in query_text.lower():
            query_text = f"generate {content_type} about {query_text}"
        
        # Generate H5P content
        h5p_content = rag_engine.generate_h5p_content(query_text, course_name)
        
        # Get Moodle course ID
        course = moodle_client.get_course_by_name(course_name)
        if not course:
            return jsonify({
                "error": f"Course '{course_name}' not found in Moodle"
            }), 404
        
        course_id = course['id']
        
        # Create intro text
        intro = f"Automatically generated {content_type} about {query_text[:100]}"
        
        # Create H5P activity in Moodle
        try:
            result = moodle_client.create_h5p_activity(
                course_id=course_id,
                name=activity_name,
                intro=intro,
                h5p_content=h5p_content,
                section=section
            )
            
            # Force garbage collection
            gc.collect()
            
            return jsonify({
                "success": True,
                "message": f"H5P {content_type} created successfully in Moodle course '{course_name}'",
                "activity_name": activity_name,
                "course": course_name,
                "moodle_activity_id": result.get("id"),
                "content_type": content_type,
                "h5p_content": h5p_content  # Return content in case manual upload is needed
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Error creating H5P activity in Moodle: {str(e)}",
                "h5p_content": h5p_content  # Return content so it's not lost
            }), 500
        
    except Exception as e:
        print(f"Error publishing H5P content to Moodle: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

@h5p_bp.route('/types', methods=['GET'])
def get_h5p_types():
    """Return available H5P content types"""
    return jsonify({
        "types": [
            {
                "id": "quiz",
                "name": "Quiz",
                "description": "Multiple choice questions with feedback"
            },
            {
                "id": "interactive_video",
                "name": "Interactive Video",
                "description": "Add interactivity to videos with questions and annotations"
            },
            {
                "id": "course_presentation",
                "name": "Course Presentation",
                "description": "Create a slideshow with interactive elements"
            },
            {
                "id": "flashcards",
                "name": "Flashcards",
                "description": "Create flashcards for memorization and learning"
            },
            {
                "id": "drag_and_drop",
                "name": "Drag and Drop",
                "description": "Create drag and drop exercises for interactive learning"
            }
        ]
    })

@h5p_bp.route('/download/<filename>', methods=['GET'])
def download_h5p(filename):
    """Download H5P file"""
    try:
        # Get the file path
        temp_dir = os.path.join(current_app.root_path, 'temp')
        file_path = os.path.join(temp_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                "error": "File not found"
            }), 404
        
        # Send the file
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/zip'
        )
    except Exception as e:
        return jsonify({
            "error": f"Error downloading H5P file: {str(e)}"
        }), 500
    finally:
        # Clean up the temporary file after sending
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass  # Ignore cleanup errors

def _generate_content_info(content_type, prompt, parameters):
    """Generate a description of the H5P content based on parameters"""
    
    if content_type == "quiz":
        # Extract parameters
        quantity = parameters.get("quantity", 5)
        difficulty = parameters.get("difficulty", "intermediate")
        question_types = parameters.get("question_types", ["multiple_choice"])
        
        # Format question types for display
        formatted_types = []
        type_counts = {}
        
        for qt in question_types:
            display_name = qt.replace("_", " ")
            if display_name in type_counts:
                type_counts[display_name] += 1
            else:
                type_counts[display_name] = 1
        
        for display_name, count in type_counts.items():
            formatted_types.append(f"{count} {display_name}")
            
        question_types_str = " and ".join(formatted_types)
        
        return f"{quantity}-question {difficulty} quiz about {prompt[:50]} with {question_types_str} questions"
    
    else:
        return f"{content_type} about {prompt[:50]}" 