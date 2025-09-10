import sqlite3
import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path=None):
        # Em ambientes serverless (Vercel) use /tmp para escrita
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = os.getenv('DATABASE_PATH', '/tmp/financial_data.db')

        # Tentar criar diretório se necessário
        dirpath = os.path.dirname(self.db_path)
        if dirpath and not os.path.exists(dirpath):
            try:
                os.makedirs(dirpath, exist_ok=True)
            except Exception:
                pass

        self.init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def init_db(self):
        """Inicializa o banco de dados com tabelas necessárias"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                establishment_name TEXT,
                transaction_date DATE,
                total_amount REAL,
                category TEXT,
                items_json TEXT,
                raw_text TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'processed',
                input_method TEXT DEFAULT 'image'
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transaction_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER,
                description TEXT,
                quantity REAL,
                unit_price REAL,
                total_price REAL,
                category TEXT,
                FOREIGN KEY (transaction_id) REFERENCES transactions (id)
            )
        ''')

        # Verificar se a coluna input_method existe, se não, adicionar
        try:
            cursor.execute("PRAGMA table_info(transactions)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'input_method' not in columns:
                cursor.execute('ALTER TABLE transactions ADD COLUMN input_method TEXT DEFAULT "image"')
                logger.info("Coluna input_method adicionada à tabela transactions")
        except Exception as e:
            logger.error(f"Erro ao verificar/adicionar coluna: {str(e)}")

        conn.commit()
        conn.close()

    def save_transaction(self, chat_id, transaction_data, input_method="image"):
        """
        Salva uma transação processada no banco de dados
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO transactions 
                (chat_id, establishment_name, transaction_date, total_amount, category, items_json, raw_text, input_method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(chat_id),
                transaction_data.get('establishment'),
                transaction_data.get('date'),
                transaction_data.get('total_amount'),
                transaction_data.get('category'),
                json.dumps(transaction_data.get('items', [])),
                transaction_data.get('raw_text', ''),
                input_method
            ))

            transaction_id = cursor.lastrowid

            if 'items' in transaction_data:
                for item in transaction_data['items']:
                    cursor.execute('''
                        INSERT INTO transaction_items 
                        (transaction_id, description, quantity, unit_price, total_price, category)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        transaction_id,
                        item.get('description'),
                        item.get('quantity', 1),
                        item.get('unit_price'),
                        item.get('total_price'),
                        item.get('category')
                    ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Erro ao salvar transação no banco: {str(e)}")
            return False

    def get_transactions(self, chat_id, limit=10):
        """Recupera transações de um chat específico"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM transactions 
                WHERE chat_id = ? 
                ORDER BY processed_at DESC 
                LIMIT ?
            ''', (str(chat_id), limit))

            transactions = cursor.fetchall()
            conn.close()
            return transactions

        except Exception as e:
            logger.error(f"Erro ao buscar transações: {str(e)}")
            return []

    def get_financial_summary(self, chat_id):
        """Retorna um resumo financeiro para um chat"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT category, SUM(total_amount) as total
                FROM transactions 
                WHERE chat_id = ? 
                GROUP BY category
            ''', (str(chat_id),))

            by_category = cursor.fetchall()

            cursor.execute('''
                SELECT strftime('%Y-%m', transaction_date) as month, 
                       SUM(total_amount) as total
                FROM transactions 
                WHERE chat_id = ? 
                GROUP BY month
                ORDER BY month DESC
            ''', (str(chat_id),))

            by_month = cursor.fetchall()

            conn.close()

            return {
                'by_category': by_category,
                'by_month': by_month
            }

        except Exception as e:
            logger.error(f"Erro ao gerar resumo financeiro: {str(e)}")
            return None

    def clear_database(self, chat_id=None):
        """
        Limpa o banco de dados - se chat_id for fornecido, limpa apenas para esse chat
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            if chat_id:
                cursor.execute('''
                    DELETE FROM transaction_items 
                    WHERE transaction_id IN (
                        SELECT id FROM transactions WHERE chat_id = ?
                    )
                ''', (str(chat_id),))

                cursor.execute('DELETE FROM transactions WHERE chat_id = ?', (str(chat_id),))

                logger.info(f"Dados do chat {chat_id} removidos do banco de dados")
            else:
                cursor.execute('DELETE FROM transaction_items')
                cursor.execute('DELETE FROM transactions')
                cursor.execute('VACUUM')  # Otimizar o banco após exclusão
                logger.info("Todo o banco de dados foi limpo")

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Erro ao limpar banco de dados: {str(e)}")
            return False
