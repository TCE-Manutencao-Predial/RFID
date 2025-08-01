# app/__init__.py
from flask import Flask, render_template
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
    
    # Inicializa gerenciador de leitores RFID
    try:
        from .utils.GerenciadorLeitoresRFID import GerenciadorLeitoresRFID
        app.config['GERENCIADOR_LEITORES'] = GerenciadorLeitoresRFID.get_instance()
        rfid_logger.info("Gerenciador de leitores RFID iniciado")
    except Exception as e:
        rfid_logger.error(f"Erro ao inicializar gerenciador de leitores: {e}")
        app.config['GERENCIADOR_LEITORES'] = None
    
    # Inicializa gerenciador de empréstimos RFID
    try:
        from .utils.GerenciadorEmprestimosRFID import GerenciadorEmprestimosRFID
        app.config['GERENCIADOR_EMPRESTIMOS_RFID'] = GerenciadorEmprestimosRFID.get_instance()
        rfid_logger.info("Gerenciador de empréstimos RFID iniciado")
    except Exception as e:
        rfid_logger.error(f"Erro ao inicializar gerenciador de empréstimos: {e}")
        app.config['GERENCIADOR_EMPRESTIMOS_RFID'] = None
    
    # Inicializa gerenciador de inventários RFID
    try:
        from .utils.GerenciadorInventariosRFID import GerenciadorInventariosRFID
        app.config['GERENCIADOR_INVENTARIOS_RFID'] = GerenciadorInventariosRFID.get_instance()
        rfid_logger.info("Gerenciador de inventários RFID iniciado")
    except Exception as e:
        rfid_logger.error(f"Erro ao inicializar gerenciador de inventários: {e}")
        app.config['GERENCIADOR_INVENTARIOS_RFID'] = None

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
    from .routes.api_leitores import api_leitores_bp
    from .routes.api_emprestimos import api_emprestimos_bp
    from .routes.api_inventarios import api_inventarios_bp
    
    # IMPORTANTE: Registrar com url_prefix
    app.register_blueprint(web_bp, url_prefix=ROUTES_PREFIX)
    app.register_blueprint(api_bp, url_prefix=f'{ROUTES_PREFIX}/api')
    app.register_blueprint(api_leitores_bp, url_prefix=f'{ROUTES_PREFIX}/api')
    app.register_blueprint(api_emprestimos_bp, url_prefix=f'{ROUTES_PREFIX}/api')
    app.register_blueprint(api_inventarios_bp, url_prefix=f'{ROUTES_PREFIX}/api')
    
    # Log de rotas registradas para debug
    rfid_logger.info("Rotas registradas:")
    for rule in app.url_map.iter_rules():
        rfid_logger.info(f"  {rule.endpoint}: {rule.rule}")
    
    return app