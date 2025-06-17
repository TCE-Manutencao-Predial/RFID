# app/__init__.py
from flask import Flask, redirect, render_template, url_for, current_app
from .routes.web import web_bp
from .routes.api_etiquetas import api_bp
from .config import ROUTES_PREFIX, setup_logging
import atexit
import logging

# Configurar logging
rfid_logger = setup_logging()

def create_app():
    app = Flask(__name__)
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

    # Registrar blueprints sem prefixo
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route('/')
    def index():
        """Página inicial - mostra controle de etiquetas diretamente."""
        try:
            gerenciador = app.config.get('GERENCIADOR_RFID')
            if not gerenciador:
                rfid_logger.error("Gerenciador RFID não inicializado")
                return render_template('erro_interno.html'), 500
            
            # Obter estatísticas
            stats_result = gerenciador.obter_estatisticas()
            estatisticas = stats_result.get('estatisticas', {})
            
            return render_template('controle_etiquetas.html', estatisticas=estatisticas)
        
        except Exception as e:
            rfid_logger.error(f"Erro ao carregar página de etiquetas: {e}")
            return render_template('erro_interno.html'), 500

    return app