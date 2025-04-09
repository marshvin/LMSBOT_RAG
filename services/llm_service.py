# from llama_index.llms.openai import OpenAI
# from config.config import Config

# class LLMService:
#     def __init__(self):
#         self.llm = OpenAI(api_key=Config.OPENAI_API_KEY)

#     def get_llm(self):
#         """Get the LLM instance."""
#         return self.llm 


from typing import List
from google.generativeai import configure, GenerativeModel, GenerationConfig
from llama_index.llms.base.openai import Whisper
from config.config import Config
class LLMService:   
    
    # FOR OPEN API
    # def __init__(self):
        
    #     # Configure the Gemini API
    #     configure(api_key=Config.GEMINI_API_KEY)
        
    #     # Initialize the Gemini Pro model
    #     self.llm = GenerativeModel('gemini-pro')

    # def get_llm(self):
    #     """Get the Gemini LLM instance with safety settings"""
    #     return self.llm
    
    # def get_embedding_model(self):
    #     return self.llm.get_embeddings_model()
    
     def __init__(self):
        configure(api_key=Config.GEMINI_API_KEY)
        self.text_model = GenerativeModel('gemini-pro')
        self.embedding_model = GenerativeModel('embedding-001')  # Gemini's embedding model

     def generate(self, prompt: str, context: str = None) -> str:
        """Generate text response with optional RAG context"""
        full_prompt = f"{context}\n\nQuestion: {prompt}" if context else prompt
        
        response = self.text_model.generate_content(
            full_prompt,
            generation_config=GenerationConfig(
                temperature=0.3,
                top_p=0.95,
                top_k=40,
                max_output_tokens=2048
            ),
            safety_settings={
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'
            }
        )
        return response.text

     def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        return [self.embedding_model.embed_content(text)['embedding'] for text in texts]

     def get_embedding_model(self):
        """Get the embedding model instance"""
        return self.embedding_model