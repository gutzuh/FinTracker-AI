from telegram_bot import TelegramBot
from gemini_vision import GeminiAIClient
from config import Config
import logging

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    config = Config()
    gemini_client = GeminiAIClient(config.GEMINI_API_KEY)
    bot = TelegramBot(config.TELEGRAM_BOT_TOKEN, gemini_client)
    
    # logger.info("Bot iniciado com processamento de imagem, texto, áudio e banco de dados")
    bot.start()

if __name__ == "__main__":
    main()
