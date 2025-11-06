# app/utils/GerenciadorPingRFID.py
import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime, timedelta
from ..config import MYSQL_CONFIG
import json
import hashlib
import re

class GerenciadorPingRFID:
    """Gerenciador para operações com registros da tabela pingsRFID."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Retorna a instância única do gerenciador (Singleton)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Inicializa o gerenciador."""
        if GerenciadorPingRFID._instance is not None:
            raise Exception("Use get_instance() para obter a instância")
        
        self.logger = logging.getLogger('controlerfid.ping')
        self.config = MYSQL_CONFIG
        
        # Sistema de cache
        self.cache = {}
        self.cache_timeout = timedelta(minutes=3)
        
        self._cache = {}
        self._cache_timeout = 180  # 3 minutos
    
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
    
    def _converter_horario_para_sql(self, horario):
        """
        Converte horário de diversos formatos para formato SQL.
        
        Args:
            horario: String com horário em formato HTTP (GMT) ou SQL
            
        Returns:
            str: Horário em formato SQL (YYYY-MM-DD HH:MM:SS)
        """
        from email.utils import parsedate_to_datetime
        
        try:
            # Se já está em formato SQL, retornar direto
            if isinstance(horario, str) and '-' in horario and ':' in horario:
                # Formato: 2025-10-31 11:32:26 ou 2025-10-31T11:32:26
                return horario.replace('T', ' ').split('.')[0]  # Remove microsegundos se houver
            
            # Se está em formato HTTP/GMT: "Fri, 31 Oct 2025 11:32:26 GMT"
            if 'GMT' in str(horario) or ',' in str(horario):
                dt = parsedate_to_datetime(horario)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Fallback: retornar como está
            return str(horario)
            
        except Exception as e:
            self.logger.warning(f"Erro ao converter horário '{horario}': {e}. Usando como está.")
            return str(horario)
    
    def _get_connection(self):
        """Cria e retorna uma conexão com o MySQL com timeouts agressivos."""
        try:
            connection_params = {
                'host': self.config['host'],
                'database': self.config['database'],
                'user': self.config['user'],
                'password': self.config['password'],
                'connection_timeout': min(self.config.get('connection_timeout', 10), 5),  # Max 5 segundos
                'autocommit': True,
                'use_pure': False  # Usar driver C mais rápido
            }
            
            # Desabilita verificação SSL apenas para domínios tce.go.gov.br
            if 'tce.go.gov.br' in self.config['host'].lower():
                connection_params['ssl_disabled'] = True
            
            connection = mysql.connector.connect(**connection_params)
            
            # Configurar timeout de execução de query
            # 60 segundos para queries complexas de PING (incluindo ORDER BY DESC com BLOB)
            cursor = connection.cursor()
            cursor.execute("SET SESSION MAX_EXECUTION_TIME=60000")  # 60 segundos em ms
            cursor.close()
            
            return connection
        except Error as e:
            self.logger.error(f"Erro ao conectar ao MySQL: {e}")
            raise
    
    def obter_pings(self, filtros=None, limite=100, offset=0, force_refresh=False):
        """
        Obtém lista de registros PING com filtros opcionais.
        
        Args:
            filtros (dict): Dicionário com filtros (local, antena, horario_inicio, horario_fim)
            limite (int): Número máximo de registros
            offset (int): Deslocamento para paginação
            force_refresh (bool): Força atualização ignorando o cache
            
        Returns:
            dict: Resultado com pings e total
        """
        cache_params = {
            'filtros': filtros or {},
            'limite': limite,
            'offset': offset
        }
        cache_key = self._get_cache_key('pings', cache_params)
        total_cache_key = self._get_cache_key('pings_total', {'filtros': filtros or {}})
        
        # Verificar cache
        if not force_refresh:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                cached_total = self._get_from_cache(total_cache_key)
                if cached_total:
                    cached_result['total'] = cached_total
                cached_result['from_cache'] = True
                return cached_result
        
        total = 0
        pings = []
        
        try:
            where_conditions = []
            params = []

            # Filtros
            if filtros:
                if filtros.get('local'):
                    where_conditions.append("Local = %s")
                    params.append(filtros['local'])
                
                if filtros.get('antena'):
                    where_conditions.append("antena = %s")
                    params.append(filtros['antena'])
                
                if filtros.get('horario_inicio'):
                    where_conditions.append("Horario >= %s")
                    params.append(filtros['horario_inicio'])

                if filtros.get('horario_fim'):
                    where_conditions.append("Horario <= %s")
                    params.append(filtros['horario_fim'])

            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            connection = None
            cursor = None
            try:
                connection = self._get_connection()
                cursor = connection.cursor(dictionary=True)
                
                # Query principal
                data_query = f"""
                    SELECT 
                        Horario,
                        Local,
                        antena
                    FROM pingsRFID
                    WHERE {where_clause}
                    ORDER BY Horario DESC
                    LIMIT %s OFFSET %s
                """
                
                query_params = params.copy()
                query_params.extend([limite, offset])
                
                self.logger.debug(f"Query: {data_query}, Params: {query_params}")
                
                cursor.execute(data_query, query_params)
                pings_raw = cursor.fetchall()
                
                # COUNT na primeira página ou se forçar refresh
                if offset == 0 or force_refresh:
                    count_query = f"""
                        SELECT COUNT(*) as total 
                        FROM pingsRFID
                        WHERE {where_clause}
                    """
                    cursor.execute(count_query, params)
                    count_result = cursor.fetchone()
                    total = count_result['total'] if count_result else 0
                    self._set_cache(total_cache_key, total)
                else:
                    cached_total = self._get_from_cache(total_cache_key)
                    if cached_total is not None:
                        total = cached_total
                    else:
                        count_query = f"""
                            SELECT COUNT(*) as total 
                            FROM pingsRFID
                            WHERE {where_clause}
                        """
                        cursor.execute(count_query, params)
                        count_result = cursor.fetchone()
                        total = count_result['total'] if count_result else 0
                        self._set_cache(total_cache_key, total)
                
                # Processar registros
                for ping in pings_raw:
                    ping_processado = {
                        'horario': ping['Horario'],
                        'local': ping['Local'],
                        'antena': ping['antena'],
                        'local_antena': f"{ping['Local']} - A{ping['antena']}",
                        'tem_foto': True  # Sempre tem foto após migração
                    }
                    
                    # Formatar horário
                    if isinstance(ping['Horario'], datetime):
                        ping_processado['horario_formatado'] = ping['Horario'].strftime('%d/%m/%Y %H:%M:%S')
                    else:
                        ping_processado['horario_formatado'] = str(ping['Horario'])
                    
                    pings.append(ping_processado)
                
            except Exception as e:
                self.logger.error(f"Erro ao buscar registros PING: {e}")
                raise
            finally:
                if cursor:
                    cursor.close()
                if connection:
                    connection.close()
            
            result = {
                'success': True,
                'pings': pings,
                'total': total,
                'limite': limite,
                'offset': offset,
                'from_cache': False
            }
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao obter registros PING: {e}")
            return {
                'success': False,
                'error': str(e),
                'pings': [],
                'total': 0,
                'from_cache': False
            }
    
    def obter_estatisticas_pings(self, filtros=None, force_refresh=False):
        """
        Obtém estatísticas dos registros PING.
        
        Args:
            filtros (dict): Filtros opcionais
            force_refresh (bool): Força atualização ignorando o cache
            
        Returns:
            dict: Estatísticas dos PINGs
        """
        cache_key = self._get_cache_key('estatisticas_pings', filtros)
        
        if not force_refresh:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                cached_result['from_cache'] = True
                return cached_result
        
        try:
            connection = None
            cursor = None
            
            try:
                connection = self._get_connection()
                cursor = connection.cursor(dictionary=True)
                
                where_conditions = []
                params = []
                
                if filtros:
                    if filtros.get('horario_inicio'):
                        where_conditions.append("Horario >= %s")
                        params.append(filtros['horario_inicio'])
                    
                    if filtros.get('horario_fim'):
                        where_conditions.append("Horario <= %s")
                        params.append(filtros['horario_fim'])
                
                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
                
                stats_query = f"""
                    SELECT 
                        COUNT(*) as total_pings,
                        COUNT(DISTINCT CONCAT(Local, ':', antena)) as total_antenas,
                        MIN(Horario) as primeiro_ping,
                        MAX(Horario) as ultimo_ping,
                        COUNT(*) as pings_com_foto
                    FROM pingsRFID
                    WHERE {where_clause}
                """
                
                cursor.execute(stats_query, params)
                stats = cursor.fetchone()
                
                if not stats:
                    stats = {
                        'total_pings': 0,
                        'total_antenas': 0,
                        'primeiro_ping': None,
                        'ultimo_ping': None,
                        'pings_com_foto': 0
                    }
                
                # Formatar datas
                if stats.get('primeiro_ping'):
                    stats['primeiro_ping_formatado'] = stats['primeiro_ping'].strftime('%d/%m/%Y %H:%M')
                else:
                    stats['primeiro_ping_formatado'] = '--'
                    
                if stats.get('ultimo_ping'):
                    stats['ultimo_ping_formatado'] = stats['ultimo_ping'].strftime('%d/%m/%Y %H:%M')
                else:
                    stats['ultimo_ping_formatado'] = '--'
                
                result = {
                    'success': True,
                    'estatisticas': stats,
                    'from_cache': False
                }
                
                self._set_cache(cache_key, result)
                return result
                
            finally:
                if cursor:
                    cursor.close()
                if connection:
                    connection.close()
            
        except mysql.connector.Error as db_error:
            error_msg = str(db_error)
            if 'max_execution_time' in error_msg.lower() or 'timeout' in error_msg.lower():
                self.logger.warning(f"Timeout na query de estatísticas PING: {db_error}")
                return {
                    'success': True,
                    'estatisticas': {
                        'total_pings': 0,
                        'total_antenas': 0,
                        'primeiro_ping_formatado': '--',
                        'ultimo_ping_formatado': '--',
                        'pings_com_foto': 0
                    },
                    'from_cache': False,
                    'warning': 'Timeout ao calcular estatísticas'
                }
            else:
                self.logger.error(f"Erro de banco ao obter estatísticas de PING: {db_error}")
                return {
                    'success': False,
                    'error': str(db_error),
                    'estatisticas': {},
                    'from_cache': False
                }
        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas de PING: {e}")
            return {
                'success': False,
                'error': str(e),
                'estatisticas': {},
                'from_cache': False
            }
    
    def obter_locais_com_antena(self, force_refresh=False):
        """
        Obtém lista de locais e antenas disponíveis.
        
        Returns:
            dict: Lista de locais com suas antenas
        """
        cache_key = 'locais_antenas_ping'
        
        if not force_refresh:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT 
                    Local,
                    antena,
                    COUNT(*) as total_pings,
                    MAX(Horario) as ultimo_ping
                FROM pingsRFID
                GROUP BY Local, antena
                ORDER BY Local, antena
            """
            
            cursor.execute(query)
            resultados = cursor.fetchall()
            
            # Formatar resultados
            locais = []
            for resultado in resultados:
                local_info = {
                    'local': resultado['Local'],
                    'antena': resultado['antena'],
                    'local_antena': f"{resultado['Local']} - A{resultado['antena']}",
                    'total_pings': resultado['total_pings'],
                    'ultimo_ping': resultado['ultimo_ping']
                }
                
                if resultado['ultimo_ping']:
                    local_info['ultimo_ping_formatado'] = resultado['ultimo_ping'].strftime('%d/%m/%Y %H:%M')
                
                locais.append(local_info)
            
            result = {
                'success': True,
                'locais': locais,
                'total': len(locais)
            }
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao obter locais PING: {e}")
            return {
                'success': False,
                'error': str(e),
                'locais': []
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def obter_foto_ping(self, local=None, antena=None, horario=None):
        """
        Obtém a foto de um PING específico.
        
        Args:
            local (str): Local do ping (B1, B2 ou S1)
            antena (str): Número da antena
            horario (str): Horário do PING
            
        Returns:
            dict: Resultado com foto (binário) ou erro
        """
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            if local and antena and horario:
                horario_sql = self._converter_horario_para_sql(horario)
                
                query = """
                    SELECT Foto, Horario, Local, antena
                    FROM pingsRFID
                    WHERE Local = %s
                      AND antena = %s
                      AND Horario = %s
                    LIMIT 1
                """
                cursor.execute(query, (local, antena, horario_sql))
            else:
                return {
                    'success': False,
                    'error': 'Parâmetros insuficientes. Forneça (local, antena, horario)'
                }
            
            resultado = cursor.fetchone()
            
            if not resultado:
                return {
                    'success': False,
                    'error': 'PING não encontrado',
                    'error_type': 'not_found'
                }
            
            if not resultado['Foto'] or len(resultado['Foto']) == 0:
                return {
                    'success': False,
                    'error': 'Sem imagem no Banco de Dados',
                    'error_type': 'no_photo',
                    'horario': resultado['Horario'],
                    'local': resultado['Local'],
                    'antena': resultado['antena']
                }
            
            return {
                'success': True,
                'foto': resultado['Foto'],
                'horario': resultado['Horario'],
                'local': resultado['Local'],
                'antena': resultado['antena']
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter foto do PING: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'exception'
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def verificar_foto_ping(self, local=None, antena=None, horario=None):
        """
        Verifica se um PING possui foto disponível.
        
        Args:
            local (str): Local do ping
            antena (str): Número da antena
            horario (str): Horário do PING
            
        Returns:
            dict: Informações sobre disponibilidade da foto
        """
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            if local and antena and horario:
                horario_sql = self._converter_horario_para_sql(horario)
                
                query = """
                    SELECT 
                        1 as tem_foto,
                        Horario as ultima_foto
                    FROM pingsRFID
                    WHERE Local = %s
                      AND antena = %s
                      AND Horario = %s
                      AND Foto IS NOT NULL
                    LIMIT 1
                """
                cursor.execute(query, (local, antena, horario_sql))
            else:
                return {
                    'success': False,
                    'error': 'Parâmetros insuficientes'
                }
            
            resultado = cursor.fetchone()
            tem_foto = resultado is not None
            
            return {
                'success': True,
                'tem_foto': tem_foto,
                'total_fotos': 1 if tem_foto else 0,
                'ultima_foto': resultado['ultima_foto'] if resultado else None,
                'local': local,
                'antena': antena,
                'horario': horario
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar foto do PING: {e}")
            return {
                'success': False,
                'error': str(e),
                'tem_foto': False
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
