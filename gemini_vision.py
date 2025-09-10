import base64
import requests
import logging
import json
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class GeminiAIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.vision_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        self.text_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    
    def analyze_financial_document(self, image_bytes=None, text_input=None):
        """
        Analisa documentos financeiros (imagem ou texto) e extrai informações estruturadas
        """
        if image_bytes:
            return self._analyze_image_document(image_bytes)
        elif text_input:
            return self._analyze_text_document(text_input)
        else:
            raise Exception("Nenhum dado fornecido para análise")
    
    def _analyze_text_document(self, text_input):
        """Analisa texto de transação financeira com prompt mais específico"""
        financial_prompt = f"""
        Você é um especialista em análise de transações financeiras. Analise o texto abaixo e extraia as seguintes informações em formato JSON STRICT:

        {{
          "establishment": "Nome do estabelecimento ou loja",
          "date": "YYYY-MM-DD (use a data de hoje se não for especificada)",
          "total_amount": 0.00,
          "category": "Tecnologia/Eletrônico/Informática/Alimentação/Transporte/Moradia/Saúde/Lazer/Educação/Mercado/Serviços/Outros",
          "items": [
            {{
              "description": "Descrição detalhada do item",
              "quantity": 1,
              "unit_price": 0.00,
              "total_price": 0.00,
              "category": "Categoria específica do item"
            }}
          ],
          "raw_text": "Texto original para referência"
        }}

        REGRAS ESTRITAS:
        1. SEMPRE retorne um JSON válido
        2. Para valores monetários, converta para números com duas casas decimais
        3. Categorize inteligentemente baseado no contexto
        4. Extraia o máximo de informações possível
        5. Se não encontrar informações, use "Não especificado" para textos e 0.00 para valores

        Exemplo de entrada: "comprei um mouse sem fio Mouse Sem Fio Logitech Signature M650 L Left - Grafite por 200,00 reais"
        Exemplo de saída: 
        {{
          "establishment": "Loja de Informática",
          "date": "2025-09-08",
          "total_amount": 200.00,
          "category": "Tecnologia",
          "items": [
            {{
              "description": "Mouse Sem Fio Logitech Signature M650 L Left - Grafite",
              "quantity": 1,
              "unit_price": 200.00,
              "total_price": 200.00,
              "category": "Periféricos"
            }}
          ],
          "raw_text": "comprei um mouse sem fio Mouse Sem Fio Logitech Signature M650 L Left - Grafite por 200,00 reais"
        }}

        TEXTO PARA ANÁLISE: {text_input}

        Retorne APENAS o JSON válido, sem markdown ou texto adicional.
        """
        
        request_body = {
            "contents": [{
                "parts": [{"text": financial_prompt}]
            }]
        }

        return self._make_gemini_request(request_body)
    
    def _make_gemini_request(self, request_body):
        """Faz requisição para a API Gemini"""
        try:
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
            
            url = self.vision_url if any('inline_data' in part for part in request_body['contents'][0]['parts']) else self.text_url
            
            response = requests.post(
                url,
                headers=headers,
                json=request_body,
                timeout=45
            )
            
            logger.debug(f"Status da API Gemini: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Erro na API Gemini: {response.text}")
                raise Exception(f"Erro na API: {response.status_code}")
            
            response_data = response.json()
            extracted_text = self._extract_text_from_response(response_data)
            
            # Extrair JSON da resposta
            json_match = re.search(r'\{.*\}', extracted_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    logger.error("JSON inválido retornado pela IA")
                    return self._fallback_financial_processing(extracted_text)
            else:
                logger.error("Nenhum JSON encontrado na resposta")
                return self._fallback_financial_processing(extracted_text)
                
        except Exception as e:
            logger.error(f"Erro na análise do documento: {str(e)}")
            raise Exception(f"Falha na análise: {str(e)}")
    
    def _extract_text_from_response(self, response):
        """Extrai texto da resposta da API Gemini"""
        try:
            return response["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            logger.error("Estrutura de resposta inesperada")
            raise Exception("Resposta da API em formato inesperado")
    
    def _fallback_financial_processing(self, text):
        """
        Processamento de fallback para quando o JSON não é retornado corretamente
        """
        # Extrair informações básicas usando regex
        date_match = re.search(r'(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})', text)
        total_match = re.search(r'R\$\s*(\d+[\.,]?\d*)|\b(\d+[\.,]?\d*)\s*reais\b', text)
        
        # Determinar categoria baseada no texto
        category = "Outros"
        category_keywords = {
            'Mercado': ['mercado', 'supermercado', 'compras', 'hipermercado'],
            'Alimentação': ['restaurante', 'lanche', 'pizza', 'hambúrguer', 'comida', 'almoço', 'jantar'],
            'Transporte': ['combustível', 'gasolina', 'posto', 'ônibus', 'metro', 'táxi', 'uber'],
            'Moradia': ['aluguel', 'condomínio', 'conta de luz', 'água', 'internet', 'energia'],
            'Saúde': ['farmácia', 'remédio', 'médico', 'hospital', 'consulta'],
            'Lazer': ['cinema', 'shopping', 'parque', 'viagem', 'hotel'],
            'Educação': ['livro', 'curso', 'faculdade', 'escola', 'material']
        }
        
        for cat, keywords in category_keywords.items():
            if any(keyword in text.lower() for keyword in keywords):
                category = cat
                break
        
        return {
            "establishment": "Estabelecimento não identificado",
            "date": date_match.group(1) if date_match else datetime.now().strftime('%Y-%m-%d'),
            "total_amount": float(total_match.group(1).replace(',', '.')) if total_match and total_match.group(1) else 0.0,
            "category": category,
            "items": [],
            "raw_text": text[:1000]  # Limitar texto para evitar problemas no banco
        }
