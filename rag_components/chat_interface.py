# rag_components/chat_interface.py
import re
import json
import requests
import os
from typing import Dict, List, Optional, Any

class ChatInterface:
    def __init__(self, rag_engine):
        self.rag_engine = rag_engine
        self.chat_history = []
        self.h5p_conversation_state = None
        self.h5p_content_types = {
            "quiz": "Question Set",
            "course_presentation": "Course Presentation",
            "interactive_video": "Interactive Video",
            "flashcards": "Flashcards",
            "drag_and_drop": "Drag and Drop"
        }
    
    def start(self):
        """Start the chat interface"""
        print("Welcome to the RAG Chatbot! Type 'exit' to quit.")
        print("You can ask questions or generate H5P content by typing 'create a quiz about [topic]'")
        
        while True:
            user_input = input("\nYou: ")
            
            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break
            
            # Process the user's message
            response = self.process_message(user_input)
            
            # Display the response
            print(f"\nBot: {response}")
    
    def process_message(self, user_input: str) -> str:
        """Process a user message and return an appropriate response"""
        # Check if we're in an H5P conversation flow
        if self.h5p_conversation_state:
            return self._continue_h5p_conversation(user_input)
        
        # Check if the message is about creating H5P content
        h5p_request = self._is_h5p_request(user_input)
        if h5p_request:
            # Start H5P conversation flow
            content_type, topic = h5p_request
            return self._start_h5p_conversation(content_type, topic)
        
        # If not an H5P request, process as a regular query
            response = self.rag_engine.answer_query(user_input)
            
            # Store the interaction in chat history
            self.chat_history.append({"user": user_input, "bot": response})
            
        return response
    
    def _is_h5p_request(self, text: str) -> Optional[tuple]:
        """
        Check if the text is requesting H5P content creation
        Returns (content_type, topic) if it is, None otherwise
        """
        text_lower = text.lower()
        
        # Patterns for different content types
        patterns = {
            "quiz": r"(create|generate|make)(?:\s+an?|\s+a)?\s+(quiz|test|assessment|exam|questions?)(?:\s+about|on|for)?\s+(.*)",
            "course_presentation": r"(create|generate|make)(?:\s+an?|\s+a)?\s+(presentation|slides|course presentation)(?:\s+about|on|for)?\s+(.*)",
            "interactive_video": r"(create|generate|make)(?:\s+an?|\s+a)?\s+(interactive video|video)(?:\s+about|on|for)?\s+(.*)",
            "flashcards": r"(create|generate|make)(?:\s+an?|\s+a)?\s+(flashcards?)(?:\s+about|on|for)?\s+(.*)",
            "drag_and_drop": r"(create|generate|make)(?:\s+an?|\s+a)?\s+(drag and drop|matching)(?:\s+about|on|for)?\s+(.*)"
        }
        
        # Check each pattern
        for content_type, pattern in patterns.items():
            match = re.match(pattern, text_lower)
            if match:
                topic = match.group(3).strip()
                return (content_type, topic)
        
        # General H5P pattern
        h5p_pattern = r"(create|generate|make)(?:\s+an?|\s+a)?\s+h5p(?:\s+content)?(?:\s+about|on|for)?\s+(.*)"
        match = re.match(h5p_pattern, text_lower)
        if match:
            topic = match.group(2).strip()
            return ("quiz", topic)  # Default to quiz if just "h5p" is mentioned
            
        return None
    
    def _start_h5p_conversation(self, content_type: str, topic: str) -> str:
        """Start a structured conversation to collect H5P parameters"""
        # Initialize conversation state
        self.h5p_conversation_state = {
            "stage": "parameters",
            "content_type": content_type,
            "topic": topic,
            "parameters": {},
            "name": "",
            "description": ""
        }
        
        # Create appropriate prompt based on content type
        if content_type == "quiz":
            return (f"I'd be happy to help you create an H5P quiz about {topic}. "
                   f"Please provide the following details:\n"
                   f"- How many questions should the quiz have?\n"
                   f"- What difficulty level? (beginner, intermediate, advanced)\n"
                   f"- What question types would you like? (multiple choice, true/false, matching, etc.)")
        elif content_type == "course_presentation":
            return (f"I'd be happy to help you create an H5P presentation about {topic}. "
                   f"Please provide the following details:\n"
                   f"- How many slides should the presentation have?\n"
                   f"- What difficulty level? (beginner, intermediate, advanced)\n"
                   f"- Would you like to include interactive elements? (yes/no)")
        elif content_type == "interactive_video":
            return (f"I'd be happy to help you create an H5P interactive video about {topic}. "
                   f"Please provide the following details:\n"
                   f"- Would you like to include questions? (yes/no)\n"
                   f"- What difficulty level? (beginner, intermediate, advanced)\n"
                   f"- Any specific video source you'd like to use?")
        else:
            return (f"I'd be happy to help you create H5P {self.h5p_content_types.get(content_type, content_type)} "
                   f"content about {topic}. Please provide any specific requirements or parameters you'd like to include.")
    
    def _continue_h5p_conversation(self, user_input: str) -> str:
        """Continue an H5P conversation flow based on current stage"""
        state = self.h5p_conversation_state
        
        if state["stage"] == "parameters":
            # Store parameters
            state["parameters"]["user_input"] = user_input
            
            # Extract structured parameters
            self._extract_parameters(user_input)
            
            # Move to next stage - name
            state["stage"] = "name"
            return f"What would you like to name this {self.h5p_content_types.get(state['content_type'], state['content_type'])}?"
            
        elif state["stage"] == "name":
            # Store name
            state["name"] = user_input.strip()
            
            # Move to next stage - description
            state["stage"] = "description"
            return f"Please provide a brief description for the {state['content_type']}."
            
        elif state["stage"] == "description":
            # Store description
            state["description"] = user_input.strip()
            
            # Move to generation stage
            state["stage"] = "generating"
            
            # Generate response
            return self._generate_h5p_content()
            
        elif state["stage"] == "complete":
            # Check if user wants modifications
            if any(word in user_input.lower() for word in ["yes", "modify", "change", "edit"]):
                # Reset to parameter stage to start over
                state["stage"] = "parameters"
                return (f"Let's make some changes to your {state['content_type']}. "
                       f"Please provide the new parameters you'd like to use.")
            
            # If user is satisfied, end the conversation
            self.h5p_conversation_state = None
            return "Great! I hope the H5P content meets your needs. Let me know if you need anything else."
            
        return "I'm not sure how to proceed. Let's start over with your H5P content request."
    
    def _extract_parameters(self, text: str) -> None:
        """Extract structured parameters from user input"""
        state = self.h5p_conversation_state
        text_lower = text.lower()
        
        # Extract number of questions/slides
        quantity_match = re.search(r'(\d+)\s+(question|slide)', text_lower)
        if quantity_match:
            state["parameters"]["quantity"] = int(quantity_match.group(1))
        
        # Extract difficulty level
        if "beginner" in text_lower:
            state["parameters"]["difficulty"] = "beginner"
        elif "intermediate" in text_lower:
            state["parameters"]["difficulty"] = "intermediate"
        elif "advanced" in text_lower:
            state["parameters"]["difficulty"] = "advanced"
        
        # Extract question types for quizzes
        if state["content_type"] == "quiz":
            question_types = []
            if "multiple choice" in text_lower:
                question_types.append("multiple_choice")
            if "true/false" in text_lower or "true false" in text_lower:
                question_types.append("true_false")
            if "matching" in text_lower:
                question_types.append("matching")
            if "fill" in text_lower and "blank" in text_lower:
                question_types.append("fill_blanks")
                
            if question_types:
                state["parameters"]["question_types"] = question_types
    
    def _generate_h5p_content(self) -> str:
        """Generate H5P content based on collected parameters"""
        state = self.h5p_conversation_state
        
        try:
            # Create a structured prompt for the RAG engine
            parameters = state["parameters"]
            difficulty = parameters.get("difficulty", "intermediate")
            quantity = parameters.get("quantity", 5)
            
            if state["content_type"] == "quiz":
                question_types = parameters.get("question_types", ["multiple_choice"])
                question_types_str = " and ".join([qt.replace("_", " ") for qt in question_types])
                query = f"Create a {quantity}-question {difficulty} quiz about {state['topic']} with {question_types_str} questions"
            else:
                query = f"Create a {difficulty} {state['content_type']} about {state['topic']}"
            
            # Generate H5P content
            h5p_content = self.rag_engine.generate_h5p_content(query, None)
            
            # Store the result
            state["result"] = h5p_content
            state["stage"] = "complete"
            
            # If Moodle integration is available, try to publish
            if self._has_moodle_config():
                try:
                    moodle_result = self._publish_to_moodle(query, state)
                    if moodle_result.get("success"):
                        activity_id = moodle_result.get("activity_id", "N/A")
                        download_url = moodle_result.get("download_url", "#")
                        return (f"Your {state['content_type']} has been created successfully! You can:\n"
                               f"- View in course: Activity ID {activity_id}\n"
                               f"- Download: {download_url}\n"
                               f"Would you like to make any changes to this content?")
                except Exception as e:
                    # Log the error but continue with the regular response
                    print(f"Error publishing to Moodle: {str(e)}")
            
            # Return a generic success message if Moodle publishing wasn't done
            return (f"I've generated your {state['content_type']} about {state['topic']}. Here's what it includes:\n\n"
                   f"{h5p_content[:300]}...\n\n"
                   f"Would you like to make any changes to this content?")
            
        except Exception as e:
            # Reset conversation state on error
            self.h5p_conversation_state = None
            return f"I'm sorry, I encountered an error while generating your H5P content: {str(e)}"
    
    def _has_moodle_config(self) -> bool:
        """Check if Moodle configuration is available"""
        return bool(os.getenv("MOODLE_URL") and os.getenv("MOODLE_TOKEN"))
    
    def _publish_to_moodle(self, query: str, state: Dict) -> Dict:
        """Publish H5P content to Moodle using the API"""
        moodle_url = os.getenv("MOODLE_URL", "")
        h5p_endpoint = f"{moodle_url}/webservice/rest/server.php"
        
        # Prepare data for the API request - using 'query' for consistency
        data = {
            "query": query,
            "content_type": state["content_type"],
            "course": "demo",  # This should be dynamically set or retrieved
            "name": state["name"],
            "intro": state["description"],
            "parameters": json.dumps(state["parameters"])
        }
        
        # Make API request
        # This is a mock implementation - in a real system, you would call your Moodle API
        # response = requests.post(h5p_endpoint, json=data)
        # return response.json()
        
        # For now, return a mock success response
        return {
            "success": True,
            "message": "H5P content generated successfully.",
            "activity_id": 456,
            "download_url": f"{moodle_url}/pluginfile.php/123/mod_h5pactivity/package/{state['content_type']}_{456}.h5p",
            "content_info": f"Generated {state['content_type']} about {state['topic']}"
        }