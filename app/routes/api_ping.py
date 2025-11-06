# app/routes/api_ping.py
from flask import Blueprint, jsonify, request, current_app, Response
import logging
import traceback
from datetime import datetime, timedelta

api_ping_bp = Blueprint('api_ping', __name__)
logger = logging.getLogger('RFID.api_ping')

@api_ping_bp.route('/ping', methods=['GET'])
def listar_pings():
    """
    API para listar registros PING RFID com paginação e filtros.
    
    Query params:
        - limite: número de registros por página (padrão: 50)
        - offset: deslocamento
        - local: filtro por local (B1, B2, S1)
        - antena: filtro por antena
        - horario_inicio: filtro por data/hora inicial (formato: YYYY-MM-DD HH:MM:SS)
        - horario_fim: filtro por data/hora final (formato: YYYY-MM-DD HH:MM:SS)
        - force_refresh: força atualização do cache
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_PING')
        if not gerenciador:
            # Tentar criar o gerenciador se não existir
            from ..utils.GerenciadorPingRFID import GerenciadorPingRFID
            gerenciador = GerenciadorPingRFID.get_instance()
            current_app.config['GERENCIADOR_PING'] = gerenciador
        
        # Obter parâmetros com validação
        try:
            limite = int(request.args.get('limite', 50))
            offset = int(request.args.get('offset', 0))
            
            # Limitar para evitar sobrecarga
            if limite > 200:
                limite = 200
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Parâmetros de paginação inválidos'
            }), 400
        
        # Filtros
        filtros = {}
        if request.args.get('local'):
            filtros['local'] = request.args.get('local').strip()

        if request.args.get('antena'):
            filtros['antena'] = request.args.get('antena').strip()
        
        if request.args.get('horario_inicio'):
            try:
                # Validar formato de data
                datetime.strptime(request.args.get('horario_inicio'), '%Y-%m-%d %H:%M:%S')
                filtros['horario_inicio'] = request.args.get('horario_inicio')
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Formato de data inválido. Use: YYYY-MM-DD HH:MM:SS'
                }), 400
        
        if request.args.get('horario_fim'):
            try:
                datetime.strptime(request.args.get('horario_fim'), '%Y-%m-%d %H:%M:%S')
                filtros['horario_fim'] = request.args.get('horario_fim')
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Formato de data inválido. Use: YYYY-MM-DD HH:MM:SS'
                }), 400
        
        # Verificar se é uma atualização forçada
        force_refresh = request.args.get('force_refresh', '').lower() == 'true'
        
        logger.info(f"Buscando PINGs com filtros: {filtros}, limite: {limite}, offset: {offset}")
        
        # Buscar PINGs
        resultado = gerenciador.obter_pings(
            filtros=filtros,
            limite=limite,
            offset=offset,
            force_refresh=force_refresh
        )
        
        if not resultado.get('success', False):
            logger.error(f"Erro ao obter PINGs: {resultado.get('error')}")
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro ao buscar PINGs')
            }), 500
        
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro não tratado ao listar PINGs: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@api_ping_bp.route('/ping/estatisticas', methods=['GET'])
def obter_estatisticas_pings():
    """
    Obtém estatísticas gerais dos registros PING.
    
    Query params:
        - horario_inicio: filtro por data/hora inicial
        - horario_fim: filtro por data/hora final
        - force_refresh: força atualização do cache
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_PING')
        if not gerenciador:
            from ..utils.GerenciadorPingRFID import GerenciadorPingRFID
            gerenciador = GerenciadorPingRFID.get_instance()
            current_app.config['GERENCIADOR_PING'] = gerenciador
        
        # Filtros opcionais
        filtros = {}
        
        if request.args.get('horario_inicio'):
            try:
                datetime.strptime(request.args.get('horario_inicio'), '%Y-%m-%d %H:%M:%S')
                filtros['horario_inicio'] = request.args.get('horario_inicio')
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Formato de data inválido. Use: YYYY-MM-DD HH:MM:SS'
                }), 400
        
        if request.args.get('horario_fim'):
            try:
                datetime.strptime(request.args.get('horario_fim'), '%Y-%m-%d %H:%M:%S')
                filtros['horario_fim'] = request.args.get('horario_fim')
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Formato de data inválido. Use: YYYY-MM-DD HH:MM:SS'
                }), 400
        
        force_refresh = request.args.get('force_refresh', '').lower() == 'true'
        
        resultado = gerenciador.obter_estatisticas_pings(
            filtros=filtros,
            force_refresh=force_refresh
        )
        
        if not resultado.get('success', False):
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro ao obter estatísticas')
            }), 500
        
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas PING: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_ping_bp.route('/ping/locais', methods=['GET'])
def listar_locais():
    """
    Lista todos os locais e antenas que registraram PINGs.
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_PING')
        if not gerenciador:
            from ..utils.GerenciadorPingRFID import GerenciadorPingRFID
            gerenciador = GerenciadorPingRFID.get_instance()
            current_app.config['GERENCIADOR_PING'] = gerenciador
        
        force_refresh = request.args.get('force_refresh', '').lower() == 'true'
        
        resultado = gerenciador.obter_locais_com_antena(force_refresh=force_refresh)
        
        if not resultado.get('success', False):
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro ao listar locais')
            }), 500
        
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro ao listar locais PING: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_ping_bp.route('/ping/foto', methods=['GET'])
def obter_foto_ping_query():
    """
    Obtém a foto de um PING específico através de query params.
    
    Query params:
        - local: local do ping (B1, B2, S1) - obrigatório
        - antena: número da antena - obrigatório
        - horario: horário do PING - obrigatório
        
    Returns:
        - Imagem binária ou JSON com erro
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_PING')
        if not gerenciador:
            from ..utils.GerenciadorPingRFID import GerenciadorPingRFID
            gerenciador = GerenciadorPingRFID.get_instance()
            current_app.config['GERENCIADOR_PING'] = gerenciador
        
        # Obter parâmetros obrigatórios
        local = request.args.get('local')
        antena = request.args.get('antena')
        horario = request.args.get('horario')
        
        # Chamar gerenciador
        resultado = gerenciador.obter_foto_ping(
            local=local,
            antena=antena,
            horario=horario
        )
        
        if not resultado.get('success', False):
            error_type = resultado.get('error_type', 'exception')
            status_code = 404 if error_type in ['not_found', 'no_photo'] else 500
            
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro ao obter foto do PING'),
                'error_type': error_type
            }), status_code
        
        # Se não encontrou foto
        if not resultado.get('foto'):
            return jsonify({
                'success': False,
                'error': 'Nenhuma foto encontrada para este PING',
                'error_type': 'not_found'
            }), 404
        
        # Retornar a imagem
        foto_data = resultado['foto']
        
        # Detectar tipo de imagem baseado nos primeiros bytes
        content_type = 'image/jpeg'  # padrão
        if foto_data.startswith(b'\x89PNG'):
            content_type = 'image/png'
        elif foto_data.startswith(b'GIF'):
            content_type = 'image/gif'
        elif foto_data.startswith(b'\xff\xd8'):
            content_type = 'image/jpeg'
        
        return Response(
            foto_data,
            mimetype=content_type,
            headers={
                'Content-Disposition': f'inline; filename="ping_{local}_{antena}.jpg"',
                'Cache-Control': 'public, max-age=3600'  # Cache por 1 hora
            }
        )
    
    except Exception as e:
        logger.error(f"Erro ao obter foto do PING: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'exception'
        }), 500

@api_ping_bp.route('/ping/foto/info', methods=['GET'])
def verificar_foto_ping_query():
    """
    Verifica se um PING possui foto disponível através de query params.
    
    Query params:
        - local: local do ping - obrigatório
        - antena: número da antena - obrigatório
        - horario: horário do PING - obrigatório
        
    Returns:
        - JSON com informações sobre disponibilidade da foto
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_PING')
        if not gerenciador:
            from ..utils.GerenciadorPingRFID import GerenciadorPingRFID
            gerenciador = GerenciadorPingRFID.get_instance()
            current_app.config['GERENCIADOR_PING'] = gerenciador
        
        # Obter parâmetros obrigatórios
        local = request.args.get('local')
        antena = request.args.get('antena')
        horario = request.args.get('horario')
        
        resultado = gerenciador.verificar_foto_ping(
            local=local,
            antena=antena,
            horario=horario
        )
        
        if not resultado.get('success', False):
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro ao verificar foto do PING')
            }), 500
        
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro ao verificar foto do PING: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
# Rota de teste/debug
@api_ping_bp.route('/ping/test', methods=['GET'])
def test_api_ping():
    """Rota de teste para verificar se a API de PING está funcionando."""
    try:
        gerenciador = current_app.config.get('GERENCIADOR_PING')
        return jsonify({
            'success': True,
            'message': 'API de PING funcionando',
            'gerenciador_status': 'OK' if gerenciador else 'Não inicializado',
            'endpoints': [
                '/ping',
                '/ping/estatisticas',
                '/ping/locais',
                '/ping/foto',
                '/ping/foto/info'
            ]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
