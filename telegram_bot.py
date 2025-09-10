from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import logging
from database_manager import DatabaseManager
from speech_to_text import SpeechToText

logger = logging.getLogger(__name__)

# Estados para a conversa de limpeza do banco
CONFIRM_CLEAR = 1

class TelegramBot:
    def __init__(self, token, gemini_client):
        self.gemini_client = gemini_client
        self.db_manager = DatabaseManager()
        self.speech_to_text = SpeechToText()
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        # Handler para limpeza de banco (com confirmação)
        clear_conv = ConversationHandler(
            entry_points=[CommandHandler('limpar', self.clear_command)],
            states={
                CONFIRM_CLEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm_clear)]
            },
            fallbacks=[CommandHandler('cancelar', self.cancel_clear)]
        )
        
        self.application.add_handler(clear_conv)
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("extrato", self.extrato_command))
        self.application.add_handler(CommandHandler("resumo", self.resumo_command))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🤖 *FinTracker AI - Sistema de Gestão Financeira*\n\n"
            "Envie fotos de recibos, notas fiscais, áudios ou textos para registro automático.\n\n"
            "Comandos disponíveis:\n"
            "/extrato - Ver últimas transações\n"
            "/resumo - Resumo financeiro por categorias\n"
            "/limpar - Limpar banco de dados (com confirmação)\n\n"
            "Aceito:\n"
            "📷 Fotos de documentos\n"
            "🎤 Áudios descrevendo gastos\n"
            "📝 Textos com transações",
            parse_mode="Markdown"
        )
    
    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📷 Processando documento financeiro...")
        
        try:
            photo = await update.message.photo[-1].get_file()
            image_bytes = await photo.download_as_bytearray()
            
            # Processar com Gemini AI
            transaction_data = self.gemini_client.analyze_financial_document(image_bytes=image_bytes)
            
            # Salvar no banco de dados
            if self.db_manager.save_transaction(update.effective_chat.id, transaction_data, "image"):
                response_message = self._format_transaction_response(transaction_data)
                await update.message.reply_text(response_message, parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Erro ao salvar transação no banco de dados.")
            
        except Exception as e:
            logger.error(f"Erro no processamento: {str(e)}")
            await update.message.reply_text("❌ Erro ao processar documento. Tente novamente com uma imagem mais nítida.")
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        
        # Ignorar comandos de confirmação de limpeza
        if text.upper() in ['SIM', 'NÃO', 'NAO', 'CANCELAR']:
            return
        
        await update.message.reply_text("📝 Processando descrição de transação...")
        
        try:
            # Processar com Gemini AI
            transaction_data = self.gemini_client.analyze_financial_document(text_input=text)
            
            # Log para debugging
            logger.info(f"Dados processados: {transaction_data}")
            
            # Verificar se os dados essenciais estão presentes
            if not transaction_data.get('total_amount', 0) > 0:
                await update.message.reply_text(
                    "❌ Não consegui identificar um valor na transação. "
                    "Por favor, seja mais específico sobre o valor gasto. "
                    "Exemplo: 'Gastei 200 reais em um mouse'"
                )
                return
            
            # Salvar no banco de dados
            if self.db_manager.save_transaction(update.effective_chat.id, transaction_data, "text"):
                response_message = self._format_transaction_response(transaction_data)
                await update.message.reply_text(response_message, parse_mode="Markdown")
            else:
                await update.message.reply_text(
                    "❌ Erro ao salvar transação no banco de dados. "
                    "Por favor, tente novamente ou use /ajuda para suporte."
                )
            
        except Exception as e:
            logger.error(f"Erro no processamento de texto: {str(e)}")
            await update.message.reply_text(
                "❌ Erro ao processar texto. Por favor, tente ser mais específico:\n\n"
                "• Inclua o valor gasto (ex: 200 reais)\n"
                "• Mentione o estabelecimento (ex: na Magazine Luiza)\n"
                "• Especifique o que foi comprado (ex: um mouse sem fio)\n\n"
                "Exemplo: 'Comprei um mouse sem fio por 200 reais na Magazine Luiza'"
            )
    
    
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🎤 Processando áudio...")
        
        try:
            voice = await update.message.voice.get_file()
            audio_bytes = await voice.download_as_bytearray()
            
            # Transcrever áudio para texto
            transcribed_text = self.speech_to_text.transcribe_audio(audio_bytes)
            
            await update.message.reply_text(f"📝 Áudio transcrito: {transcribed_text}")
            
            # Processar texto transcrito
            transaction_data = self.gemini_client.analyze_financial_document(text_input=transcribed_text)
            
            # Salvar no banco de dados
            if self.db_manager.save_transaction(update.effective_chat.id, transaction_data, "voice"):
                response_message = self._format_transaction_response(transaction_data)
                await update.message.reply_text(response_message, parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Erro ao salvar transação no banco de dados.")
            
        except Exception as e:
            logger.error(f"Erro no processamento de áudio: {str(e)}")
            await update.message.reply_text("❌ Erro ao processar áudio. Tente novamente com um áudio mais claro.")
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia o processo de limpeza do banco de dados"""
        await update.message.reply_text(
            "⚠️ *ATENÇÃO: Esta ação irá limpar TODOS os dados do banco.*\n\n"
            "Tem certeza que deseja continuar? Responda 'SIM' para confirmar ou 'NÃO' para cancelar.",
            parse_mode="Markdown"
        )
        return CONFIRM_CLEAR
    
    async def confirm_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirma a limpeza do banco de dados"""
        response = update.message.text.upper()
        
        if response in ['SIM', 'YES']:
            if self.db_manager.clear_database(update.effective_chat.id):
                await update.message.reply_text("✅ Banco de dados limpo com sucesso!")
            else:
                await update.message.reply_text("❌ Erro ao limpar banco de dados.")
        else:
            await update.message.reply_text("❌ Operação de limpeza cancelada.")
        
        return ConversationHandler.END
    
    async def cancel_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancela a limpeza do banco de dados"""
        await update.message.reply_text("❌ Operação de limpeza cancelada.")
        return ConversationHandler.END
    
    def _format_transaction_response(self, transaction_data):
        """Formata a resposta da transação para o usuário"""
        response_message = (
            f"✅ *Transação registrada com sucesso!*\n\n"
            f"🏪 **Estabelecimento:** {transaction_data.get('establishment', 'Não identificado')}\n"
            f"📅 **Data:** {transaction_data.get('date', 'Não especificada')}\n"
            f"💰 **Valor Total:** R$ {transaction_data.get('total_amount', 0):.2f}\n"
            f"🏷️ **Categoria:** {transaction_data.get('category', 'Outros')}\n"
        )
        
        # Adicionar itens se existirem
        if transaction_data.get('items'):
            response_message += "\n🛍️ **Itens:**\n"
            for item in transaction_data['items']:
                response_message += f"   • {item.get('description', 'Item')}: R$ {item.get('total_price', 0):.2f}\n"
        
        return response_message
    
    async def extrato_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        transactions = self.db_manager.get_transactions(chat_id, 10)
        
        if not transactions:
            await update.message.reply_text("📝 Nenhuma transação registrada ainda.")
            return
        
        message = "📋 *Últimas Transações:*\n\n"
        for trans in transactions:
            message += (
                f"🏪 {trans[2]}\n"
                f"   📅 {trans[3]} | 💰 R$ {trans[4]:.2f}\n"
                f"   🏷️ {trans[5]} | 📝 {trans[10]}\n\n"
            )
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def resumo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        summary = self.db_manager.get_financial_summary(chat_id)
        
        if not summary or not summary['by_category']:
            await update.message.reply_text("📊 Não há dados suficientes para gerar um resumo.")
            return
        
        message = "📊 *Resumo Financeiro por Categoria:*\n\n"
        total = 0
        
        for category, amount in summary['by_category']:
            if amount:
                message += f"🏷️ {category}: R$ {amount:.2f}\n"
                total += amount
        
        message += f"\n💰 **Total Geral:** R$ {total:.2f}"
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    def start(self):
        self.application.run_polling()
