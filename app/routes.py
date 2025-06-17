from flask import jsonify, request
from app import app
import logging
from app.utilidades import enviar_email

# Obtenha o logger já configurado
logger = logging.getLogger('RFID')

RAIZ = '/RFID'


""" WEB PAGE 
------------------------------------------""" 

@app.route('/')    # Rota para testes locais
@app.route(RAIZ + '/')
@app.route(RAIZ + '/index')
def index():
    return "Hello from RFID"


""" API
------------------------------------------""" 

@app.route(RAIZ + '/api/hello')
def hello():
    return "Hello from RFID"


@app.route(RAIZ + '/api/enviaremail', methods=['POST'])
def api_enviar_email():
    try:
        # Acessa os dados do formulário (se foi enviado como form-data)
        conteudo_html = request.form.get('conteudo')
    
        enviar_email("Enviando email a partir do Flask", conteudo_html,"phmotaemiliano@gmail.com")
    except:
        logger.error(f"Erro ao enviar email.")
        return "Falha" # Acho que vou retornar apenas um OK para não revelar o que isso está fazendo por enquanto.
    finally:
        logger.error(f"Email enviado via Flask.")
        return "OK" # Acho que vou retornar apenas um OK para não revelar o que isso está fazendo por enquanto.
 