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
            
            # Preparar dados
            dataInventario = dados.get('dataInventario', datetime.now())
            observacao = dados.get('Observacao', '')
            
            # Inserir inventário
            insert_query = """
                INSERT INTO inventariosRFID 
                (dataInventario, id_colaborador, Observacao, Status)
                VALUES (%s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (
                dataInventario,
                dados['id_colaborador'],
                observacao,
                'Em andamento'
            ))
            
            id_inventario = cursor.lastrowid
            
            # Obter todas as etiquetas ativas
            etiquetas_result = self.gerenciador_etiquetas.obter_etiquetas(
                filtros={'destruida': 0},
                limite=10000  # Buscar todas
            )
            
            if etiquetas_result['success']:
                # Inserir todas as etiquetas como não localizadas inicialmente
                for etiqueta in etiquetas_result['etiquetas']:
                    insert_item_query = """
                        INSERT INTO inventariosRFID 
                        (idInventarioRFID, EtiquetaRFID_hex, Status, CodigoLeitor, Observacao)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    
                    cursor.execute(insert_item_query, (
                        id_inventario,
                        etiqueta['EtiquetaRFID_hex'],
                        'Não localizado',
                        None,
                        None
                    ))
            
            # Processar leituras dos últimos 6 meses
            self._processar_leituras_historicas(id_inventario)
            
            # Limpar cache
            self.limpar_cache()
            
            return {
                'success': True,
                'message': 'Inventário criado com sucesso',
                'id_inventario': id_inventario,
                'total_etiquetas': len(etiquetas_result['etiquetas']) if etiquetas_result['success'] else 0
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
    
    def _processar_leituras_historicas(self, id_inventario):
        """
        Processa leituras históricas dos últimos 6 meses para marcar itens como localizados.
        
        Args:
            id_inventario (int): ID do inventário
        """
        connection = None
        cursor = None
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Data de 6 meses atrás
            data_inicio = datetime.now() - timedelta(days=180)
            
            # Buscar etiquetas com leituras nos últimos 6 meses
            query_leituras = """
                SELECT DISTINCT 
                    l.EtiquetaRFID_hex,
                    l.CodigoLeitor,
                    MAX(l.Horario) as UltimaLeitura
                FROM leitoresRFID l
                INNER JOIN inventariosRFID i ON l.EtiquetaRFID_hex = i.EtiquetaRFID_hex
                WHERE i.idInventarioRFID = %s 
                    AND l.Horario >= %s
                    AND l.RSSI != 0
                GROUP BY l.EtiquetaRFID_hex, l.CodigoLeitor
            """
            
            cursor.execute(query_leituras, (id_inventario, data_inicio))
            leituras = cursor.fetchall()
            
            # Atualizar status dos itens encontrados
            for leitura in leituras:
                update_query = """
                    UPDATE inventariosRFID
                    SET Status = %s,
                        CodigoLeitor = %s,
                        Observacao = %s,
                        dataInventario = %s
                    WHERE idInventarioRFID = %s 
                        AND EtiquetaRFID_hex = %s
                        AND Status = 'Não localizado'
                """
                
                observacao = f"Localizado no BD (Última leitura: {leitura[2].strftime('%d/%m/%Y %H:%M')})"
                
                cursor.execute(update_query, (
                    'Localizado',
                    leitura[1],  # CodigoLeitor
                    observacao,
                    leitura[2],  # UltimaLeitura como dataInventario
                    id_inventario,
                    leitura[0]   # EtiquetaRFID_hex
                ))
            
            self.logger.info(f"Processadas {len(leituras)} leituras históricas para inventário {id_inventario}")
            
        except Error as e:
            self.logger.error(f"Erro ao processar leituras históricas: {e}")
        finally:
            if cursor:
                cursor.close()
            if connection:
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
                
                # Verificar se a etiqueta existe no inventário
                check_query = """
                    SELECT Status
                    FROM inventariosRFID
                    WHERE idInventarioRFID = %s AND EtiquetaRFID_hex = %s
                """
                
                cursor.execute(check_query, (id_inventario, epc))
                result = cursor.fetchone()
                
                if not result:
                    erros.append(f"EPC {epc}: não encontrado no inventário")
                    continue
                
                # Atualizar apenas se ainda não foi localizado
                if result[0] == 'Não localizado':
                    update_query = """
                        UPDATE inventariosRFID
                        SET Status = %s,
                            CodigoLeitor = %s,
                            Observacao = %s,
                            dataInventario = %s
                        WHERE idInventarioRFID = %s AND EtiquetaRFID_hex = %s
                    """
                    
                    cursor.execute(update_query, (
                        'Localizado',
                        'MOBILE',  # Indicar que foi leitor móvel
                        'Localizado via leitor móvel',
                        datetime.now(),
                        id_inventario,
                        epc
                    ))
                    
                    etiquetas_atualizadas += 1
            
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
            
            # Query base
            base_query = """
                SELECT 
                    i.idInventarioRFID,
                    i.dataInventario,
                    i.id_colaborador,
                    i.Observacao,
                    i.Status,
                    COUNT(DISTINCT ii.EtiquetaRFID_hex) as total_itens,
                    SUM(CASE WHEN ii.Status = 'Localizado' THEN 1 ELSE 0 END) as itens_localizados
                FROM inventariosRFID i
                LEFT JOIN inventariosRFID ii ON i.idInventarioRFID = ii.idInventarioRFID
                WHERE 1=1
            """
            
            where_conditions = []
            params = []
            
            if filtros:
                if filtros.get('status'):
                    where_conditions.append("i.Status = %s")
                    params.append(filtros['status'])
                
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
            
            base_query += " GROUP BY i.idInventarioRFID"
            
            # Contar total
            count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']
            
            # Obter dados com paginação
            data_query = base_query + " ORDER BY i.dataInventario DESC LIMIT %s OFFSET %s"
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
            
            # Obter dados do inventário
            query_inventario = """
                SELECT 
                    idInventarioRFID,
                    dataInventario,
                    id_colaborador,
                    Observacao,
                    Status
                FROM inventariosRFID
                WHERE idInventarioRFID = %s
            """
            
            cursor.execute(query_inventario, (id_inventario,))
            inventario = cursor.fetchone()
            
            if not inventario:
                return {
                    'success': False,
                    'error': 'Inventário não encontrado'
                }
            
            # Obter itens do inventário
            query_itens = """
                SELECT 
                    ii.EtiquetaRFID_hex,
                    ii.Status,
                    ii.CodigoLeitor,
                    ii.Observacao as ObservacaoItem,
                    ii.dataInventario as dataLocalizacao,
                    e.Descricao as DescricaoEtiqueta
                FROM inventariosRFID ii
                LEFT JOIN etiquetasRFID e ON ii.EtiquetaRFID_hex = e.EtiquetaRFID_hex
                WHERE ii.idInventarioRFID = %s
                ORDER BY ii.Status DESC, e.Descricao
            """
            
            cursor.execute(query_itens, (id_inventario,))
            itens = cursor.fetchall()
            
            # Processar datas
            if inventario['dataInventario']:
                inventario['dataInventario_formatada'] = inventario['dataInventario'].strftime('%d/%m/%Y %H:%M')
            
            for item in itens:
                if item['dataLocalizacao']:
                    item['dataLocalizacao_formatada'] = item['dataLocalizacao'].strftime('%d/%m/%Y %H:%M')
            
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
                SELECT Status
                FROM inventariosRFID
                WHERE idInventarioRFID = %s
            """
            
            cursor.execute(check_query, (id_inventario,))
            result = cursor.fetchone()
            
            if not result:
                return {
                    'success': False,
                    'error': 'Inventário não encontrado'
                }
            
            if result[0] != 'Em andamento':
                return {
                    'success': False,
                    'error': 'Inventário já foi finalizado'
                }
            
            # Atualizar status
            update_query = """
                UPDATE inventariosRFID
                SET Status = %s
                WHERE idInventarioRFID = %s
            """
            
            cursor.execute(update_query, ('Finalizado', id_inventario))
            
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