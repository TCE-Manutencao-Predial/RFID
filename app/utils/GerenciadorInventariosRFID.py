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
            
            # Criar lista de etiquetas como JSON
            lista_etiquetas = [{'hex': e['EtiquetaRFID_hex'], 'status': 'nao_localizado'} 
                             for e in etiquetas]
            
            # Processar leituras dos últimos 6 meses
            localizados = self._processar_leituras_historicas(lista_etiquetas)
            
            # Calcular estatísticas
            total_localizados = sum(1 for item in lista_etiquetas if item['status'] == 'localizado')
            
            # Inserir inventário - NÃO especificar o id pois é auto_increment
            insert_query = """
                INSERT INTO inventariosRFID 
                (dataInventario, id_colaborador, Observacao, Status, itens_json, 
                 total_itens, itens_localizados)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (
                dataInventario,
                dados['id_colaborador'],
                observacao,
                'Em andamento',
                json.dumps(lista_etiquetas),
                total_etiquetas,
                total_localizados
            ))
            
            id_inventario = cursor.lastrowid
            
            # Limpar cache
            self.limpar_cache()
            
            return {
                'success': True,
                'message': 'Inventário criado com sucesso',
                'id_inventario': id_inventario,
                'total_etiquetas': total_etiquetas,
                'etiquetas_localizadas': total_localizados
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
    
    def _processar_leituras_historicas(self, lista_etiquetas):
        """
        Processa leituras históricas dos últimos 6 meses para marcar itens como localizados.
        
        Args:
            lista_etiquetas (list): Lista de dicionários com etiquetas
            
        Returns:
            int: Número de etiquetas localizadas
        """
        try:
            # Data de 6 meses atrás
            data_inicio = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d %H:%M:%S')
            
            # Criar mapa para busca rápida
            etiquetas_map = {item['hex']: item for item in lista_etiquetas}
            
            # Buscar leituras dos últimos 6 meses
            resultado_leituras = self.gerenciador_leitores.obter_leituras(
                filtros={
                    'horario_inicio': data_inicio,
                    'horario_fim': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                },
                limite=10000  # Buscar muitas leituras
            )
            
            if resultado_leituras['success']:
                # Processar leituras únicas por etiqueta
                etiquetas_lidas = set()
                
                for leitura in resultado_leituras['leituras']:
                    etiqueta_hex = leitura.get('etiqueta_hex')
                    if etiqueta_hex and etiqueta_hex in etiquetas_map:
                        etiquetas_lidas.add(etiqueta_hex)
                        etiquetas_map[etiqueta_hex]['status'] = 'localizado'
                        etiquetas_map[etiqueta_hex]['data_leitura'] = leitura.get('horario_formatado', '')
                        etiquetas_map[etiqueta_hex]['codigo_leitor'] = leitura.get('codigo_leitor', '')
                
                return len(etiquetas_lidas)
            
        except Exception as e:
            self.logger.error(f"Erro ao processar leituras históricas: {e}")
        
        return 0
    
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
            cursor = connection.cursor(dictionary=True)
            
            # Buscar inventário
            query = """
                SELECT id, itens_json, Status, total_itens, itens_localizados
                FROM inventariosRFID
                WHERE id = %s
            """
            cursor.execute(query, (id_inventario,))
            inventario = cursor.fetchone()
            
            if not inventario:
                return {
                    'success': False,
                    'error': 'Inventário não encontrado'
                }
            
            if inventario['Status'] != 'Em andamento':
                return {
                    'success': False,
                    'error': 'Inventário já foi finalizado'
                }
            
            # Carregar itens do JSON
            itens = json.loads(inventario['itens_json'])
            itens_map = {item['hex']: item for item in itens}
            
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
                if epc in itens_map:
                    if itens_map[epc]['status'] == 'nao_localizado':
                        itens_map[epc]['status'] = 'localizado'
                        itens_map[epc]['data_leitura'] = datetime.now().strftime('%d/%m/%Y %H:%M')
                        itens_map[epc]['codigo_leitor'] = 'MOBILE'
                        etiquetas_atualizadas += 1
                else:
                    erros.append(f"EPC {epc}: não faz parte deste inventário")
            
            # Atualizar inventário no banco
            total_localizados = sum(1 for item in itens if item['status'] == 'localizado')
            
            update_query = """
                UPDATE inventariosRFID
                SET itens_json = %s,
                    itens_localizados = %s
                WHERE id = %s
            """
            
            cursor.execute(update_query, (
                json.dumps(itens),
                total_localizados,
                id_inventario
            ))
            
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
                    id as idInventarioRFID,
                    dataInventario,
                    id_colaborador,
                    Observacao,
                    Status,
                    total_itens,
                    itens_localizados
                FROM inventariosRFID
                WHERE 1=1
            """
            
            where_conditions = []
            params = []
            
            if filtros:
                if filtros.get('status'):
                    where_conditions.append("Status = %s")
                    params.append(filtros['status'])
                
                if filtros.get('id_colaborador'):
                    where_conditions.append("id_colaborador = %s")
                    params.append(filtros['id_colaborador'])
                
                if filtros.get('data_inicio'):
                    where_conditions.append("DATE(dataInventario) >= %s")
                    params.append(filtros['data_inicio'])
                
                if filtros.get('data_fim'):
                    where_conditions.append("DATE(dataInventario) <= %s")
                    params.append(filtros['data_fim'])
            
            if where_conditions:
                base_query += " AND " + " AND ".join(where_conditions)
            
            # Contar total
            count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']
            
            # Obter dados com paginação
            data_query = base_query + " ORDER BY dataInventario DESC LIMIT %s OFFSET %s"
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
                    id as idInventarioRFID,
                    dataInventario,
                    id_colaborador,
                    Observacao,
                    Status,
                    itens_json,
                    total_itens,
                    itens_localizados
                FROM inventariosRFID
                WHERE id = %s
            """
            
            cursor.execute(query_inventario, (id_inventario,))
            inventario = cursor.fetchone()
            
            if not inventario:
                return {
                    'success': False,
                    'error': 'Inventário não encontrado'
                }
            
            # Processar itens do JSON
            itens = json.loads(inventario['itens_json'])
            
            # Buscar descrições das etiquetas
            etiquetas_hex = [item['hex'] for item in itens]
            if etiquetas_hex:
                # Buscar descrições em lotes
                placeholders = ','.join(['%s'] * len(etiquetas_hex))
                query_descricoes = f"""
                    SELECT EtiquetaRFID_hex, Descricao
                    FROM etiquetasRFID
                    WHERE EtiquetaRFID_hex IN ({placeholders})
                """
                cursor.execute(query_descricoes, etiquetas_hex)
                
                # Criar mapa de descrições
                descricoes = {row['EtiquetaRFID_hex']: row['Descricao'] 
                             for row in cursor.fetchall()}
                
                # Adicionar descrições aos itens
                for item in itens:
                    item['EtiquetaRFID_hex'] = item['hex']
                    item['Status'] = 'Localizado' if item['status'] == 'localizado' else 'Não localizado'
                    item['DescricaoEtiqueta'] = descricoes.get(item['hex'], 'Sem descrição')
                    item['ObservacaoItem'] = item.get('data_leitura', '')
                    if item.get('codigo_leitor'):
                        item['ObservacaoItem'] += f" - Leitor: {item['codigo_leitor']}"
            
            # Processar data
            if inventario['dataInventario']:
                inventario['dataInventario_formatada'] = inventario['dataInventario'].strftime('%d/%m/%Y %H:%M')
            
            # Estatísticas
            percentual = round((inventario['itens_localizados'] / inventario['total_itens'] * 100) 
                             if inventario['total_itens'] > 0 else 0, 2)
            
            return {
                'success': True,
                'inventario': inventario,
                'itens': itens,
                'estatisticas': {
                    'total_itens': inventario['total_itens'],
                    'itens_localizados': inventario['itens_localizados'],
                    'itens_nao_localizados': inventario['total_itens'] - inventario['itens_localizados'],
                    'percentual_localizado': percentual
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
                WHERE id = %s
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
                WHERE id = %s
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