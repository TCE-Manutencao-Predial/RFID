# app/routes/web.py
from flask import Blueprint, render_template, current_app
import logging

web_bp = Blueprint('web', __name__)
logger = logging.getLogger('controlerfid.web')

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