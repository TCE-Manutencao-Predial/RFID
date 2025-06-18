# app/__init__.py
from flask import Flask
from .config import setup_logging
import logging

# Configurar logging
rfid_logger = setup_logging()

ROUTES_PREFIX = '/RFID'

def create_app():
    # IMPORTANTE: Configurar static_url_path com o prefixo
    app = Flask(__name__, static_url_path=f'{ROUTES_PREFIX}/static')
    app.config['SECRET_KEY'] = '123rfid'
    
    # Inicializa gerenciador de etiquetas RFID
    try:
        from .utils.GerenciadorEtiquetasRFID import GerenciadorEtiquetasRFID
        app.config['GERENCIADOR_RFID'] = GerenciadorEtiquetasRFID.get_instance()
        rfid_logger.info("Gerenciador de etiquetas RFID iniciado")
    except Exception as e:
        rfid_logger.error(f"Erro ao inicializar gerenciador RFID: {e}")
        app.config['GERENCIADOR_RFID'] = None

    # Handlers de erro
    @app.errorhandler(404)
    def not_found_error(error):
        try:
            return render_template('erro_pagina_nao_encontrada.html')
        except:
            return "Página não encontrada", 404
    
    @app.errorhandler(500)
    def internal_error(error):
        rfid_logger.error(f"Erro interno: {error}")
        try:
            return render_template('erro_interno.html'), 500
        except:
            return "Erro interno do servidor", 500

    # Registrar blueprints com prefixo
    from .routes.web import web_bp
    from .routes.api_etiquetas import api_bp
    
    # IMPORTANTE: Registrar com url_prefix
    app.register_blueprint(web_bp, url_prefix=ROUTES_PREFIX)
    app.register_blueprint(api_bp, url_prefix=f'{ROUTES_PREFIX}/api')
    
    return app