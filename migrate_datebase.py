#!/usr/bin/env python3
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Migra o banco de dados existente para adicionar a coluna input_method"""
    try:
        conn = sqlite3.connect('financial_data.db')
        cursor = conn.cursor()
        
        # Verificar se a coluna input_method já existe
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'input_method' not in columns:
            logger.info("Adicionando coluna input_method à tabela transactions...")
            cursor.execute('ALTER TABLE transactions ADD COLUMN input_method TEXT DEFAULT "image"')
            conn.commit()
            logger.info("Coluna input_method adicionada com sucesso!")
        else:
            logger.info("Coluna input_method já existe na tabela transactions")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Erro na migração do banco de dados: {str(e)}")

if __name__ == "__main__":
    migrate_database()
