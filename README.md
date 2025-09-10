# FinTracker-AI

Pequeno assistente de gestão financeira via Telegram que registra transações a partir de imagens, textos ou áudios.

## Resumo rápido
- **Objetivo**: permitir que o usuário envie recibos, notas fiscais, textos ou áudios para registrar transações automaticamente em um banco SQLite.
- **Principais componentes**: bot Telegram (`telegram_bot.py`), gerenciador de banco (`database_manager.py`), transcrição de áudio (`speech_to_text.py`), integração com um cliente de IA (`gemini_vision.py`) e script principal (`main.py`).
- **Estado atual**: a transcrição de áudio está mockada para retornar um texto padrão quando o ambiente de speech-to-text não estiver disponível (compatibilidade com Python 3.13).

## Instalação mínima
1. Criar um ambiente virtual e ativar:

    ```fish
    python -m venv .venv
    source .venv/bin/activate.fish
    ```

2. Instalar dependências (ajuste em `req.txt` se necessário):

    ```fish
    pip install -r req.txt
    ```

## Execução
1. Configurar `config.py` com o token do bot e credenciais da API de IA.
2. Rodar o bot:

    ```fish
    python main.py
    ```

## Notas importantes
- `speech_to_text.py` atualmente usa um mock simples para evitar dependências quebradas em Python 3.13; ao reativar, prefira bibliotecas compatíveis ou usar serviços externos.
- `.gitignore` já foi criado para ignorar `financial_data.db`, caches e artefatos.
- O banco SQLite `financial_data.db` é criado localmente; não o adicione ao repositório.

## Contribuição
- Abra issues e pull requests no repositório GitHub: https://github.com/gutzuh/FinTracker-AI

## Licença
- Escolha uma licença apropriada adicionando um arquivo `LICENSE`.
