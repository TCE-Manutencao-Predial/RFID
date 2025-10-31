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
    """Gerenciador para operações com registros PING_PERIODICO da tabela leitoresRFID."""
    
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
        
        self.logger.info("Gerenciador de PING RFID inicializado")
    
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
    
    def obter_pings(self, filtros=None, limite=100, offset=0, force_refresh=False):
        """
        Obtém lista de registros PING com filtros opcionais.
        
        Args:
            filtros (dict): Dicionário com filtros (etiqueta, antena, horario_inicio, horario_fim)
            limite (int): Número máximo de registros
            offset (int): Deslocamento para paginação
            force_refresh (bool): Força atualização ignorando o cache
            
        Returns:
            dict: Resultado com pings e total
        """
        # Gerar chave do cache
        cache_params = {
            'filtros': filtros or {},
            'limite': limite,
            'offset': offset
        }
        cache_key = self._get_cache_key('pings', cache_params)
        
        # Verificar cache primeiro
        if not force_refresh:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                cached_result['from_cache'] = True
                return cached_result
        
        total = None
        total_from_cache = False
        pings = []
        # Reutiliza a contagem total por filtro para evitar COUNT repetidos
        total_cache_key = self._get_cache_key('pings_total', {
            'filtros': filtros or {}
        })

        if not force_refresh:
            cached_total = self._get_from_cache(total_cache_key)
            if cached_total and isinstance(cached_total, dict):
                total = cached_total.get('total')
                if total is not None:
                    total_from_cache = True
        
        try:
            # Construir query base - FILTROS ESPECÍFICOS PARA PING
            where_conditions = []
            params = []

            # Filtro principal: EtiquetaRFID_hex começa com 'PING_PERIODICO_'
            where_conditions.append("l.EtiquetaRFID_hex LIKE 'PING_PERIODICO_%'")
            
            # Filtro principal: Foto deve existir e ter tamanho > 0
            where_conditions.append("l.Foto IS NOT NULL")
            where_conditions.append("LENGTH(l.Foto) > 0")

            # Filtros adicionais do usuário
            if filtros:
                if filtros.get('etiqueta'):
                    where_conditions.append("l.EtiquetaRFID_hex LIKE %s")
                    params.append(f"%{filtros['etiqueta']}%")

                # Filtro especial para antena com código do leitor
                if filtros.get('antena'):
                    if '[' in str(filtros['antena']) and ']' in str(filtros['antena']):
                        match = re.match(r'\[([^\]]+)\]\s*A?(\d+)', str(filtros['antena']))
                        if match:
                            codigo_leitor = match.group(1)
                            antena_num = match.group(2)
                            where_conditions.append("l.CodigoLeitor = %s AND l.Antena = %s")
                            params.append(codigo_leitor)
                            params.append(antena_num)
                        else:
                            where_conditions.append("l.Antena = %s")
                            params.append(filtros['antena'])
                    else:
                        where_conditions.append("l.Antena = %s")
                        params.append(filtros['antena'])
                
                if filtros.get('codigo_leitor'):
                    where_conditions.append("l.CodigoLeitor = %s")
                    params.append(filtros['codigo_leitor'])

                if filtros.get('horario_inicio'):
                    where_conditions.append("l.Horario >= %s")
                    params.append(filtros['horario_inicio'])

                if filtros.get('horario_fim'):
                    where_conditions.append("l.Horario <= %s")
                    params.append(filtros['horario_fim'])

            where_clause = " AND ".join(where_conditions)

            connection = None
            cursor = None
            try:
                connection = self._get_connection()
                cursor = connection.cursor(dictionary=True)

                if total is None:
                    count_query = f"""
                        SELECT COUNT(*) as total
                        FROM leitoresRFID l
                        WHERE {where_clause}
                    """
                    count_params = params.copy()
                    cursor.execute(count_query, count_params)
                    result = cursor.fetchone()
                    total = result['total'] if result and 'total' in result else 0
                    self._set_cache(total_cache_key, {'total': total})

                if total is None:
                    total = 0

                pings_raw = []
                if total > 0 and offset < total:  # Evita SELECT inútil quando não há página disponível
                    data_query = f"""
                        SELECT 
                            l.CodigoLeitor,
                            l.Horario,
                            l.Antena,
                            l.EtiquetaRFID_hex,
                            l.RSSI,
                            CASE 
                                WHEN l.Foto IS NOT NULL AND LENGTH(l.Foto) > 0 THEN 1 
                                ELSE 0 
                            END as TemFoto
                        FROM leitoresRFID l
                        WHERE {where_clause}
                        ORDER BY l.Horario DESC
                        LIMIT %s OFFSET %s
                    """

                    query_params = params.copy()
                    query_params.extend([limite, offset])
                    cursor.execute(data_query, query_params)
                    pings_raw = cursor.fetchall()

                for ping in pings_raw:
                    ping_processado = {
                        'codigo_leitor': ping['CodigoLeitor'],
                        'horario': ping['Horario'],
                        'antena': ping['Antena'],
                        'antena_completa': f"[{ping['CodigoLeitor']}] A{ping['Antena']}",
                        'etiqueta_hex': ping['EtiquetaRFID_hex'],
                        'rssi': ping['RSSI'],
                        'tem_foto': bool(ping['TemFoto'])
                    }

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
                'from_cache': False,
                'total_from_cache': total_from_cache
            }
            
            # Armazenar no cache
            self._set_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao obter registros PING: {e}")
            return {
                'success': False,
                'error': str(e),
                'pings': [],
                'total': 0,
                'from_cache': False,
                'total_from_cache': False
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
                
                # Construir filtros base
                where_conditions = []
                params = []
                
                # Filtros principais
                where_conditions.append("l.EtiquetaRFID_hex LIKE 'PING_PERIODICO_%'")
                where_conditions.append("l.Foto IS NOT NULL")
                where_conditions.append("LENGTH(l.Foto) > 0")
                
                # Aplicar filtros adicionais
                if filtros:
                    if filtros.get('horario_inicio'):
                        where_conditions.append("l.Horario >= %s")
                        params.append(filtros['horario_inicio'])
                    
                    if filtros.get('horario_fim'):
                        where_conditions.append("l.Horario <= %s")
                        params.append(filtros['horario_fim'])
                
                where_clause = " AND ".join(where_conditions)
                
                # Query para estatísticas
                stats_query = f"""
                    SELECT 
                        COUNT(*) as total_pings,
                        COUNT(DISTINCT l.EtiquetaRFID_hex) as pings_unicos,
                        COUNT(DISTINCT CONCAT(l.CodigoLeitor, ':', l.Antena)) as total_antenas,
                        MIN(l.Horario) as primeiro_ping,
                        MAX(l.Horario) as ultimo_ping,
                        SUM(CASE WHEN l.Foto IS NOT NULL AND LENGTH(l.Foto) > 0 THEN 1 ELSE 0 END) as pings_com_foto
                    FROM leitoresRFID l
                    WHERE {where_clause}
                """
                
                cursor.execute(stats_query, params)
                stats = cursor.fetchone()
                
                # Formatar datas
                if stats['primeiro_ping']:
                    stats['primeiro_ping_formatado'] = stats['primeiro_ping'].strftime('%d/%m/%Y %H:%M')
                if stats['ultimo_ping']:
                    stats['ultimo_ping_formatado'] = stats['ultimo_ping'].strftime('%d/%m/%Y %H:%M')
                
                result = {
                    'success': True,
                    'estatisticas': stats,
                    'from_cache': False
                }
                
                # Armazenar no cache
                self._set_cache(cache_key, result)
                
                return result
                
            finally:
                if cursor:
                    cursor.close()
                if connection:
                    connection.close()
            
        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas de PING: {e}")
            return {
                'success': False,
                'error': str(e),
                'estatisticas': {},
                'from_cache': False
            }
    
    def obter_pings_por_etiqueta(self, etiqueta_hex, limite=50):
        """
        Obtém histórico de PINGs de uma etiqueta específica.
        
        Args:
            etiqueta_hex (str): Código hexadecimal da etiqueta
            limite (int): Número máximo de registros a retornar
            
        Returns:
            dict: Histórico de PINGs da etiqueta
        """
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT 
                    CodigoLeitor,
                    Horario,
                    Antena,
                    RSSI,
                    CASE 
                        WHEN Foto IS NOT NULL AND LENGTH(Foto) > 0 THEN 1 
                        ELSE 0 
                    END as TemFoto
                FROM leitoresRFID
                WHERE EtiquetaRFID_hex = %s 
                  AND EtiquetaRFID_hex LIKE 'PING_PERIODICO_%'
                  AND Foto IS NOT NULL
                  AND LENGTH(Foto) > 0
                ORDER BY Horario DESC
                LIMIT %s
            """
            
            cursor.execute(query, (etiqueta_hex, limite))
            pings = cursor.fetchall()
            
            # Formatar horários
            for ping in pings:
                if isinstance(ping['Horario'], datetime):
                    ping['horario_formatado'] = ping['Horario'].strftime('%d/%m/%Y %H:%M:%S')
            
            return {
                'success': True,
                'etiqueta': etiqueta_hex,
                'pings': pings,
                'total': len(pings)
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter PINGs da etiqueta {etiqueta_hex}: {e}")
            return {
                'success': False,
                'error': str(e),
                'pings': []
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def obter_antenas_com_leitor(self, force_refresh=False):
        """
        Obtém lista de antenas agrupadas por código do leitor.
        
        Returns:
            dict: Lista de antenas com informações do leitor
        """
        cache_key = 'antenas_com_leitor_ping'
        
        if not force_refresh:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT 
                    CodigoLeitor,
                    Antena,
                    COUNT(*) as total_pings,
                    COUNT(DISTINCT EtiquetaRFID_hex) as etiquetas_unicas,
                    MAX(Horario) as ultimo_ping
                FROM leitoresRFID
                WHERE EtiquetaRFID_hex LIKE 'PING_PERIODICO_%'
                  AND Foto IS NOT NULL
                  AND LENGTH(Foto) > 0
                GROUP BY CodigoLeitor, Antena
                ORDER BY CodigoLeitor, Antena
            """
            
            cursor.execute(query)
            resultados = cursor.fetchall()
            
            # Formatar resultados
            antenas = []
            for resultado in resultados:
                antena_info = {
                    'codigo_leitor': resultado['CodigoLeitor'],
                    'antena': resultado['Antena'],
                    'antena_completa': f"[{resultado['CodigoLeitor']}] A{resultado['Antena']}",
                    'total_pings': resultado['total_pings'],
                    'etiquetas_unicas': resultado['etiquetas_unicas'],
                    'ultimo_ping': resultado['ultimo_ping']
                }
                
                if resultado['ultimo_ping']:
                    antena_info['ultimo_ping_formatado'] = resultado['ultimo_ping'].strftime('%d/%m/%Y %H:%M')
                
                antenas.append(antena_info)
            
            result = {
                'success': True,
                'antenas': antenas,
                'total': len(antenas)
            }
            
            # Armazenar no cache
            self._set_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao obter antenas PING com leitor: {e}")
            return {
                'success': False,
                'error': str(e),
                'antenas': []
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def obter_foto_ping(self, etiqueta_hex):
        """
        Obtém a foto mais recente de um PING específico.
        
        Args:
            etiqueta_hex (str): Código hexadecimal da etiqueta PING
            
        Returns:
            dict: Resultado com foto (binário) ou erro
        """
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT Foto, Horario
                FROM leitoresRFID
                WHERE EtiquetaRFID_hex = %s 
                  AND EtiquetaRFID_hex LIKE 'PING_PERIODICO_%'
                  AND Foto IS NOT NULL 
                  AND LENGTH(Foto) > 0
                ORDER BY Horario DESC
                LIMIT 1
            """
            
            cursor.execute(query, (etiqueta_hex,))
            resultado = cursor.fetchone()
            
            if not resultado:
                return {
                    'success': False,
                    'error': 'Nenhuma foto encontrada para este PING'
                }
            
            return {
                'success': True,
                'foto': resultado['Foto'],
                'horario': resultado['Horario'],
                'etiqueta': etiqueta_hex
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter foto do PING {etiqueta_hex}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def verificar_foto_ping(self, etiqueta_hex):
        """
        Verifica se um PING possui foto disponível.
        
        Args:
            etiqueta_hex (str): Código hexadecimal da etiqueta PING
            
        Returns:
            dict: Informações sobre disponibilidade da foto
        """
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT 
                    COUNT(*) as total_fotos,
                    MAX(Horario) as ultima_foto
                FROM leitoresRFID
                WHERE EtiquetaRFID_hex = %s 
                  AND EtiquetaRFID_hex LIKE 'PING_PERIODICO_%'
                  AND Foto IS NOT NULL 
                  AND LENGTH(Foto) > 0
            """
            
            cursor.execute(query, (etiqueta_hex,))
            resultado = cursor.fetchone()
            
            tem_foto = resultado['total_fotos'] > 0 if resultado else False
            
            return {
                'success': True,
                'tem_foto': tem_foto,
                'total_fotos': resultado['total_fotos'] if resultado else 0,
                'ultima_foto': resultado['ultima_foto'] if resultado else None,
                'etiqueta': etiqueta_hex
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar foto do PING {etiqueta_hex}: {e}")
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
