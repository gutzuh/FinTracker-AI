from fastapi import FastAPI, Request
import json
import logging
import os
import httpx

app = FastAPI()
logger = logging.getLogger("vercel_webhook")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}" if TELEGRAM_TOKEN else None


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

    # Resposta mínima: se for uma mensagem de texto, responde com confirmação.
    try:
        message = update.get('message') or update.get('edited_message')
        if message:
            chat = message.get('chat', {})
            chat_id = chat.get('id')
            if 'text' in message and chat_id:
                text = message.get('text')
                reply = f"Recebido pelo FinTracker (via Vercel): {text}"
                await _send_telegram_message(chat_id, reply)
            else:
                # Para fotos/voices/other, notifica que foi recebido
                if chat_id:
                    await _send_telegram_message(chat_id, "Recebi seu arquivo/mensagem — processando depois.")
    except Exception as e:
        logger.error(f"Erro processando update: {e}")

    return {"ok": True}
