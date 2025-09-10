from fastapi import FastAPI, Request
import json
import logging
import os
import httpx

from gemini_vision import GeminiAIClient
from database_manager import DatabaseManager
from speech_to_text import SpeechToText

app = FastAPI()
logger = logging.getLogger("vercel_webhook")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}" if TELEGRAM_TOKEN else None
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Instâncias reutilizáveis
gemini_client = GeminiAIClient(GEMINI_API_KEY) if GEMINI_API_KEY else None
db = DatabaseManager()
stt = SpeechToText()


async def _send_telegram_message(chat_id: int, text: str):
    if not TELEGRAM_API:
        logger.info("TELEGRAM_BOT_TOKEN not set; skipping send_message")
        return

    url = TELEGRAM_API + "/sendMessage"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.post(url, json={"chat_id": chat_id, "text": text})
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem Telegram: {e}")


async def _download_telegram_file(file_id: str) -> bytes:
    """Baixa arquivo do Telegram (imagem/voice) e retorna bytes"""
    if not TELEGRAM_API:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # getFile
        r = await client.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id})
        r.raise_for_status()
        data = r.json()
        file_path = data['result']['file_path']
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        r2 = await client.get(file_url)
        r2.raise_for_status()
        return r2.content


def _format_transaction_response(transaction_data):
    response_message = (
        f"✅ Transação registrada com sucesso!\n\n"
        f"🏪 Estabelecimento: {transaction_data.get('establishment', 'Não identificado')}\n"
        f"📅 Data: {transaction_data.get('date', 'Não especificada')}\n"
        f"💰 Valor Total: R$ {transaction_data.get('total_amount', 0):.2f}\n"
        f"🏷️ Categoria: {transaction_data.get('category', 'Outros')}\n"
    )

    if transaction_data.get('items'):
        response_message += "\n🛍️ Itens:\n"
        for item in transaction_data['items']:
            response_message += f"  • {item.get('description', 'Item')}: R$ {item.get('total_price', 0):.2f}\n"

    return response_message


@app.post('/')
async def telegram_webhook(request: Request):
    try:
        update = await request.json()
    except Exception:
        update = await request.body()

    # Salva o último update recebido (útil para debug)
    try:
        with open('last_update.json', 'w') as f:
            json.dump(update, f)
    except Exception as e:
        logger.error(f'Erro salvando update: {e}')

    message = update.get('message') or update.get('edited_message')
    if not message:
        return {"ok": True}

    chat = message.get('chat', {})
    chat_id = chat.get('id')

    try:
        # Texto
        if 'text' in message and chat_id:
            text = message.get('text')
            # Processar com Gemini (se disponível)
            try:
                if gemini_client:
                    transaction_data = gemini_client.analyze_financial_document(text_input=text)
                else:
                    raise RuntimeError('Gemini client não configurado')
            except Exception as e:
                logger.error(f'Gemini erro: {e}')
                # fallback simples
                transaction_data = {
                    'establishment': 'Não identificado',
                    'date': '',
                    'total_amount': 0.0,
                    'category': 'Outros',
                    'items': [],
                    'raw_text': text
                }

            saved = db.save_transaction(chat_id, transaction_data, 'text')
            if saved:
                await _send_telegram_message(chat_id, _format_transaction_response(transaction_data))
            else:
                await _send_telegram_message(chat_id, '❌ Erro ao salvar transação no banco de dados.')

        # Foto
        elif 'photo' in message and chat_id and TELEGRAM_API:
            # Pegar maior resolução
            photo_list = message.get('photo')
            file_id = photo_list[-1].get('file_id')
            try:
                image_bytes = await _download_telegram_file(file_id)
                if gemini_client:
                    transaction_data = gemini_client.analyze_financial_document(image_bytes=image_bytes)
                else:
                    raise RuntimeError('Gemini client não configurado')
            except Exception as e:
                logger.error(f'Erro processando imagem: {e}')
                transaction_data = {
                    'establishment': 'Não identificado',
                    'date': '',
                    'total_amount': 0.0,
                    'category': 'Outros',
                    'items': [],
                    'raw_text': 'Imagem recebida'
                }

            saved = db.save_transaction(chat_id, transaction_data, 'image')
            if saved:
                await _send_telegram_message(chat_id, _format_transaction_response(transaction_data))
            else:
                await _send_telegram_message(chat_id, '❌ Erro ao salvar transação no banco de dados.')

        # Voice
        elif 'voice' in message and chat_id and TELEGRAM_API:
            file_id = message.get('voice', {}).get('file_id')
            try:
                audio_bytes = await _download_telegram_file(file_id)
                transcribed = stt.transcribe_audio(audio_bytes)
                if gemini_client:
                    transaction_data = gemini_client.analyze_financial_document(text_input=transcribed)
                else:
                    raise RuntimeError('Gemini client não configurado')
            except Exception as e:
                logger.error(f'Erro processando voice: {e}')
                transaction_data = {
                    'establishment': 'Não identificado',
                    'date': '',
                    'total_amount': 0.0,
                    'category': 'Outros',
                    'items': [],
                    'raw_text': 'Áudio recebido'
                }

            saved = db.save_transaction(chat_id, transaction_data, 'voice')
            if saved:
                await _send_telegram_message(chat_id, _format_transaction_response(transaction_data))
            else:
                await _send_telegram_message(chat_id, '❌ Erro ao salvar transação no banco de dados.')

        else:
            if chat_id:
                await _send_telegram_message(chat_id, 'Recebi seu conteúdo — estou processando.')

    except Exception as e:
        logger.error(f'Erro geral no processamento do update: {e}')
        if chat_id:
            await _send_telegram_message(chat_id, '❌ Erro interno ao processar sua mensagem.')

    return {"ok": True}
