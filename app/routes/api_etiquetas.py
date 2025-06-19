# app/routes/api_etiquetas.py
from flask import Blueprint, jsonify, request, current_app
import logging
import traceback
from datetime import datetime

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
        - destruida: filtro por status (0=ativas, 1=destruídas)
    """
    try:
        logger.info("Iniciando listagem de etiquetas")
        
        gerenciador = current_app.config.get('GERENCIADOR_RFID')
        if not gerenciador:
            logger.error("Gerenciador RFID não encontrado no config")
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        # Obter parâmetros com validação
        try:
            limite = int(request.args.get('limite', 20))
            offset = int(request.args.get('offset', 0))
        except ValueError as e:
            logger.error(f"Parâmetros inválidos: {e}")
            return jsonify({
                'success': False,
                'error': 'Parâmetros de paginação inválidos'
            }), 400
        
        # Filtros
        filtros = {}
        if request.args.get('etiqueta'):
            filtros['etiqueta'] = request.args.get('etiqueta')
        if request.args.get('descricao'):
            filtros['descricao'] = request.args.get('descricao')

        if request.args.get('destruida') is not None:
            try:
                filtros['destruida'] = int(request.args.get('destruida'))
            except ValueError:
                logger.error(f"Valor inválido para destruida: {request.args.get('destruida')}")        
                
        # Verificar se é uma atualização forçada
        force_refresh = request.args.get('force_refresh', '').lower() == 'true'
        
        logger.info(f"Buscando etiquetas com filtros: {filtros}, limite: {limite}, offset: {offset}, force_refresh: {force_refresh}")
        
        # Buscar etiquetas
        resultado = gerenciador.obter_etiquetas(
            filtros=filtros,
            limite=limite,
            offset=offset,
            force_refresh=force_refresh
        )
        
        if not resultado.get('success', False):
            logger.error(f"Erro ao obter etiquetas: {resultado.get('error', 'Erro desconhecido')}")
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro ao buscar etiquetas')
            }), 500
        
        # Processar dados das etiquetas para incluir status formatado
        etiquetas_processadas = []
        for etiqueta in resultado.get('etiquetas', []):
            etiqueta_processada = etiqueta.copy()
            
            # Adicionar campos de status baseado na data de destruição
            if etiqueta.get('Destruida') is not None:
                etiqueta_processada['status'] = 'destruida'
                etiqueta_processada['ativa'] = False
                # Formatar data de destruição para exibição
                try:
                    # Se for um objeto datetime
                    if hasattr(etiqueta['Destruida'], 'strftime'):
                        etiqueta_processada['data_destruicao_formatada'] = etiqueta['Destruida'].strftime('%d/%m/%Y às %H:%M')
                    # Se for uma string
                    elif isinstance(etiqueta['Destruida'], str):
                        # Tentar vários formatos de data
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%a, %d %b %Y %H:%M:%S GMT']:
                            try:
                                data_destruicao = datetime.strptime(etiqueta['Destruida'], fmt)
                                etiqueta_processada['data_destruicao_formatada'] = data_destruicao.strftime('%d/%m/%Y às %H:%M')
                                break
                            except ValueError:
                                continue
                        else:
                            # Se nenhum formato funcionou, usar a string original
                            etiqueta_processada['data_destruicao_formatada'] = str(etiqueta['Destruida'])
                    else:
                        etiqueta_processada['data_destruicao_formatada'] = str(etiqueta['Destruida'])
                except Exception as e:
                    logger.error(f"Erro ao formatar data: {e}")
                    etiqueta_processada['data_destruicao_formatada'] = str(etiqueta['Destruida'])
            else:
                etiqueta_processada['status'] = 'ativa'
                etiqueta_processada['ativa'] = True
                etiqueta_processada['data_destruicao_formatada'] = None
            
            etiquetas_processadas.append(etiqueta_processada)
        
        # Atualizar resultado com etiquetas processadas
        resultado['etiquetas'] = etiquetas_processadas
        
        logger.info(f"Etiquetas obtidas com sucesso. Total: {resultado.get('total', 0)}")
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro não tratado ao listar etiquetas: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@api_bp.route('/etiquetas/<int:id_etiqueta>', methods=['GET'])
def obter_etiqueta(id_etiqueta):
    """Obtém detalhes de uma etiqueta específica."""
    try:
        logger.info(f"Obtendo etiqueta ID: {id_etiqueta}")
        
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
        logger.error(f"Erro ao obter etiqueta {id_etiqueta}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
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
        logger.error(f"Erro ao atualizar etiqueta {id_etiqueta}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/estatisticas', methods=['GET'])
def obter_estatisticas():
    """Obtém estatísticas das etiquetas."""
    try:
        logger.info("Obtendo estatísticas")
        
        gerenciador = current_app.config.get('GERENCIADOR_RFID')
        if not gerenciador:
            logger.error("Gerenciador RFID não encontrado")
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        # Verificar se é uma atualização forçada
        force_refresh = request.args.get('force_refresh', '').lower() == 'true'
        
        resultado = gerenciador.obter_estatisticas(force_refresh=force_refresh)
        
        if not resultado.get('success', False):
            logger.error(f"Erro ao obter estatísticas: {resultado.get('error', 'Erro desconhecido')}")
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro ao obter estatísticas')
            }), 500
            
        logger.info("Estatísticas obtidas com sucesso")
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro não tratado ao obter estatísticas: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

# Rota de teste/debug
@api_bp.route('/test', methods=['GET'])
def test_api():
    """Rota de teste para verificar se a API está funcionando."""
    try:
        gerenciador = current_app.config.get('GERENCIADOR_RFID')
        return jsonify({
            'success': True,
            'message': 'API funcionando',
            'gerenciador_status': 'OK' if gerenciador else 'Não inicializado'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500