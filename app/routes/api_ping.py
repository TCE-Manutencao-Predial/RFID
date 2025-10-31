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
        - etiqueta: filtro por código da etiqueta
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
        if request.args.get('etiqueta'):
            filtros['etiqueta'] = request.args.get('etiqueta').strip()

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

@api_ping_bp.route('/ping/etiqueta/<etiqueta_hex>', methods=['GET'])
def obter_historico_ping(etiqueta_hex):
    """
    Obtém histórico de registros PING de uma etiqueta específica.
    
    Params:
        - etiqueta_hex: código hexadecimal da etiqueta PING
    
    Query params:
        - limite: número máximo de registros (padrão: 50, máx: 200)
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_PING')
        if not gerenciador:
            from ..utils.GerenciadorPingRFID import GerenciadorPingRFID
            gerenciador = GerenciadorPingRFID.get_instance()
            current_app.config['GERENCIADOR_PING'] = gerenciador
        
        try:
            limite = int(request.args.get('limite', 50))
            if limite > 200:
                limite = 200
        except ValueError:
            limite = 50
        
        logger.info(f"Obtendo histórico do PING: {etiqueta_hex}")
        
        resultado = gerenciador.obter_pings_por_etiqueta(etiqueta_hex, limite)
        
        if not resultado.get('success', False):
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro ao obter histórico')
            }), 500
        
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro ao obter histórico do PING: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_ping_bp.route('/ping/ultimos/<int:minutos>', methods=['GET'])
def obter_pings_recentes(minutos):
    """
    Obtém registros PING dos últimos X minutos.
    
    Params:
        - minutos: número de minutos (máx: 1440 = 24 horas)
    """
    try:
        # Limitar a 24 horas
        if minutos > 1440:
            minutos = 1440
        
        gerenciador = current_app.config.get('GERENCIADOR_PING')
        if not gerenciador:
            from ..utils.GerenciadorPingRFID import GerenciadorPingRFID
            gerenciador = GerenciadorPingRFID.get_instance()
            current_app.config['GERENCIADOR_PING'] = gerenciador
        
        # Calcular período
        agora = datetime.now()
        inicio = agora - timedelta(minutes=minutos)
        
        filtros = {
            'horario_inicio': inicio.strftime('%Y-%m-%d %H:%M:%S'),
            'horario_fim': agora.strftime('%Y-%m-%d %H:%M:%S')
        }

        # Reaplicar filtros opcionais
        for chave in ('etiqueta', 'antena'):
            val = request.args.get(chave)
            if val:
                filtros[chave] = val.strip()

        # Obter parâmetros de paginação
        try:
            limite = int(request.args.get('limite', 100))
            offset = int(request.args.get('offset', 0))
            if limite > 200:
                limite = 200
        except ValueError:
            limite = 100
            offset = 0
        
        logger.info(f"Obtendo PINGs dos últimos {minutos} minutos")
        
        resultado = gerenciador.obter_pings(
            filtros=filtros,
            limite=limite,
            offset=offset,
            force_refresh=True  # Sempre atualizar para dados recentes
        )
        
        if not resultado.get('success', False):
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro ao obter PINGs recentes')
            }), 500
        
        # Adicionar informação do período
        resultado['periodo'] = {
            'minutos': minutos,
            'inicio': inicio.strftime('%Y-%m-%d %H:%M:%S'),
            'fim': agora.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro ao obter PINGs recentes: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_ping_bp.route('/ping/antenas', methods=['GET'])
def listar_antenas():
    """
    Lista todas as antenas que registraram PINGs, agrupadas por leitor.
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_PING')
        if not gerenciador:
            from ..utils.GerenciadorPingRFID import GerenciadorPingRFID
            gerenciador = GerenciadorPingRFID.get_instance()
            current_app.config['GERENCIADOR_PING'] = gerenciador
        
        force_refresh = request.args.get('force_refresh', '').lower() == 'true'
        
        resultado = gerenciador.obter_antenas_com_leitor(force_refresh=force_refresh)
        
        if not resultado.get('success', False):
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro ao listar antenas')
            }), 500
        
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro ao listar antenas PING: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_ping_bp.route('/ping/foto/<string:etiqueta_hex>', methods=['GET'])
def obter_foto_ping(etiqueta_hex):
    """
    Obtém a foto mais recente de um PING específico.
    
    Params:
        - etiqueta_hex: código hexadecimal da etiqueta PING
        
    Returns:
        - Imagem binária ou JSON com erro
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_PING')
        if not gerenciador:
            from ..utils.GerenciadorPingRFID import GerenciadorPingRFID
            gerenciador = GerenciadorPingRFID.get_instance()
            current_app.config['GERENCIADOR_PING'] = gerenciador
        
        logger.info(f"Buscando foto para PING: {etiqueta_hex}")
        
        resultado = gerenciador.obter_foto_ping(etiqueta_hex)
        
        if not resultado.get('success', False):
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro ao obter foto do PING')
            }), 404
        
        # Se não encontrou foto
        if not resultado.get('foto'):
            return jsonify({
                'success': False,
                'error': 'Nenhuma foto encontrada para este PING'
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
                'Content-Disposition': f'inline; filename="ping_{etiqueta_hex}.jpg"',
                'Cache-Control': 'public, max-age=3600'  # Cache por 1 hora
            }
        )
    
    except Exception as e:
        logger.error(f"Erro ao obter foto do PING {etiqueta_hex}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_ping_bp.route('/ping/foto/info/<string:etiqueta_hex>', methods=['GET'])
def verificar_foto_ping(etiqueta_hex):
    """
    Verifica se um PING possui foto disponível.
    
    Params:
        - etiqueta_hex: código hexadecimal da etiqueta PING
        
    Returns:
        - JSON com informações sobre disponibilidade da foto
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_PING')
        if not gerenciador:
            from ..utils.GerenciadorPingRFID import GerenciadorPingRFID
            gerenciador = GerenciadorPingRFID.get_instance()
            current_app.config['GERENCIADOR_PING'] = gerenciador
        
        resultado = gerenciador.verificar_foto_ping(etiqueta_hex)
        
        if not resultado.get('success', False):
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro ao verificar foto do PING')
            }), 500
        
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro ao verificar foto do PING {etiqueta_hex}: {str(e)}")
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
                '/ping/etiqueta/{hex}',
                '/ping/ultimos/{minutos}',
                '/ping/antenas',
                '/ping/foto/{hex}',
                '/ping/foto/info/{hex}'
            ]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
