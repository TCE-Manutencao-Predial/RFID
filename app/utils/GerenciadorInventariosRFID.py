# app/utils/GerenciadorInventariosRFID.py
import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime, timedelta
from ..config import MYSQL_CONFIG
import json
import hashlib
import csv
import io
from .GerenciadorEtiquetasRFID import GerenciadorEtiquetasRFID
from .GerenciadorLeitoresRFID import GerenciadorLeitoresRFID

class GerenciadorInventariosRFID:
    """Gerenciador para operações de inventário RFID."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Retorna a instância única do gerenciador (Singleton)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Inicializa o gerenciador."""
        if GerenciadorInventariosRFID._instance is not None:
            raise Exception("Use get_instance() para obter a instância")
        
        self.logger = logging.getLogger('controlerfid.inventarios')
        self.config = MYSQL_CONFIG
        
        # Sistema de cache
        self.cache = {}
        self.cache_timeout = timedelta(minutes=5)
        
        # Referências aos outros gerenciadores
        self.gerenciador_etiquetas = GerenciadorEtiquetasRFID.get_instance()
        self.gerenciador_leitores = GerenciadorLeitoresRFID.get_instance()
        
        self.logger.info("Gerenciador de Inventários RFID inicializado")
    
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
            connection_params = {
                'host': self.config['host'],
                'database': self.config['database'],
                'user': self.config['user'],
                'password': self.config['password'],
                'connection_timeout': self.config['connection_timeout'],
                'autocommit': True
            }
            
            # Desabilita verificação SSL apenas para domínios tce.go.gov.br
            if 'tce.go.gov.br' in self.config['host'].lower():
                connection_params['ssl_disabled'] = True
            
            connection = mysql.connector.connect(**connection_params)
            return connection
        except Error as e:
            self.logger.error(f"Erro ao conectar ao MySQL: {e}")
            raise
    
    def _obter_proximo_id_inventario(self):
        """Obtém o próximo ID de inventário disponível."""
        connection = None
        cursor = None
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Buscar o maior idInventarioRFID atual
            query = "SELECT MAX(idInventarioRFID) FROM inventariosRFID"
            cursor.execute(query)
            result = cursor.fetchone()
            
            # Se não houver nenhum registro ou o resultado for None, começar com 1
            if result[0] is None:
                return 1
            else:
                return result[0] + 1
                
        except Error as e:
            self.logger.error(f"Erro ao obter próximo ID de inventário: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def criar_inventario(self, dados):
        """
        Cria um novo inventário.
        
        Args:
            dados (dict): Dados do inventário:
                - dataInventario: Data do inventário (opcional, padrão: agora)
                - id_colaborador: ID do colaborador responsável (obrigatório)
                - Observacao: Observações sobre o inventário (opcional)
                
        Returns:
            dict: Resultado da operação com ID do novo inventário
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
            
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Obter próximo ID de inventário
            id_inventario = self._obter_proximo_id_inventario()
            
            # Preparar dados
            dataInventario = dados.get('dataInventario', datetime.now())
            observacao = dados.get('Observacao', '')
            
            # Obter todas as etiquetas ativas
            etiquetas_result = self.gerenciador_etiquetas.obter_etiquetas(
                filtros={'destruida': 0},
                limite=10000  # Buscar todas
            )
            
            if not etiquetas_result['success']:
                return {
                    'success': False,
                    'error': 'Erro ao obter etiquetas ativas'
                }
            
            etiquetas = etiquetas_result['etiquetas']
            total_etiquetas = len(etiquetas)
            
            if total_etiquetas == 0:
                return {
                    'success': False,
                    'error': 'Nenhuma etiqueta ativa encontrada para inventariar'
                }
            
            # Inserir cada etiqueta como uma linha do inventário
            insert_query = """
                INSERT INTO inventariosRFID 
                (idInventarioRFID, dataInventario, id_colaborador, EtiquetaRFID_hex, 
                 Status, Observacao, CodigoLeitor)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            # Inserir todas as etiquetas com status inicial
            for etiqueta in etiquetas:
                valores = (
                    id_inventario,
                    dataInventario,
                    dados['id_colaborador'],
                    etiqueta['EtiquetaRFID_hex'],
                    'Não localizado',
                    observacao,
                    None  # CodigoLeitor inicial vazio
                )
                cursor.execute(insert_query, valores)
            
            connection.commit()  # COMMIT após inserir todas as etiquetas
            
            # Processar leituras dos últimos 6 meses
            localizados = self._processar_leituras_historicas(id_inventario, connection, cursor)
            
            connection.commit()  # COMMIT após processar leituras históricas
            
            # Limpar cache
            self.limpar_cache()
            
            return {
                'success': True,
                'message': 'Inventário criado com sucesso',
                'id_inventario': id_inventario,
                'total_etiquetas': total_etiquetas,
                'etiquetas_localizadas': localizados
            }
            
        except Error as e:
            self.logger.error(f"Erro ao criar inventário: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def _processar_leituras_historicas(self, id_inventario, connection=None, cursor=None):
        """
        Processa leituras históricas dos últimos 6 meses para marcar itens como localizados.
        
        Args:
            id_inventario (int): ID do inventário
            connection: Conexão MySQL (opcional, reutiliza se fornecida)
            cursor: Cursor MySQL (opcional, reutiliza se fornecido)
            
        Returns:
            int: Número de etiquetas localizadas
        """
        fechar_conexao = False
        fechar_cursor = False
        localizados = 0
        
        try:
            # Se não recebeu conexão, criar nova
            if not connection:
                connection = self._get_connection()
                fechar_conexao = True
            
            if not cursor:
                cursor = connection.cursor()
                fechar_cursor = True
            
            # Data de 6 meses atrás
            data_inicio = datetime.now() - timedelta(days=180)
            
            # Buscar etiquetas com leituras nos últimos 6 meses que fazem parte do inventário
            query_update = """
                UPDATE inventariosRFID i
                INNER JOIN (
                    SELECT DISTINCT 
                        l.EtiquetaRFID_hex,
                        l.CodigoLeitor,
                        MAX(l.Horario) as UltimaLeitura
                    FROM leitoresRFID l
                    WHERE l.Horario >= %s AND l.RSSI != 0
                    GROUP BY l.EtiquetaRFID_hex, l.CodigoLeitor
                ) AS leituras ON i.EtiquetaRFID_hex = leituras.EtiquetaRFID_hex
                SET 
                    i.Status = 'Localizado',
                    i.CodigoLeitor = leituras.CodigoLeitor,
                    i.Observacao = CONCAT(i.Observacao, ' | Localizado no BD em: ', 
                                         DATE_FORMAT(leituras.UltimaLeitura, '%%d/%%m/%%Y %%H:%%i'))
                WHERE i.idInventarioRFID = %s AND i.Status = 'Não localizado'
            """
            
            cursor.execute(query_update, (data_inicio, id_inventario))
            localizados = cursor.rowcount
            
            # Se criou a conexão aqui, faz commit
            if fechar_conexao:
                connection.commit()
            
            self.logger.info(f"Processadas {localizados} leituras históricas para inventário {id_inventario}")
            
            return localizados
            
        except Error as e:
            self.logger.error(f"Erro ao processar leituras históricas: {e}")
            if fechar_conexao and connection:
                connection.rollback()
            return 0
        finally:
            if fechar_cursor and cursor:
                cursor.close()
            if fechar_conexao and connection:
                connection.close()
    
    def processar_csv_leituras(self, id_inventario, arquivo_csv):
        """
        Processa arquivo CSV com leituras de leitor móvel.
        
        Args:
            id_inventario (int): ID do inventário
            arquivo_csv: Arquivo CSV ou string com conteúdo CSV
            
        Returns:
            dict: Resultado do processamento
        """
        connection = None
        cursor = None
        etiquetas_processadas = 0
        etiquetas_atualizadas = 0
        erros = []
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Verificar se o inventário existe e está em andamento
            check_query = """
                SELECT COUNT(DISTINCT idInventarioRFID) as existe,
                       COUNT(CASE WHEN Status = 'Finalizado' THEN 1 END) as finalizado
                FROM inventariosRFID
                WHERE idInventarioRFID = %s
            """
            cursor.execute(check_query, (id_inventario,))
            result = cursor.fetchone()
            
            if result[0] == 0:
                return {
                    'success': False,
                    'error': 'Inventário não encontrado'
                }
            
            if result[1] > 0:
                return {
                    'success': False,
                    'error': 'Inventário já foi finalizado'
                }
            
            # Processar CSV
            if isinstance(arquivo_csv, str):
                csv_file = io.StringIO(arquivo_csv)
            else:
                # Se for um arquivo, decodificar para string
                csv_content = arquivo_csv.read()
                if isinstance(csv_content, bytes):
                    csv_content = csv_content.decode('utf-8-sig')  # Remove BOM se presente
                csv_file = io.StringIO(csv_content)
            
            reader = csv.DictReader(csv_file)
            
            # Verificar se tem coluna EPC
            if 'EPC' not in reader.fieldnames:
                return {
                    'success': False,
                    'error': 'Arquivo CSV deve conter coluna "EPC"'
                }
            
            # Processar cada linha
            for row in reader:
                etiquetas_processadas += 1
                epc = row.get('EPC', '').strip()
                
                if not epc:
                    erros.append(f"Linha {etiquetas_processadas}: EPC vazio")
                    continue
                
                # Atualizar etiqueta se existir no inventário e ainda não foi localizada
                update_query = """
                    UPDATE inventariosRFID
                    SET Status = 'Localizado',
                        CodigoLeitor = 'MOBILE',
                        Observacao = CONCAT(Observacao, ' | Localizado via leitor móvel em: ', 
                                          DATE_FORMAT(NOW(), '%%d/%%m/%%Y %%H:%%i'))
                    WHERE idInventarioRFID = %s 
                        AND EtiquetaRFID_hex = %s 
                        AND Status = 'Não localizado'
                """
                
                cursor.execute(update_query, (id_inventario, epc))
                
                if cursor.rowcount > 0:
                    etiquetas_atualizadas += 1
                else:
                    # Verificar se a etiqueta existe no inventário
                    check_etiqueta = """
                        SELECT Status 
                        FROM inventariosRFID 
                        WHERE idInventarioRFID = %s AND EtiquetaRFID_hex = %s
                    """
                    cursor.execute(check_etiqueta, (id_inventario, epc))
                    result = cursor.fetchone()
                    
                    if not result:
                        erros.append(f"EPC {epc}: não encontrado no inventário")
                    elif result[0] == 'Localizado':
                        # Etiqueta já foi localizada anteriormente
                        pass
            
            connection.commit()  # COMMIT após processar todas as etiquetas do CSV
            
            # Limpar cache
            self.limpar_cache()
            
            return {
                'success': True,
                'message': f'CSV processado com sucesso',
                'etiquetas_processadas': etiquetas_processadas,
                'etiquetas_atualizadas': etiquetas_atualizadas,
                'erros': erros if erros else None
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao processar CSV: {e}")
            return {
                'success': False,
                'error': str(e),
                'etiquetas_processadas': etiquetas_processadas,
                'etiquetas_atualizadas': etiquetas_atualizadas
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def obter_inventarios(self, filtros=None, limite=100, offset=0, force_refresh=False):
        """
        Obtém lista de inventários com filtros opcionais.
        
        Args:
            filtros (dict): Dicionário com filtros
            limite (int): Número máximo de registros
            offset (int): Deslocamento para paginação
            force_refresh (bool): Força atualização ignorando o cache
            
        Returns:
            dict: Resultado com inventários e total
        """
        cache_params = {
            'filtros': filtros or {},
            'limite': limite,
            'offset': offset
        }
        cache_key = self._get_cache_key('inventarios', cache_params)
        
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
            
            # Query para obter inventários agrupados
            base_query = """
                SELECT 
                    i.idInventarioRFID,
                    MIN(i.dataInventario) as dataInventario,
                    i.id_colaborador,
                    MIN(i.Observacao) as Observacao,
                    CASE 
                        WHEN COUNT(CASE WHEN i.Status = 'Finalizado' THEN 1 END) > 0 THEN 'Finalizado'
                        ELSE 'Em andamento'
                    END as Status,
                    COUNT(*) as total_itens,
                    COUNT(CASE WHEN i.Status = 'Localizado' THEN 1 END) as itens_localizados
                FROM inventariosRFID i
                WHERE 1=1
            """
            
            where_conditions = []
            params = []
            
            if filtros:
                if filtros.get('status'):
                    if filtros['status'] == 'Finalizado':
                        where_conditions.append("EXISTS (SELECT 1 FROM inventariosRFID i2 WHERE i2.idInventarioRFID = i.idInventarioRFID AND i2.Status = 'Finalizado')")
                    else:
                        where_conditions.append("NOT EXISTS (SELECT 1 FROM inventariosRFID i2 WHERE i2.idInventarioRFID = i.idInventarioRFID AND i2.Status = 'Finalizado')")
                
                if filtros.get('id_colaborador'):
                    where_conditions.append("i.id_colaborador = %s")
                    params.append(filtros['id_colaborador'])
                
                if filtros.get('data_inicio'):
                    where_conditions.append("DATE(i.dataInventario) >= %s")
                    params.append(filtros['data_inicio'])
                
                if filtros.get('data_fim'):
                    where_conditions.append("DATE(i.dataInventario) <= %s")
                    params.append(filtros['data_fim'])
            
            if where_conditions:
                base_query += " AND " + " AND ".join(where_conditions)
            
            base_query += " GROUP BY i.idInventarioRFID, i.id_colaborador"
            
            # Contar total
            count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']
            
            # Obter dados com paginação
            data_query = base_query + " ORDER BY MIN(i.dataInventario) DESC LIMIT %s OFFSET %s"
            params.extend([limite, offset])
            
            cursor.execute(data_query, params)
            inventarios = cursor.fetchall()
            
            # Processar dados
            for inv in inventarios:
                if inv['dataInventario']:
                    inv['dataInventario_formatada'] = inv['dataInventario'].strftime('%d/%m/%Y %H:%M')
                
                # Calcular percentual
                if inv['total_itens'] > 0:
                    inv['percentual_localizado'] = round((inv['itens_localizados'] / inv['total_itens']) * 100, 2)
                else:
                    inv['percentual_localizado'] = 0
            
            result = {
                'success': True,
                'inventarios': inventarios,
                'total': total,
                'limite': limite,
                'offset': offset,
                'from_cache': False
            }
            
            self._set_cache(cache_key, result)
            
            return result
            
        except Error as e:
            self.logger.error(f"Erro ao obter inventários: {e}")
            return {
                'success': False,
                'error': str(e),
                'inventarios': [],
                'total': 0,
                'from_cache': False
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def obter_detalhes_inventario(self, id_inventario):
        """
        Obtém detalhes completos de um inventário específico.
        
        Args:
            id_inventario (int): ID do inventário
            
        Returns:
            dict: Detalhes do inventário
        """
        connection = None
        cursor = None
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Obter dados básicos do inventário
            query_info = """
                SELECT 
                    idInventarioRFID,
                    MIN(dataInventario) as dataInventario,
                    id_colaborador,
                    MIN(Observacao) as Observacao,
                    CASE 
                        WHEN COUNT(CASE WHEN Status = 'Finalizado' THEN 1 END) > 0 THEN 'Finalizado'
                        ELSE 'Em andamento'
                    END as Status
                FROM inventariosRFID
                WHERE idInventarioRFID = %s
                GROUP BY idInventarioRFID, id_colaborador
            """
            
            cursor.execute(query_info, (id_inventario,))
            inventario = cursor.fetchone()
            
            if not inventario:
                return {
                    'success': False,
                    'error': 'Inventário não encontrado'
                }
            
            # Obter itens do inventário com informações das etiquetas
            query_itens = """
                SELECT 
                    i.EtiquetaRFID_hex,
                    i.Status,
                    i.CodigoLeitor,
                    i.Observacao as ObservacaoItem,
                    e.Descricao as DescricaoEtiqueta
                FROM inventariosRFID i
                LEFT JOIN etiquetasRFID e ON i.EtiquetaRFID_hex = e.EtiquetaRFID_hex
                WHERE i.idInventarioRFID = %s
                ORDER BY i.Status DESC, e.Descricao
            """
            
            cursor.execute(query_itens, (id_inventario,))
            itens = cursor.fetchall()
            
            # Processar data
            if inventario['dataInventario']:
                inventario['dataInventario_formatada'] = inventario['dataInventario'].strftime('%d/%m/%Y %H:%M')
            
            # Estatísticas
            total_itens = len(itens)
            itens_localizados = sum(1 for item in itens if item['Status'] == 'Localizado')
            
            return {
                'success': True,
                'inventario': inventario,
                'itens': itens,
                'estatisticas': {
                    'total_itens': total_itens,
                    'itens_localizados': itens_localizados,
                    'itens_nao_localizados': total_itens - itens_localizados,
                    'percentual_localizado': round((itens_localizados / total_itens * 100) if total_itens > 0 else 0, 2)
                }
            }
            
        except Error as e:
            self.logger.error(f"Erro ao obter detalhes do inventário: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def finalizar_inventario(self, id_inventario):
        """
        Finaliza um inventário em andamento.
        
        Args:
            id_inventario (int): ID do inventário
            
        Returns:
            dict: Resultado da operação
        """
        connection = None
        cursor = None
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Verificar se o inventário existe e está em andamento
            check_query = """
                SELECT COUNT(*) as existe,
                       COUNT(CASE WHEN Status = 'Finalizado' THEN 1 END) as finalizado
                FROM inventariosRFID
                WHERE idInventarioRFID = %s
            """
            
            cursor.execute(check_query, (id_inventario,))
            result = cursor.fetchone()
            
            if result[0] == 0:
                return {
                    'success': False,
                    'error': 'Inventário não encontrado'
                }
            
            if result[1] > 0:
                return {
                    'success': False,
                    'error': 'Inventário já foi finalizado'
                }
            
            # Atualizar todos os registros do inventário para Finalizado
            update_query = """
                UPDATE inventariosRFID
                SET Status = 'Finalizado'
                WHERE idInventarioRFID = %s
            """
            
            cursor.execute(update_query, (id_inventario,))
            connection.commit()  # COMMIT necessário para persistir a mudança
            
            # Limpar cache
            self.limpar_cache()
            
            return {
                'success': True,
                'message': 'Inventário finalizado com sucesso'
            }
            
        except Error as e:
            self.logger.error(f"Erro ao finalizar inventário: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()