# app/routes/web.py
from flask import Blueprint, render_template, current_app
import logging

web_bp = Blueprint('web', __name__)
logger = logging.getLogger('controlerfid.web')

@web_bp.route('/')
@web_bp.route('/index')
@web_bp.route('/index.html')
@web_bp.route('/etiquetas')
def controle_etiquetas():
    """Página principal de controle de etiquetas RFID."""
    try:
        gerenciador = current_app.config.get('GERENCIADOR_RFID')
        if not gerenciador:
            logger.error("Gerenciador RFID não inicializado")
            return render_template('erro_interno.html'), 500
        
        # Obter estatísticas
        stats_result = gerenciador.obter_estatisticas()
        estatisticas = stats_result.get('estatisticas', {})
        
        return render_template('controle_etiquetas.html', estatisticas=estatisticas)
    
    except Exception as e:
        logger.error(f"Erro ao carregar página de etiquetas: {e}")
        return render_template('erro_interno.html'), 500

@web_bp.route('/inventarios')
@web_bp.route('/inventarios.html')
def inventarios():
    """Página de gerenciamento de inventários RFID."""
    try:
        gerenciador = current_app.config.get('GERENCIADOR_RFID')
        if not gerenciador:
            logger.error("Gerenciador RFID não inicializado")
            return render_template('erro_interno.html'), 500
        
        # Futuramente: obter dados específicos de inventários
        # Por enquanto, renderiza a página básica
        return render_template('inventarios.html')
    
    except Exception as e:
        logger.error(f"Erro ao carregar página de inventários: {e}")
        return render_template('erro_interno.html'), 500

@web_bp.route('/antenas')
@web_bp.route('/antenas.html')
def antenas():
    """Página de gerenciamento de antenas RFID."""
    try:
        gerenciador = current_app.config.get('GERENCIADOR_RFID')
        if not gerenciador:
            logger.error("Gerenciador RFID não inicializado")
            return render_template('erro_interno.html'), 500
        
        # Futuramente: obter dados específicos de antenas
        # Por enquanto, renderiza a página básica
        return render_template('antenas.html')
    
    except Exception as e:
        logger.error(f"Erro ao carregar página de antenas: {e}")
        return render_template('erro_interno.html'), 500

@web_bp.route('/emprestimos')
@web_bp.route('/emprestimos.html')
def emprestimos():
    """Página de gerenciamento de empréstimos de ferramentas."""
    try:
        gerenciador = current_app.config.get('GERENCIADOR_RFID')
        if not gerenciador:
            logger.error("Gerenciador RFID não inicializado")
            return render_template('erro_interno.html'), 500
        
        # Futuramente: obter dados específicos de empréstimos
        # Por enquanto, renderiza a página básica
        return render_template('emprestimos.html')
    
    except Exception as e:
        logger.error(f"Erro ao carregar página de empréstimos: {e}")
        return render_template('erro_interno.html'), 500