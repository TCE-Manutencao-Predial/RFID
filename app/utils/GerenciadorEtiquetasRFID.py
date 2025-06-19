# app/utils/GerenciadorEtiquetasRFID.py
import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime, timedelta
from ..config import MYSQL_CONFIG
import json
import hashlib

class GerenciadorEtiquetasRFID:
    """Gerenciador para operações com etiquetas RFID no MySQL com sistema de cache."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Retorna a instância única do gerenciador (Singleton)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Inicializa o gerenciador."""
        if GerenciadorEtiquetasRFID._instance is not None:
            raise Exception("Use get_instance() para obter a instância")
        
        self.logger = logging.getLogger('controlerfid.gerenciador')
        self.config = MYSQL_CONFIG
        
        # Sistema de cache
        self.cache = {}
        self.cache_timeout = timedelta(minutes=5)  # Cache válido por 5 minutos
        
        self.logger.info("Gerenciador de Etiquetas RFID inicializado com cache")
    
    def _get_cache_key(self, prefix, params=None):
        """Gera uma chave única para o cache baseada nos parâmetros."""
        if params:
            # Criar hash dos parâmetros para a chave
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
                # Cache expirado, remover
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
    
    def obter_etiquetas(self, filtros=None, limite=100, offset=0, force_refresh=False):
        """
        Obtém lista de etiquetas com filtros opcionais.
        
        Args:
            filtros (dict): Dicionário com filtros (etiqueta, descricao, destruida)
            limite (int): Número máximo de registros
            offset (int): Deslocamento para paginação
            force_refresh (bool): Força atualização ignorando o cache
            
        Returns:
            dict: Resultado com etiquetas e total
        """
        # Gerar chave do cache
        cache_params = {
            'filtros': filtros or {},
            'limite': limite,
            'offset': offset
        }
        cache_key = self._get_cache_key('etiquetas', cache_params)
        
        # Verificar cache primeiro (a menos que force_refresh seja True)
        if not force_refresh:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result
        
        total = 0
        etiquetas = []
        
        try:
            # Construir query base
            where_conditions = []
            params = []
            
            if filtros:
                if filtros.get('etiqueta'):
                    where_conditions.append("EtiquetaRFID_hex LIKE %s")
                    params.append(f"%{filtros['etiqueta']}%")
                
                if filtros.get('descricao'):
                    where_conditions.append("Descricao LIKE %s")
                    params.append(f"%{filtros['descricao']}%")
                
                if filtros.get('destruida') is not None:
                    # Filtrar por status baseado no campo de data
                    if filtros['destruida'] == 0:  # Ativas
                        where_conditions.append("Destruida IS NULL")
                    elif filtros['destruida'] == 1:  # Destruídas
                        where_conditions.append("Destruida IS NOT NULL")
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # PRIMEIRA CONEXÃO: Obter o total
            connection1 = None
            cursor1 = None
            try:
                connection1 = self._get_connection()
                cursor1 = connection1.cursor(dictionary=True)
                
                count_query = f"SELECT COUNT(*) as total FROM etiquetasRFID WHERE {where_clause}"
                cursor1.execute(count_query, params)
                result = cursor1.fetchone()
                total = result['total'] if result and 'total' in result else 0
                
            except Exception as e:
                self.logger.error(f"Erro ao contar registros: {e}")
                raise
            finally:
                if cursor1:
                    cursor1.close()
                if connection1:
                    connection1.close()
            
            # SEGUNDA CONEXÃO: Obter os registros
            connection2 = None
            cursor2 = None
            try:
                connection2 = self._get_connection()
                cursor2 = connection2.cursor(dictionary=True)
                
                data_query = f"""
                    SELECT 
                        id_listaEtiquetasRFID,
                        EtiquetaRFID_hex,
                        Descricao,
                        Destruida
                    FROM etiquetasRFID
                    WHERE {where_clause}
                    ORDER BY id_listaEtiquetasRFID DESC
                    LIMIT %s OFFSET %s
                """
                
                # Adicionar limite e offset aos parâmetros
                query_params = params.copy()
                query_params.extend([limite, offset])
                
                cursor2.execute(data_query, query_params)
                etiquetas = cursor2.fetchall()
                
            except Exception as e:
                self.logger.error(f"Erro ao buscar registros: {e}")
                raise
            finally:
                if cursor2:
                    cursor2.close()
                if connection2:
                    connection2.close()
            
            result = {
                'success': True,
                'etiquetas': etiquetas,
                'total': total,
                'limite': limite,
                'offset': offset,
                'from_cache': False
            }
            
            # Armazenar no cache
            self._set_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao obter etiquetas: {e}")
            return {
                'success': False,
                'error': str(e),
                'etiquetas': [],
                'total': 0,
                'from_cache': False
            }
    
    def obter_etiqueta_por_id(self, id_etiqueta):
        """
        Obtém uma etiqueta específica pelo ID.
        
        Args:
            id_etiqueta (int): ID da etiqueta
            
        Returns:
            dict: Dados da etiqueta ou None
        """
        # Verificar cache primeiro
        cache_key = self._get_cache_key(f'etiqueta_{id_etiqueta}')
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        connection = None
        cursor = None
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT 
                    id_listaEtiquetasRFID,
                    EtiquetaRFID_hex,
                    Foto,
                    Descricao,
                    Destruida
                FROM etiquetasRFID
                WHERE id_listaEtiquetasRFID = %s
            """
            
            cursor.execute(query, (id_etiqueta,))
            etiqueta = cursor.fetchone()
            
            # Armazenar no cache se encontrado
            if etiqueta:
                self._set_cache(cache_key, etiqueta)
            
            return etiqueta
            
        except Error as e:
            self.logger.error(f"Erro ao obter etiqueta {id_etiqueta}: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def atualizar_etiqueta(self, id_etiqueta, dados):
        """
        Atualiza dados de uma etiqueta.
        
        Args:
            id_etiqueta (int): ID da etiqueta
            dados (dict): Dados para atualizar
            
        Returns:
            dict: Resultado da operação
        """
        connection = None
        cursor = None
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Construir query de atualização
            campos = []
            valores = []
            
            if 'descricao' in dados:
                campos.append("Descricao = %s")
                valores.append(dados['descricao'])
            
            if 'destruida' in dados:
                campos.append("Destruida = %s")
                valores.append(dados['destruida'])
            
            if not campos:
                return {
                    'success': False,
                    'error': 'Nenhum campo para atualizar'
                }
            
            query = f"UPDATE etiquetasRFID SET {', '.join(campos)} WHERE id_listaEtiquetasRFID = %s"
            valores.append(id_etiqueta)
            
            cursor.execute(query, valores)
            
            # Limpar cache após atualização
            self.limpar_cache()
            
            return {
                'success': True,
                'message': 'Etiqueta atualizada com sucesso',
                'affected_rows': cursor.rowcount
            }
            
        except Error as e:
            self.logger.error(f"Erro ao atualizar etiqueta {id_etiqueta}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def obter_estatisticas(self, force_refresh=False):
        """
        Obtém estatísticas gerais das etiquetas.
        
        Args:
            force_refresh (bool): Força atualização ignorando o cache
            
        Returns:
            dict: Estatísticas
        """
        cache_key = 'estatisticas'
        
        # Verificar cache primeiro
        if not force_refresh:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                cached_result['from_cache'] = True
                return cached_result
        
        try:
            total = 0
            destruidas = 0
            
            # Primeira conexão: total de etiquetas
            connection1 = None
            cursor1 = None
            try:
                connection1 = self._get_connection()
                cursor1 = connection1.cursor(dictionary=True)
                
                cursor1.execute("SELECT COUNT(*) as total FROM etiquetasRFID")
                result = cursor1.fetchone()
                total = result['total'] if result and 'total' in result else 0
                
            finally:
                if cursor1:
                    cursor1.close()
                if connection1:
                    connection1.close()
            
            # Segunda conexão: total de destruídas
            connection2 = None
            cursor2 = None
            try:
                connection2 = self._get_connection()
                cursor2 = connection2.cursor(dictionary=True)
                
                cursor2.execute("SELECT COUNT(*) as destruidas FROM etiquetasRFID WHERE Destruida = 1")
                result = cursor2.fetchone()
                destruidas = result['destruidas'] if result and 'destruidas' in result else 0
                
            finally:
                if cursor2:
                    cursor2.close()
                if connection2:
                    connection2.close()
            
            # Calcular ativas
            ativas = total - destruidas
            
            result = {
                'success': True,
                'estatisticas': {
                    'total': total,
                    'ativas': ativas,
                    'destruidas': destruidas,
                    'percentual_ativas': round((ativas / total * 100) if total > 0 else 0, 2)
                },
                'from_cache': False
            }
            
            # Armazenar no cache
            self._set_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas: {e}")
            return {
                'success': False,
                'error': str(e),
                'estatisticas': {
                    'total': 0,
                    'ativas': 0,
                    'destruidas': 0,
                    'percentual_ativas': 0
                },
                'from_cache': False
            }