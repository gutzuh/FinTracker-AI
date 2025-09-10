from fastapi import FastAPI, Request
import json
import logging

app = FastAPI()
logger = logging.getLogger("vercel_webhook")

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

    # Aqui você pode integrar com `telegram_bot.TelegramBot` ou processar o update
    # No momento apenas respondemos OK para que o webhook funcione.
    return {"ok": True}
