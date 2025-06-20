# app/routes/api_emprestimos.py
from flask import Blueprint, jsonify, request, current_app
import logging
import traceback
from datetime import datetime

api_emprestimos_bp = Blueprint('api_emprestimos', __name__)
logger = logging.getLogger('RFID.api_emprestimos')

@api_emprestimos_bp.route('/emprestimos', methods=['GET'])
def listar_emprestimos():
    """
    API para listar empréstimos com paginação e filtros.
    
    Query params:
        - limite: número de registros por página (padrão: 20)
        - offset: deslocamento (padrão: 0)
        - id_colaborador: filtro por ID do colaborador
        - etiqueta: filtro por código da etiqueta
        - status: filtro por status (ativo/devolvido)
        - data_inicio: filtro por data início (formato: YYYY-MM-DD)
        - data_fim: filtro por data fim (formato: YYYY-MM-DD)
        - force_refresh: forçar atualização do cache (true/false)
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_EMPRESTIMOS_RFID')
        if not gerenciador:
            logger.error("Gerenciador de Empréstimos RFID não encontrado no config")
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
        
        if request.args.get('id_colaborador'):
            try:
                filtros['id_colaborador'] = int(request.args.get('id_colaborador'))
            except ValueError:
                logger.error(f"ID colaborador inválido: {request.args.get('id_colaborador')}")
                return jsonify({
                    'success': False,
                    'error': 'ID do colaborador deve ser um número'
                }), 400
        
        if request.args.get('etiqueta'):
            filtros['etiqueta'] = request.args.get('etiqueta')
        
        if request.args.get('status'):
            status = request.args.get('status').lower()
            if status in ['ativo', 'devolvido']:
                filtros['status'] = status
            else:
                return jsonify({
                    'success': False,
                    'error': 'Status deve ser "ativo" ou "devolvido"'
                }), 400
        
        if request.args.get('data_inicio'):
            filtros['data_inicio'] = request.args.get('data_inicio')
        
        if request.args.get('data_fim'):
            filtros['data_fim'] = request.args.get('data_fim')
        
        # Verificar se é uma atualização forçada
        force_refresh = request.args.get('force_refresh', '').lower() == 'true'
        
        logger.info(f"Buscando empréstimos com filtros: {filtros}, limite: {limite}, offset: {offset}, force_refresh: {force_refresh}")
        
        # Buscar empréstimos
        resultado = gerenciador.obter_emprestimos(
            filtros=filtros,
            limite=limite,
            offset=offset,
            force_refresh=force_refresh
        )
        
        if not resultado.get('success', False):
            logger.error(f"Erro ao obter empréstimos: {resultado.get('error', 'Erro desconhecido')}")
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro ao buscar empréstimos')
            }), 500
        
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro não tratado ao listar empréstimos: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@api_emprestimos_bp.route('/emprestimos', methods=['POST'])
def criar_emprestimo():
    """
    Cria um novo empréstimo de ferramenta.
    
    Body JSON:
        - id_colaborador: ID do colaborador (obrigatório)
        - EtiquetaRFID_hex: código hexadecimal da etiqueta (obrigatório)
        - Observacao: observações sobre o empréstimo (opcional)
        - dataEmprestimo: data/hora do empréstimo (opcional, padrão: agora)
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_EMPRESTIMOS_RFID')
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
        
        if not dados.get('EtiquetaRFID_hex'):
            return jsonify({
                'success': False,
                'error': 'Código da etiqueta RFID é obrigatório'
            }), 400
        
        logger.info(f"Criando empréstimo - Colaborador: {dados.get('id_colaborador')}, Etiqueta: {dados.get('EtiquetaRFID_hex')}")
        
        # Criar empréstimo
        resultado = gerenciador.criar_emprestimo(dados)
        
        if resultado['success']:
            return jsonify(resultado), 201
        else:
            return jsonify(resultado), 400
    
    except Exception as e:
        logger.error(f"Erro ao criar empréstimo: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_emprestimos_bp.route('/emprestimos/<int:id_emprestimo>/devolver', methods=['POST'])
def devolver_ferramenta(id_emprestimo):
    """
    Registra a devolução de uma ferramenta.
    
    Body JSON (opcional):
        - observacao_devolucao: observações sobre a devolução
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_EMPRESTIMOS_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        # Obter observação opcional
        observacao_devolucao = None
        if request.is_json:
            dados = request.get_json()
            observacao_devolucao = dados.get('observacao_devolucao')
        
        logger.info(f"Registrando devolução do empréstimo {id_emprestimo}")
        
        # Registrar devolução
        resultado = gerenciador.registrar_devolucao(id_emprestimo, observacao_devolucao)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
    
    except Exception as e:
        logger.error(f"Erro ao registrar devolução: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_emprestimos_bp.route('/emprestimos/colaborador/<int:id_colaborador>/ativos', methods=['GET'])
def listar_emprestimos_ativos_colaborador(id_colaborador):
    """
    Lista todos os empréstimos ativos de um colaborador específico.
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_EMPRESTIMOS_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        logger.info(f"Buscando empréstimos ativos do colaborador {id_colaborador}")
        
        resultado = gerenciador.obter_emprestimos_ativos_colaborador(id_colaborador)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 500
    
    except Exception as e:
        logger.error(f"Erro ao buscar empréstimos ativos: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_emprestimos_bp.route('/emprestimos/ferramenta/<etiqueta_hex>/historico', methods=['GET'])
def obter_historico_ferramenta(etiqueta_hex):
    """
    Obtém o histórico completo de empréstimos de uma ferramenta.
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_EMPRESTIMOS_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        logger.info(f"Buscando histórico da ferramenta {etiqueta_hex}")
        
        resultado = gerenciador.obter_historico_ferramenta(etiqueta_hex)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 500
    
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_emprestimos_bp.route('/emprestimos/ferramenta/<etiqueta_hex>/disponibilidade', methods=['GET'])
def verificar_disponibilidade(etiqueta_hex):
    """
    Verifica se uma ferramenta está disponível para empréstimo.
    
    Retorna:
        - disponivel: boolean indicando se está disponível
        - motivo: razão caso não esteja disponível
        - descricao: descrição da ferramenta
        - emprestimo_ativo: dados do empréstimo ativo (se houver)
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_EMPRESTIMOS_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        logger.info(f"Verificando disponibilidade da ferramenta {etiqueta_hex}")
        
        resultado = gerenciador.verificar_disponibilidade_ferramenta(etiqueta_hex)
        
        if resultado.get('success', False):
            return jsonify(resultado)
        else:
            # Se não teve sucesso mas tem erro específico
            if 'error' in resultado:
                return jsonify(resultado), 500
            # Se a ferramenta não foi encontrada
            else:
                return jsonify(resultado), 404
    
    except Exception as e:
        logger.error(f"Erro ao verificar disponibilidade: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_emprestimos_bp.route('/emprestimos/estatisticas', methods=['GET'])
def obter_estatisticas_emprestimos():
    """
    Obtém estatísticas gerais dos empréstimos.
    
    Query params:
        - force_refresh: forçar atualização do cache (true/false)
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_EMPRESTIMOS_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        # Verificar se é uma atualização forçada
        force_refresh = request.args.get('force_refresh', '').lower() == 'true'
        
        logger.info(f"Obtendo estatísticas de empréstimos, force_refresh: {force_refresh}")
        
        resultado = gerenciador.obter_estatisticas_emprestimos(force_refresh=force_refresh)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 500
    
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_emprestimos_bp.route('/emprestimos/pendentes', methods=['GET'])
def listar_emprestimos_pendentes():
    """
    Lista todos os empréstimos pendentes (não devolvidos) com informações resumidas.
    Útil para dashboard e verificações rápidas.
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_EMPRESTIMOS_RFID')
        if not gerenciador:
            return jsonify({
                'success': False,
                'error': 'Gerenciador não inicializado'
            }), 500
        
        logger.info("Buscando todos os empréstimos pendentes")
        
        # Buscar apenas empréstimos ativos
        resultado = gerenciador.obter_emprestimos(
            filtros={'status': 'ativo'},
            limite=1000  # Limite alto para pegar todos
        )
        
        if resultado['success']:
            # Adicionar informação de tempo decorrido
            emprestimos = resultado.get('emprestimos', [])
            agora = datetime.now()
            
            for emp in emprestimos:
                if emp.get('dataEmprestimo'):
                    # Calcular tempo decorrido
                    data_emprestimo = emp['dataEmprestimo']
                    if isinstance(data_emprestimo, str):
                        data_emprestimo = datetime.strptime(data_emprestimo, '%Y-%m-%d %H:%M:%S')
                    
                    tempo_decorrido = agora - data_emprestimo
                    dias = tempo_decorrido.days
                    horas = tempo_decorrido.seconds // 3600
                    
                    if dias > 0:
                        emp['tempo_decorrido'] = f"{dias} dia(s) e {horas} hora(s)"
                    else:
                        emp['tempo_decorrido'] = f"{horas} hora(s)"
                    
                    # Adicionar flag de alerta se muito tempo
                    emp['alerta'] = dias > 7  # Alerta se mais de 7 dias
            
            resultado['emprestimos'] = emprestimos
            return jsonify(resultado)
        else:
            return jsonify(resultado), 500
    
    except Exception as e:
        logger.error(f"Erro ao buscar empréstimos pendentes: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Rota de teste/debug
@api_emprestimos_bp.route('/emprestimos/test', methods=['GET'])
def test_api_emprestimos():
    """Rota de teste para verificar se a API de empréstimos está funcionando."""
    try:
        gerenciador = current_app.config.get('GERENCIADOR_EMPRESTIMOS_RFID')
        return jsonify({
            'success': True,
            'message': 'API de Empréstimos funcionando',
            'gerenciador_status': 'OK' if gerenciador else 'Não inicializado',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500