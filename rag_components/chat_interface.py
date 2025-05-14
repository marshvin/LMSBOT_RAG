# rag_components/chat_interface.py
class ChatInterface:
    def __init__(self, rag_engine):
        self.rag_engine = rag_engine
        self.chat_history = []
    
    def start(self):
        """Start the chat interface"""
        print("Welcome to the RAG Chatbot! Type 'exit' to quit.")
        print("You can ask questions or generate H5P content by typing 'generate h5p quiz about [topic]'")
        
        while True:
            user_input = input("\nYou: ")
            
            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break
            
            # Check if the user wants to generate H5P content
            if "h5p" in user_input.lower() or "generate quiz" in user_input.lower() or "create assessment" in user_input.lower():
                # Process the query for H5P content
                h5p_content = self.rag_engine.generate_h5p_content(user_input)
                
                # Store the interaction in chat history
                self.chat_history.append({"user": user_input, "bot": "H5P content generated"})
                
                # Display a summary of the generated content
                print(f"\nBot: {h5p_content}")
                continue
            
            # Process regular query through RAG
            response = self.rag_engine.answer_query(user_input)
            
            # Store the interaction in chat history
            self.chat_history.append({"user": user_input, "bot": response})
            
            # Display the response
            print(f"\nBot: {response}")