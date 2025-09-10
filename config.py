import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        load_dotenv()
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        
        if not self.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN não encontrado no arquivo .env")
        
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY não encontrado no arquivo .env")
