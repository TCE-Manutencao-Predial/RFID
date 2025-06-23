# app/routes/api_inventarios.py
from flask import Blueprint, jsonify, request, current_app
import logging
import traceback
from datetime import datetime, timedelta
import io

api_inventarios_bp = Blueprint('api_inventarios', __name__)
logger = logging.getLogger('RFID.api_inventarios')

@api_inventarios_bp.route('/inventarios', methods=['GET'])
def listar_inventarios():
    """
    API para listar inventários com paginação e filtros.
    
    Query params:
        - limite: número de registros por página (padrão: 20)
        - offset: deslocamento (padrão: 0)
        - status: filtro por status (Em andamento/Finalizado)
        - id_colaborador: filtro por ID do colaborador
        - data_inicio: filtro por data início (formato: YYYY-MM-DD)
        - data_fim: filtro por data fim (formato: YYYY-MM-DD)
        - force_refresh: forçar atualização do cache (true/false)
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_INVENTARIOS_RFID')
        if not gerenciador:
            logger.error("Gerenciador de Inventários RFID não encontrado no config")
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
        
        if request.args.get('status'):
            status = request.args.get('status')
            if status in ['Em andamento', 'Finalizado']:
                filtros['status'] = status
            else:
                return jsonify({
                    'success': False,
                    'error': 'Status deve ser "Em andamento" ou "Finalizado"'
                }), 400
        
        if request.args.get('id_colaborador'):
            try:
                filtros['id_colaborador'] = int(request.args.get('id_colaborador'))
            except ValueError:
                logger.error(f"ID colaborador inválido: {request.args.get('id_colaborador')}")
                return jsonify({
                    'success': False,
                    'error': 'ID do colaborador deve ser um número'
                }), 400
        
        if request.args.get('data_inicio'):
            filtros['data_inicio'] = request.args.get('data_inicio')
        
        if request.args.get('data_fim'):
            filtros['data_fim'] = request.args.get('data_fim')
        
        # Verificar se é uma atualização forçada
        force_refresh = request.args.get('force_refresh', '').lower() == 'true'
        
        logger.info(f"Buscando inventários com filtros: {filtros}, limite: {limite}, offset: {offset}, force_refresh: {force_refresh}")
        
        # Buscar inventários
        resultado = gerenciador.obter_inventarios(
            filtros=filtros,
            limite=limite,
            offset=offset,
            force_refresh=force_refresh
        )
        
        if not resultado.get('success', False):
            logger.error(f"Erro ao obter inventários: {resultado.get('error', 'Erro desconhecido')}")
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro ao buscar inventários')
            }), 500
        
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro não tratado ao listar inventários: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@api_inventarios_bp.route('/inventarios', methods=['POST'])
def criar_inventario():
    """
    Cria um novo inventário.
    
    Body JSON:
        - id_colaborador: ID do colaborador responsável (obrigatório)
        - Observacao: observações sobre o inventário (opcional)
        - dataInventario: data do inventário (opcional, padrão: agora)
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_INVENTARIOS_RFID')
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
        if not dados.get('id_colaborador'):
            return jsonify({
                'success': False,
                'error': 'ID do colaborador é obrigatório'
            }), 400
        
        logger.info(f"Criando inventário - Colaborador: {dados.get('id_colaborador')}")
        
        # Criar inventário
        resultado = gerenciador.criar_inventario(dados)
        
        if resultado['success']:
            return jsonify(resultado), 201
        else:
            return jsonify(resultado), 400
    
    except Exception as e:
        logger.error(f"Erro ao criar inventário: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_inventarios_bp.route('/inventarios/<int:id_inventario>', methods=['GET'])
def obter_detalhes_inventario(id_inventario):
    """
    Obtém detalhes completos de um inventário específico.
    
    Retorna:
        - Dados do inventário
        - Lista de todos os itens (localizados e não localizados)
        - Estatísticas do inventário
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_INVENTARIOS_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        logger.info(f"Obtendo detalhes do inventário {id_inventario}")
        
        resultado = gerenciador.obter_detalhes_inventario(id_inventario)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            # Se o inventário não foi encontrado
            if resultado.get('error') == 'Inventário não encontrado':
                return jsonify(resultado), 404
            else:
                return jsonify(resultado), 500
    
    except Exception as e:
        logger.error(f"Erro ao obter detalhes do inventário: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_inventarios_bp.route('/inventarios/<int:id_inventario>/processar-csv', methods=['POST'])
def processar_csv_inventario(id_inventario):
    """
    Processa arquivo CSV com leituras de leitor móvel para um inventário.
    
    O arquivo CSV deve conter uma coluna 'EPC' com os códigos das etiquetas.
    
    Body:
        - Multipart form-data com arquivo CSV
        - OU JSON com campo 'csv_content' contendo o conteúdo do CSV
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_INVENTARIOS_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        arquivo_csv = None
        
        # Verificar se é upload de arquivo
        if 'arquivo' in request.files:
            file = request.files['arquivo']
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': 'Nenhum arquivo selecionado'
                }), 400
            
            # Verificar extensão
            if not file.filename.lower().endswith('.csv'):
                return jsonify({
                    'success': False,
                    'error': 'Arquivo deve ser CSV'
                }), 400
            
            arquivo_csv = file
        
        # Verificar se é JSON com conteúdo CSV
        elif request.is_json:
            dados = request.get_json()
            csv_content = dados.get('csv_content')
            
            if not csv_content:
                return jsonify({
                    'success': False,
                    'error': 'Campo "csv_content" não encontrado'
                }), 400
            
            arquivo_csv = csv_content
        
        else:
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo CSV fornecido'
            }), 400
        
        logger.info(f"Processando CSV para inventário {id_inventario}")
        
        # Processar CSV
        resultado = gerenciador.processar_csv_leituras(id_inventario, arquivo_csv)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
    
    except Exception as e:
        logger.error(f"Erro ao processar CSV: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_inventarios_bp.route('/inventarios/<int:id_inventario>/finalizar', methods=['POST'])
def finalizar_inventario(id_inventario):
    """
    Finaliza um inventário em andamento.
    
    Após finalizado, o inventário não pode mais receber atualizações.
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_INVENTARIOS_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        logger.info(f"Finalizando inventário {id_inventario}")
        
        resultado = gerenciador.finalizar_inventario(id_inventario)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            # Verificar tipo de erro
            if resultado.get('error') == 'Inventário não encontrado':
                return jsonify(resultado), 404
            elif resultado.get('error') == 'Inventário já foi finalizado':
                return jsonify(resultado), 400
            else:
                return jsonify(resultado), 500
    
    except Exception as e:
        logger.error(f"Erro ao finalizar inventário: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_inventarios_bp.route('/inventarios/<int:id_inventario>/itens', methods=['GET'])
def listar_itens_inventario(id_inventario):
    """
    Lista itens de um inventário com filtros.
    
    Query params:
        - status: filtro por status (Localizado/Não localizado)
        - etiqueta: filtro por código da etiqueta
        - descricao: filtro por descrição
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_INVENTARIOS_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        # Obter detalhes completos do inventário
        resultado = gerenciador.obter_detalhes_inventario(id_inventario)
        
        if not resultado['success']:
            if resultado.get('error') == 'Inventário não encontrado':
                return jsonify(resultado), 404
            else:
                return jsonify(resultado), 500
        
        # Aplicar filtros nos itens
        itens = resultado.get('itens', [])
        
        # Filtro por status
        status_filtro = request.args.get('status')
        if status_filtro:
            itens = [item for item in itens if item.get('Status') == status_filtro]
        
        # Filtro por etiqueta
        etiqueta_filtro = request.args.get('etiqueta')
        if etiqueta_filtro:
            itens = [item for item in itens if etiqueta_filtro.lower() in item.get('EtiquetaRFID_hex', '').lower()]
        
        # Filtro por descrição
        descricao_filtro = request.args.get('descricao')
        if descricao_filtro:
            itens = [item for item in itens if descricao_filtro.lower() in (item.get('DescricaoEtiqueta') or '').lower()]
        
        # Recalcular estatísticas com itens filtrados
        total_itens = len(itens)
        itens_localizados = sum(1 for item in itens if item.get('Status') == 'Localizado')
        
        return jsonify({
            'success': True,
            'id_inventario': id_inventario,
            'itens': itens,
            'total': total_itens,
            'estatisticas_filtradas': {
                'total_itens': total_itens,
                'itens_localizados': itens_localizados,
                'itens_nao_localizados': total_itens - itens_localizados,
                'percentual_localizado': round((itens_localizados / total_itens * 100) if total_itens > 0 else 0, 2)
            }
        })
    
    except Exception as e:
        logger.error(f"Erro ao listar itens do inventário: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_inventarios_bp.route('/inventarios/estatisticas', methods=['GET'])
def obter_estatisticas_inventarios():
    """
    Obtém estatísticas gerais dos inventários.
    
    Query params:
        - periodo: últimos X dias (padrão: 30)
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_INVENTARIOS_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        # Obter período
        try:
            periodo_dias = int(request.args.get('periodo', 30))
            if periodo_dias > 365:
                periodo_dias = 365
        except ValueError:
            periodo_dias = 30
        
        # Calcular data início
        data_inicio = (datetime.now() - timedelta(days=periodo_dias)).strftime('%Y-%m-%d')
        
        logger.info(f"Obtendo estatísticas de inventários dos últimos {periodo_dias} dias")
        
        # Buscar todos os inventários do período
        resultado = gerenciador.obter_inventarios(
            filtros={'data_inicio': data_inicio},
            limite=1000  # Buscar todos
        )
        
        if not resultado['success']:
            return jsonify(resultado), 500
        
        inventarios = resultado.get('inventarios', [])
        
        # Calcular estatísticas
        total_inventarios = len(inventarios)
        inventarios_finalizados = sum(1 for inv in inventarios if inv.get('Status') == 'Finalizado')
        inventarios_em_andamento = sum(1 for inv in inventarios if inv.get('Status') == 'Em andamento')
        
        # Estatísticas de itens
        total_itens_verificados = sum(inv.get('total_itens', 0) for inv in inventarios)
        total_itens_localizados = sum(inv.get('itens_localizados', 0) for inv in inventarios)
        
        # Taxa média de localização
        taxa_localizacao_media = 0
        if inventarios:
            taxas = [inv.get('percentual_localizado', 0) for inv in inventarios if inv.get('total_itens', 0) > 0]
            if taxas:
                taxa_localizacao_media = round(sum(taxas) / len(taxas), 2)
        
        # Inventários por colaborador
        inventarios_por_colaborador = {}
        for inv in inventarios:
            colab_id = inv.get('id_colaborador')
            if colab_id:
                if colab_id not in inventarios_por_colaborador:
                    inventarios_por_colaborador[colab_id] = 0
                inventarios_por_colaborador[colab_id] += 1
        
        # Top 5 colaboradores
        top_colaboradores = sorted(
            inventarios_por_colaborador.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return jsonify({
            'success': True,
            'periodo_dias': periodo_dias,
            'data_inicio': data_inicio,
            'estatisticas': {
                'total_inventarios': total_inventarios,
                'inventarios_finalizados': inventarios_finalizados,
                'inventarios_em_andamento': inventarios_em_andamento,
                'total_itens_verificados': total_itens_verificados,
                'total_itens_localizados': total_itens_localizados,
                'taxa_localizacao_media': taxa_localizacao_media,
                'top_colaboradores': [
                    {'id_colaborador': colab[0], 'total_inventarios': colab[1]}
                    for colab in top_colaboradores
                ]
            }
        })
    
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_inventarios_bp.route('/inventarios/ultimo', methods=['GET'])
def obter_ultimo_inventario():
    """
    Obtém o último inventário criado (útil para continuar inventário em andamento).
    
    Query params:
        - id_colaborador: filtrar por colaborador específico
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_INVENTARIOS_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        filtros = {}
        if request.args.get('id_colaborador'):
            try:
                filtros['id_colaborador'] = int(request.args.get('id_colaborador'))
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'ID do colaborador deve ser um número'
                }), 400
        
        # Buscar inventários ordenados por data
        resultado = gerenciador.obter_inventarios(
            filtros=filtros,
            limite=1,
            offset=0
        )
        
        if not resultado['success']:
            return jsonify(resultado), 500
        
        inventarios = resultado.get('inventarios', [])
        
        if inventarios:
            # Pegar o primeiro (mais recente)
            ultimo_inventario = inventarios[0]
            
            # Obter detalhes completos
            detalhes = gerenciador.obter_detalhes_inventario(ultimo_inventario['idInventarioRFID'])
            
            if detalhes['success']:
                return jsonify(detalhes)
            else:
                return jsonify(detalhes), 500
        else:
            return jsonify({
                'success': False,
                'error': 'Nenhum inventário encontrado'
            }), 404
    
    except Exception as e:
        logger.error(f"Erro ao obter último inventário: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_inventarios_bp.route('/inventarios/download-template', methods=['GET'])
def download_template_csv():
    """
    Fornece um template CSV de exemplo para upload de leituras.
    """
    try:
        # Criar CSV de exemplo
        csv_content = """EPC,Observacao
00000000000000000001234567,Exemplo de etiqueta 1
61706172000000000087654321,Exemplo de etiqueta 2
AAA0AAAA12345678,Exemplo de etiqueta 3
32366259FC000001,Exemplo de etiqueta 4
"""
        
        # Criar response com o CSV
        output = io.StringIO()
        output.write(csv_content)
        output.seek(0)
        
        from flask import Response
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=template_inventario_rfid.csv'
            }
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Erro ao gerar template CSV: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Rota de teste/debug
@api_inventarios_bp.route('/inventarios/test', methods=['GET'])
def test_api_inventarios():
    """Rota de teste para verificar se a API de inventários está funcionando."""
    try:
        gerenciador = current_app.config.get('GERENCIADOR_INVENTARIOS_RFID')
        return jsonify({
            'success': True,
            'message': 'API de Inventários funcionando',
            'gerenciador_status': 'OK' if gerenciador else 'Não inicializado',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'endpoints': [
                'GET /inventarios - Listar inventários',
                'POST /inventarios - Criar inventário',
                'GET /inventarios/{id} - Detalhes do inventário',
                'POST /inventarios/{id}/processar-csv - Processar CSV',
                'POST /inventarios/{id}/finalizar - Finalizar inventário',
                'GET /inventarios/{id}/itens - Listar itens',
                'GET /inventarios/estatisticas - Estatísticas gerais',
                'GET /inventarios/ultimo - Último inventário',
                'GET /inventarios/download-template - Template CSV'
            ]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500