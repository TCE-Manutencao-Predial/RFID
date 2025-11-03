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
        
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro não tratado ao listar etiquetas: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@api_bp.route('/etiquetas', methods=['POST'])
def criar_etiqueta():
    """
    Cria uma nova etiqueta RFID.
    
    Body JSON:
        - EtiquetaRFID_hex: código hexadecimal da etiqueta (obrigatório)
        - Descricao: descrição da etiqueta (opcional)
        - Foto: imagem em base64 (opcional)
    """
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
        
        # Validar dados obrigatórios
        if not dados.get('EtiquetaRFID_hex'):
            return jsonify({
                'success': False,
                'error': 'Código da etiqueta (EtiquetaRFID_hex) é obrigatório'
            }), 400
        
        logger.info(f"Criando nova etiqueta: {dados.get('EtiquetaRFID_hex')}")
        
        # Criar etiqueta
        resultado = gerenciador.criar_etiqueta(dados)
        
        if resultado['success']:
            return jsonify(resultado), 201
        else:
            return jsonify(resultado), 400
    
    except Exception as e:
        logger.error(f"Erro ao criar etiqueta: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
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
    """
    Atualiza dados de uma etiqueta.
    
    Body JSON:
        - EtiquetaRFID_hex: novo código da etiqueta (opcional)
        - Descricao: nova descrição (opcional)
        - Destruida: status da etiqueta (opcional)
        - Foto: nova imagem em base64 (opcional)
    """
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
        
        logger.info(f"Atualizando etiqueta {id_etiqueta} com dados: {list(dados.keys())}")
        
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

@api_bp.route('/etiquetas/<int:id_etiqueta>/destruir', methods=['POST'])
def destruir_etiqueta(id_etiqueta):
    """
    Marca uma etiqueta como destruída (soft delete).
    Preenche o campo Destruida com a data/hora atual.
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        logger.info(f"Destruindo etiqueta {id_etiqueta}")
        
        # Destruir etiqueta (soft delete)
        resultado = gerenciador.destruir_etiqueta(id_etiqueta)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
    
    except Exception as e:
        logger.error(f"Erro ao destruir etiqueta {id_etiqueta}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/etiquetas/<int:id_etiqueta>/restaurar', methods=['POST'])
def restaurar_etiqueta(id_etiqueta):
    """
    Restaura uma etiqueta destruída.
    Define o campo Destruida como NULL.
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        logger.info(f"Restaurando etiqueta {id_etiqueta}")
        
        # Restaurar etiqueta
        resultado = gerenciador.restaurar_etiqueta(id_etiqueta)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
    
    except Exception as e:
        logger.error(f"Erro ao restaurar etiqueta {id_etiqueta}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/etiquetas/<int:id_etiqueta>/foto', methods=['POST'])
def upload_foto_etiqueta(id_etiqueta):
    """
    Upload de foto para uma etiqueta específica.
    
    Body pode ser:
        - JSON com campo 'foto' contendo base64
        - Multipart form-data com arquivo de imagem
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        foto_data = None
        
        # Verificar se é JSON com base64
        if request.is_json:
            dados = request.get_json()
            foto_data = dados.get('foto') or dados.get('Foto')
            
            if not foto_data:
                return jsonify({
                    'success': False,
                    'error': 'Campo "foto" não encontrado no JSON'
                }), 400
        
        # Verificar se é upload de arquivo
        elif 'foto' in request.files:
            file = request.files['foto']
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': 'Nenhum arquivo selecionado'
                }), 400
            
            # Ler arquivo e converter para base64
            import base64
            foto_data = base64.b64encode(file.read()).decode('utf-8')
        
        else:
            return jsonify({
                'success': False,
                'error': 'Nenhuma foto fornecida'
            }), 400
        
        logger.info(f"Fazendo upload de foto para etiqueta {id_etiqueta}")
        
        # Atualizar apenas a foto
        resultado = gerenciador.atualizar_etiqueta(id_etiqueta, {'Foto': foto_data})
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
    
    except Exception as e:
        logger.error(f"Erro ao fazer upload de foto para etiqueta {id_etiqueta}: {str(e)}")
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

@api_bp.route('/migrations/status', methods=['GET'])
def get_migrations_status():
    """
    Retorna o status das migrations executadas na inicialização.
    
    Returns:
        JSON com informações sobre as migrations executadas
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        status = gerenciador.get_migration_status()
        
        return jsonify({
            'success': True,
            'migration_status': status
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status de migrations: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
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