# app/routes/api_etiquetas.py
from flask import Blueprint, jsonify, request, current_app
import logging

api_bp = Blueprint('api', __name__)
logger = logging.getLogger('RFID.api')

@api_bp.route('/etiquetas', methods=['GET'])
def listar_etiquetas():
    """
    API para listar etiquetas com paginação e filtros.
    
    Query params:
        - limite: número de registros por página
        - offset: deslocamento
        - etiqueta: filtro por código da etiqueta
        - descricao: filtro por descrição
        - destruida: filtro por status (0 ou 1)
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        # Obter parâmetros
        limite = int(request.args.get('limite', 20))
        offset = int(request.args.get('offset', 0))
        
        # Filtros
        filtros = {}
        if request.args.get('etiqueta'):
            filtros['etiqueta'] = request.args.get('etiqueta')
        if request.args.get('descricao'):
            filtros['descricao'] = request.args.get('descricao')
        if request.args.get('destruida') is not None:
            filtros['destruida'] = int(request.args.get('destruida'))
        
        # Buscar etiquetas
        resultado = gerenciador.obter_etiquetas(
            filtros=filtros,
            limite=limite,
            offset=offset
        )
        
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro ao listar etiquetas: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/etiquetas/<int:id_etiqueta>', methods=['GET'])
def obter_etiqueta(id_etiqueta):
    """Obtém detalhes de uma etiqueta específica."""
    try:
        gerenciador = current_app.config.get('GERENCIADOR_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        etiqueta = gerenciador.obter_etiqueta_por_id(id_etiqueta)
        
        if etiqueta:
            return jsonify({
                'success': True,
                'etiqueta': etiqueta
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Etiqueta não encontrada'
            }), 404
    
    except Exception as e:
        logger.error(f"Erro ao obter etiqueta {id_etiqueta}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/etiquetas/<int:id_etiqueta>', methods=['PUT'])
def atualizar_etiqueta(id_etiqueta):
    """Atualiza dados de uma etiqueta."""
    try:
        gerenciador = current_app.config.get('GERENCIADOR_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        # Obter dados do corpo da requisição
        dados = request.get_json()
        
        if not dados:
            return jsonify({
                'success': False,
                'error': 'Nenhum dado fornecido'
            }), 400
        
        # Atualizar etiqueta
        resultado = gerenciador.atualizar_etiqueta(id_etiqueta, dados)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
    
    except Exception as e:
        logger.error(f"Erro ao atualizar etiqueta {id_etiqueta}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/estatisticas', methods=['GET'])
def obter_estatisticas():
    """Obtém estatísticas das etiquetas."""
    try:
        gerenciador = current_app.config.get('GERENCIADOR_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        resultado = gerenciador.obter_estatisticas()
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500