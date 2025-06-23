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

class GerenciadorInventariosRFID:
    """Gerenciador simplificado para operações de inventário RFID."""
    
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
        
        self.logger.info("Gerenciador de Inventários RFID inicializado (versão simplificada)")
    
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
        Cria um novo inventário (versão simplificada).
        
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
            
            # Inserir inventário (sem especificar o ID para usar AUTO_INCREMENT)
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
            
            # Limpar cache
            self.limpar_cache()
            
            self.logger.info(f"Inventário criado com sucesso - ID: {id_inventario}")
            
            return {
                'success': True,
                'message': 'Inventário criado com sucesso',
                'id_inventario': id_inventario,
                'info': 'Sistema simplificado - registre os itens manualmente'
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
                    idInventarioRFID,
                    dataInventario,
                    id_colaborador,
                    Observacao,
                    Status
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
            
            # Processar dados (simulando contagem de itens)
            for inv in inventarios:
                if inv['dataInventario']:
                    inv['dataInventario_formatada'] = inv['dataInventario'].strftime('%d/%m/%Y %H:%M')
                
                # Valores simulados já que não temos tabela de itens
                inv['total_itens'] = 0
                inv['itens_localizados'] = 0
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
        Obtém detalhes de um inventário específico.
        
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
            
            # Processar data
            if inventario['dataInventario']:
                inventario['dataInventario_formatada'] = inventario['dataInventario'].strftime('%d/%m/%Y %H:%M')
            
            return {
                'success': True,
                'inventario': inventario,
                'itens': [],  # Sistema simplificado sem itens
                'estatisticas': {
                    'total_itens': 0,
                    'itens_localizados': 0,
                    'itens_nao_localizados': 0,
                    'percentual_localizado': 0
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
    
    def processar_csv_leituras(self, id_inventario, arquivo_csv):
        """
        Método simplificado - apenas retorna sucesso.
        
        Args:
            id_inventario (int): ID do inventário
            arquivo_csv: Arquivo CSV
            
        Returns:
            dict: Resultado do processamento
        """
        return {
            'success': True,
            'message': 'Sistema simplificado - funcionalidade não implementada',
            'etiquetas_processadas': 0,
            'etiquetas_atualizadas': 0,
            'erros': ['Sistema não possui tabela de itens de inventário']
        }