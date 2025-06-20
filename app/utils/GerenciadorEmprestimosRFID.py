# app/utils/GerenciadorEmprestimosRFID.py
import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime, timedelta
from ..config import MYSQL_CONFIG
import json
import hashlib

class GerenciadorEmprestimosRFID:
    """Gerenciador para operações com empréstimos de ferramentas RFID no MySQL com sistema de cache."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Retorna a instância única do gerenciador (Singleton)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Inicializa o gerenciador."""
        if GerenciadorEmprestimosRFID._instance is not None:
            raise Exception("Use get_instance() para obter a instância")
        
        self.logger = logging.getLogger('controlerfid.gerenciador_emprestimos')
        self.config = MYSQL_CONFIG
        
        # Sistema de cache
        self.cache = {}
        self.cache_timeout = timedelta(minutes=5)  # Cache válido por 5 minutos
        
        self.logger.info("Gerenciador de Empréstimos RFID inicializado com cache")
    
    def _get_cache_key(self, prefix, params=None):
        """Gera uma chave única para o cache baseada nos parâmetros."""
        if params:
            params_str = json.dumps(params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()
            return f"{prefix}_{params_hash}"
        return prefix
    
    def _get_from_cache(self, key):
        """Obtém dados do cache se ainda válidos."""
        if key in self.cache:
            cached_data, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.cache_timeout:
                self.logger.debug(f"Cache hit para key: {key}")
                return cached_data
            else:
                del self.cache[key]
                self.logger.debug(f"Cache expirado para key: {key}")
        return None
    
    def _set_cache(self, key, data):
        """Armazena dados no cache."""
        self.cache[key] = (data, datetime.now())
        self.logger.debug(f"Dados armazenados no cache para key: {key}")
    
    def limpar_cache(self):
        """Limpa todo o cache."""
        self.cache.clear()
        self.logger.info("Cache limpo")
    
    def _get_connection(self):
        """Cria e retorna uma conexão com o MySQL."""
        try:
            connection = mysql.connector.connect(
                host=self.config['host'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password'],
                connection_timeout=self.config['connection_timeout'],
                autocommit=True
            )
            return connection
        except Error as e:
            self.logger.error(f"Erro ao conectar ao MySQL: {e}")
            raise
    
    def criar_emprestimo(self, dados):
        """
        Cria um novo empréstimo de ferramenta.
        
        Args:
            dados (dict): Dados do empréstimo:
                - id_colaborador: ID do colaborador (obrigatório)
                - EtiquetaRFID_hex: Código hex da etiqueta (obrigatório)
                - dataEmprestimo: Data/hora do empréstimo (opcional, padrão: agora)
                - Observacao: Observações sobre o empréstimo (opcional)
                
        Returns:
            dict: Resultado da operação com ID do novo empréstimo
        """
        connection = None
        cursor = None
        
        try:
            # Validar dados obrigatórios
            if not dados.get('id_colaborador'):
                return {
                    'success': False,
                    'error': 'ID do colaborador é obrigatório'
                }
            
            if not dados.get('EtiquetaRFID_hex'):
                return {
                    'success': False,
                    'error': 'Código da etiqueta RFID é obrigatório'
                }
            
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Verificar se a ferramenta existe
            check_etiqueta = """
                SELECT id_listaEtiquetasRFID, Descricao 
                FROM etiquetasRFID 
                WHERE EtiquetaRFID_hex = %s AND Destruida IS NULL
            """
            cursor.execute(check_etiqueta, (dados['EtiquetaRFID_hex'],))
            etiqueta = cursor.fetchone()
            
            if not etiqueta:
                return {
                    'success': False,
                    'error': 'Etiqueta não encontrada ou está destruída'
                }
            
            # Verificar se a ferramenta já está emprestada
            check_emprestimo = """
                SELECT id, id_colaborador 
                FROM emprestimoRFID 
                WHERE EtiquetaRFID_hex = %s AND dataDevolucao IS NULL
            """
            cursor.execute(check_emprestimo, (dados['EtiquetaRFID_hex'],))
            emprestimo_ativo = cursor.fetchone()
            
            if emprestimo_ativo:
                return {
                    'success': False,
                    'error': f'Ferramenta já está emprestada para o colaborador ID {emprestimo_ativo[1]}'
                }
            
            # Preparar dados para inserção
            dataEmprestimo = dados.get('dataEmprestimo', datetime.now())
            observacao = dados.get('Observacao', '')
            
            # Inserir empréstimo
            insert_query = """
                INSERT INTO emprestimoRFID 
                (id_colaborador, EtiquetaRFID_hex, dataEmprestimo, Observacao)
                VALUES (%s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (
                dados['id_colaborador'],
                dados['EtiquetaRFID_hex'],
                dataEmprestimo,
                observacao
            ))
            
            id_emprestimo = cursor.lastrowid
            
            # Limpar cache após inserção
            self.limpar_cache()
            
            return {
                'success': True,
                'message': 'Empréstimo registrado com sucesso',
                'id_emprestimo': id_emprestimo,
                'descricao_ferramenta': etiqueta[1]
            }
            
        except Error as e:
            self.logger.error(f"Erro ao criar empréstimo: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def registrar_devolucao(self, id_emprestimo, observacao_devolucao=None):
        """
        Registra a devolução de uma ferramenta.
        
        Args:
            id_emprestimo (int): ID do empréstimo
            observacao_devolucao (str): Observações sobre a devolução (opcional)
            
        Returns:
            dict: Resultado da operação
        """
        connection = None
        cursor = None
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Verificar se o empréstimo existe e está ativo
            check_query = """
                SELECT id, dataDevolucao 
                FROM emprestimoRFID 
                WHERE id = %s
            """
            cursor.execute(check_query, (id_emprestimo,))
            emprestimo = cursor.fetchone()
            
            if not emprestimo:
                return {
                    'success': False,
                    'error': 'Empréstimo não encontrado'
                }
            
            if emprestimo[1] is not None:
                return {
                    'success': False,
                    'error': 'Este empréstimo já foi devolvido'
                }
            
            # Atualizar com data de devolução
            update_query = """
                UPDATE emprestimoRFID 
                SET dataDevolucao = %s, Observacao = CONCAT(Observacao, %s)
                WHERE id = %s
            """
            
            obs_adicional = f"\nDevolução: {observacao_devolucao}" if observacao_devolucao else ""
            
            cursor.execute(update_query, (
                datetime.now(),
                obs_adicional,
                id_emprestimo
            ))
            
            # Limpar cache após atualização
            self.limpar_cache()
            
            return {
                'success': True,
                'message': 'Devolução registrada com sucesso'
            }
            
        except Error as e:
            self.logger.error(f"Erro ao registrar devolução: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def obter_emprestimos(self, filtros=None, limite=100, offset=0, force_refresh=False):
        """
        Obtém lista de empréstimos com filtros opcionais.
        
        Args:
            filtros (dict): Dicionário com filtros:
                - id_colaborador: ID do colaborador
                - etiqueta: Código da etiqueta RFID
                - status: 'ativo' ou 'devolvido'
                - data_inicio: Data início (formato: YYYY-MM-DD)
                - data_fim: Data fim (formato: YYYY-MM-DD)
            limite (int): Número máximo de registros
            offset (int): Deslocamento para paginação
            force_refresh (bool): Força atualização ignorando o cache
            
        Returns:
            dict: Resultado com empréstimos e total
        """
        cache_params = {
            'filtros': filtros or {},
            'limite': limite,
            'offset': offset
        }
        cache_key = self._get_cache_key('emprestimos', cache_params)
        
        # Verificar cache primeiro
        if not force_refresh:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                cached_result['from_cache'] = True
                return cached_result
        
        connection = None
        cursor = None
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Construir query com JOINs
            base_query = """
                SELECT 
                    e.id,
                    e.id_colaborador,
                    e.EtiquetaRFID_hex,
                    e.dataEmprestimo,
                    e.dataDevolucao,
                    e.Observacao,
                    et.Descricao as descricao_ferramenta,
                    CASE 
                        WHEN e.dataDevolucao IS NULL THEN 'ativo'
                        ELSE 'devolvido'
                    END as status
                FROM emprestimoRFID e
                LEFT JOIN etiquetasRFID et ON e.EtiquetaRFID_hex = et.EtiquetaRFID_hex
                WHERE 1=1
            """
            
            where_conditions = []
            params = []
            
            if filtros:
                if filtros.get('id_colaborador'):
                    where_conditions.append("e.id_colaborador = %s")
                    params.append(filtros['id_colaborador'])
                
                if filtros.get('etiqueta'):
                    where_conditions.append("e.EtiquetaRFID_hex LIKE %s")
                    params.append(f"%{filtros['etiqueta']}%")
                
                if filtros.get('status'):
                    if filtros['status'] == 'ativo':
                        where_conditions.append("e.dataDevolucao IS NULL")
                    elif filtros['status'] == 'devolvido':
                        where_conditions.append("e.dataDevolucao IS NOT NULL")
                
                if filtros.get('data_inicio'):
                    where_conditions.append("DATE(e.dataEmprestimo) >= %s")
                    params.append(filtros['data_inicio'])
                
                if filtros.get('data_fim'):
                    where_conditions.append("DATE(e.dataEmprestimo) <= %s")
                    params.append(filtros['data_fim'])
            
            # Adicionar condições WHERE
            if where_conditions:
                base_query += " AND " + " AND ".join(where_conditions)
            
            # Query para contar total
            count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']
            
            # Query para obter dados com paginação
            data_query = base_query + " ORDER BY e.dataEmprestimo DESC LIMIT %s OFFSET %s"
            params.extend([limite, offset])
            
            cursor.execute(data_query, params)
            emprestimos = cursor.fetchall()
            
            # Processar datas para formato legível
            for emp in emprestimos:
                if emp['dataEmprestimo']:
                    emp['dataEmprestimo_formatada'] = emp['dataEmprestimo'].strftime('%d/%m/%Y %H:%M')
                if emp['dataDevolucao']:
                    emp['dataDevolucao_formatada'] = emp['dataDevolucao'].strftime('%d/%m/%Y %H:%M')
                else:
                    emp['dataDevolucao_formatada'] = None
            
            result = {
                'success': True,
                'emprestimos': emprestimos,
                'total': total,
                'limite': limite,
                'offset': offset,
                'from_cache': False
            }
            
            # Armazenar no cache
            self._set_cache(cache_key, result)
            
            return result
            
        except Error as e:
            self.logger.error(f"Erro ao obter empréstimos: {e}")
            return {
                'success': False,
                'error': str(e),
                'emprestimos': [],
                'total': 0,
                'from_cache': False
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def obter_emprestimos_ativos_colaborador(self, id_colaborador):
        """
        Obtém todos os empréstimos ativos de um colaborador específico.
        
        Args:
            id_colaborador (int): ID do colaborador
            
        Returns:
            dict: Resultado com empréstimos ativos
        """
        return self.obter_emprestimos(
            filtros={
                'id_colaborador': id_colaborador,
                'status': 'ativo'
            }
        )
    
    def obter_historico_ferramenta(self, etiqueta_rfid_hex):
        """
        Obtém o histórico completo de empréstimos de uma ferramenta.
        
        Args:
            etiqueta_rfid_hex (str): Código hexadecimal da etiqueta
            
        Returns:
            dict: Resultado com histórico de empréstimos
        """
        return self.obter_emprestimos(
            filtros={'etiqueta': etiqueta_rfid_hex},
            limite=1000  # Histórico completo
        )
    
    def obter_estatisticas_emprestimos(self, force_refresh=False):
        """
        Obtém estatísticas gerais dos empréstimos.
        
        Args:
            force_refresh (bool): Força atualização ignorando o cache
            
        Returns:
            dict: Estatísticas dos empréstimos
        """
        cache_key = 'estatisticas_emprestimos'
        
        if not force_refresh:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                cached_result['from_cache'] = True
                return cached_result
        
        connection = None
        cursor = None
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Total de empréstimos
            cursor.execute("SELECT COUNT(*) as total FROM emprestimoRFID")
            total_emprestimos = cursor.fetchone()['total']
            
            # Empréstimos ativos
            cursor.execute("SELECT COUNT(*) as ativos FROM emprestimoRFID WHERE dataDevolucao IS NULL")
            emprestimos_ativos = cursor.fetchone()['ativos']
            
            # Ferramentas mais emprestadas
            query_top_ferramentas = """
                SELECT 
                    e.EtiquetaRFID_hex,
                    et.Descricao,
                    COUNT(*) as total_emprestimos
                FROM emprestimoRFID e
                LEFT JOIN etiquetasRFID et ON e.EtiquetaRFID_hex = et.EtiquetaRFID_hex
                GROUP BY e.EtiquetaRFID_hex
                ORDER BY total_emprestimos DESC
                LIMIT 10
            """
            cursor.execute(query_top_ferramentas)
            top_ferramentas = cursor.fetchall()
            
            # Colaboradores com mais empréstimos ativos
            query_top_colaboradores = """
                SELECT 
                    id_colaborador,
                    COUNT(*) as emprestimos_ativos
                FROM emprestimoRFID
                WHERE dataDevolucao IS NULL
                GROUP BY id_colaborador
                ORDER BY emprestimos_ativos DESC
                LIMIT 10
            """
            cursor.execute(query_top_colaboradores)
            top_colaboradores = cursor.fetchall()
            
            result = {
                'success': True,
                'estatisticas': {
                    'total_emprestimos': total_emprestimos,
                    'emprestimos_ativos': emprestimos_ativos,
                    'emprestimos_devolvidos': total_emprestimos - emprestimos_ativos,
                    'percentual_ativos': round((emprestimos_ativos / total_emprestimos * 100) if total_emprestimos > 0 else 0, 2),
                    'top_ferramentas': top_ferramentas,
                    'top_colaboradores_ativos': top_colaboradores
                },
                'from_cache': False
            }
            
            # Armazenar no cache
            self._set_cache(cache_key, result)
            
            return result
            
        except Error as e:
            self.logger.error(f"Erro ao obter estatísticas: {e}")
            return {
                'success': False,
                'error': str(e),
                'estatisticas': {},
                'from_cache': False
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def verificar_disponibilidade_ferramenta(self, etiqueta_rfid_hex):
        """
        Verifica se uma ferramenta está disponível para empréstimo.
        
        Args:
            etiqueta_rfid_hex (str): Código hexadecimal da etiqueta
            
        Returns:
            dict: Informações sobre disponibilidade
        """
        connection = None
        cursor = None
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Verificar se a etiqueta existe e não está destruída
            query_etiqueta = """
                SELECT id_listaEtiquetasRFID, Descricao, Destruida
                FROM etiquetasRFID
                WHERE EtiquetaRFID_hex = %s
            """
            cursor.execute(query_etiqueta, (etiqueta_rfid_hex,))
            etiqueta = cursor.fetchone()
            
            if not etiqueta:
                return {
                    'success': False,
                    'disponivel': False,
                    'motivo': 'Etiqueta não encontrada'
                }
            
            if etiqueta['Destruida'] is not None:
                return {
                    'success': True,
                    'disponivel': False,
                    'motivo': 'Ferramenta está destruída',
                    'descricao': etiqueta['Descricao']
                }
            
            # Verificar se está emprestada
            query_emprestimo = """
                SELECT id, id_colaborador, dataEmprestimo
                FROM emprestimoRFID
                WHERE EtiquetaRFID_hex = %s AND dataDevolucao IS NULL
            """
            cursor.execute(query_emprestimo, (etiqueta_rfid_hex,))
            emprestimo_ativo = cursor.fetchone()
            
            if emprestimo_ativo:
                return {
                    'success': True,
                    'disponivel': False,
                    'motivo': 'Ferramenta está emprestada',
                    'descricao': etiqueta['Descricao'],
                    'emprestimo_ativo': {
                        'id': emprestimo_ativo['id'],
                        'id_colaborador': emprestimo_ativo['id_colaborador'],
                        'data_emprestimo': emprestimo_ativo['dataEmprestimo'].strftime('%d/%m/%Y %H:%M')
                    }
                }
            
            return {
                'success': True,
                'disponivel': True,
                'descricao': etiqueta['Descricao']
            }
            
        except Error as e:
            self.logger.error(f"Erro ao verificar disponibilidade: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()