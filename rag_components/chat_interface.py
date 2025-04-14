# rag_components/chat_interface.py
class ChatInterface:
    def __init__(self, rag_engine):
        self.rag_engine = rag_engine
        self.chat_history = []
    
    def start(self):
        """Start the chat interface"""
        print("Welcome to the RAG Chatbot! Type 'exit' to quit.")
        
        while True:
            user_input = input("\nYou: ")
            
            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break
            
            # Process the query through RAG
            response = self.rag_engine.answer_query(user_input)
            
            # Store the interaction in chat history
            self.chat_history.append({"user": user_input, "bot": response})
            
            # Display the response
            print(f"\nBot: {response}")