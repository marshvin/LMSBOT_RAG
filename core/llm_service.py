from llama_index.llms.openai import OpenAI
from config.config import Config

class LLMService:
    def __init__(self):
        self.llm = OpenAI(api_key=Config.OPENAI_API_KEY)

    def get_llm(self):
        """Get the LLM instance."""
        return self.llm 