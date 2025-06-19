# app/utils/GerenciadorLeitoresRFID.py
import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime, timedelta
from ..config import MYSQL_CONFIG
import json
import hashlib
import re

class GerenciadorLeitoresRFID:
    """Gerenciador para operações com leituras RFID da tabela leitoresRFID."""
    
    _instance = None
    
    # Prefixos válidos para filtrar etiquetas relevantes
    PREFIXOS_VALIDOS = [
        '0000000000000000000',
        '617061720000000000',
        'AAA0AAAA',
        '32366259FC'
    ]
    
    @classmethod
    def get_instance(cls):
        """Retorna a instância única do gerenciador (Singleton)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Inicializa o gerenciador."""
        if GerenciadorLeitoresRFID._instance is not None:
            raise Exception("Use get_instance() para obter a instância")
        
        self.logger = logging.getLogger('controlerfid.leitores')
        self.config = MYSQL_CONFIG
        
        # Sistema de cache
        self.cache = {}
        self.cache_timeout = timedelta(minutes=3)  # Cache menor devido ao volume de dados
        
        self.logger.info("Gerenciador de Leitores RFID inicializado")
    
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
    
    def _etiqueta_valida(self, etiqueta_hex):
        """Verifica se a etiqueta tem um dos prefixos válidos."""
        if not etiqueta_hex:
            return False
        
        etiqueta_upper = etiqueta_hex.upper()
        return any(etiqueta_upper.startswith(prefixo.upper()) for prefixo in self.PREFIXOS_VALIDOS)
    
    def obter_leituras(self, filtros=None, limite=100, offset=0, force_refresh=False):
        """
        Obtém lista de leituras com filtros opcionais.
        
        Args:
            filtros (dict): Dicionário com filtros (etiqueta, antena, horario_inicio, horario_fim)
            limite (int): Número máximo de registros
            offset (int): Deslocamento para paginação
            force_refresh (bool): Força atualização ignorando o cache
            
        Returns:
            dict: Resultado com leituras e total
        """
        # Gerar chave do cache
        cache_params = {
            'filtros': filtros or {},
            'limite': limite,
            'offset': offset
        }
        cache_key = self._get_cache_key('leituras', cache_params)
        
        # Verificar cache primeiro
        if not force_refresh:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                cached_result['from_cache'] = True
                return cached_result
        
        total = 0
        leituras = []
        
        try:
            # Construir query base com filtros de prefixo e RSSI
            where_conditions = []
            params = []

            where_conditions.append("RSSI != 0")
            prefixo_conditions = []
            for prefixo in self.PREFIXOS_VALIDOS:
                prefixo_conditions.append("l.EtiquetaRFID_hex LIKE %s")
                params.append(f"{prefixo}%")
            where_conditions.append(f"({' OR '.join(prefixo_conditions)})")

            # Filtros adicionais do usuário
            if filtros:
                if filtros.get('etiqueta'):
                    where_conditions.append("l.EtiquetaRFID_hex LIKE %s")
                    params.append(f"%{filtros['etiqueta']}%")

                if filtros.get('descricao'):
                    where_conditions.append("e.Descricao LIKE %s")
                    params.append(f"%{filtros['descricao']}%")

                # Filtro especial para antena com código do leitor
                if filtros.get('antena'):
                    # Verificar se é formato "[XX] AY"
                    if '[' in str(filtros['antena']) and ']' in str(filtros['antena']):
                        # Extrair código do leitor e antena
                        match = re.match(r'\[([^\]]+)\]\s*A?(\d+)', str(filtros['antena']))
                        if match:
                            codigo_leitor = match.group(1)
                            antena_num = match.group(2)
                            where_conditions.append("l.CodigoLeitor = %s AND l.Antena = %s")
                            params.append(codigo_leitor)
                            params.append(antena_num)
                        else:
                            # Formato inválido, usar como está
                            where_conditions.append("l.Antena = %s")
                            params.append(filtros['antena'])
                    else:
                        # Formato simples, apenas número da antena
                        where_conditions.append("l.Antena = %s")
                        params.append(filtros['antena'])
                
                # Filtro por código do leitor apenas
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

            # PRIMEIRA CONEXÃO: Obter o total (agora com JOIN para descrição)
            connection1 = None
            cursor1 = None
            try:
                connection1 = self._get_connection()
                cursor1 = connection1.cursor(dictionary=True)
                
                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM leitoresRFID l
                    LEFT JOIN etiquetasRFID e ON l.EtiquetaRFID_hex = e.EtiquetaRFID_hex
                    WHERE {where_clause}
                """
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
            
            # SEGUNDA CONEXÃO: Obter os registros (já havia JOIN)
            connection2 = None
            cursor2 = None
            try:
                connection2 = self._get_connection()
                cursor2 = connection2.cursor(dictionary=True)
                
                # Query com LEFT JOIN para obter descrição da etiqueta
                data_query = f"""
                    SELECT 
                        l.CodigoLeitor,
                        l.Horario,
                        l.Antena,
                        l.EtiquetaRFID_hex,
                        l.RSSI,
                        e.Descricao as DescricaoEquipamento,
                        e.Destruida,
                        CASE 
                            WHEN e.Destruida IS NOT NULL THEN 'destruida'
                            WHEN e.id_listaEtiquetasRFID IS NOT NULL THEN 'ativa'
                            ELSE 'nao_cadastrada'
                        END as StatusEtiqueta
                    FROM leitoresRFID l
                    LEFT JOIN etiquetasRFID e ON l.EtiquetaRFID_hex = e.EtiquetaRFID_hex
                    WHERE {where_clause}
                    ORDER BY l.Horario DESC
                    LIMIT %s OFFSET %s
                """
                
                # Adicionar limite e offset aos parâmetros
                query_params = params.copy()
                query_params.extend([limite, offset])
                
                cursor2.execute(data_query, query_params)
                leituras_raw = cursor2.fetchall()
                
                # Processar leituras para formatar dados
                for leitura in leituras_raw:
                    leitura_processada = {
                        'codigo_leitor': leitura['CodigoLeitor'],
                        'horario': leitura['Horario'],
                        'antena': leitura['Antena'],
                        'antena_completa': f"[{leitura['CodigoLeitor']}] A{leitura['Antena']}",
                        'etiqueta_hex': leitura['EtiquetaRFID_hex'],
                        'rssi': leitura['RSSI'],
                        'descricao_equipamento': leitura['DescricaoEquipamento'] or 'Sem descrição',
                        'status_etiqueta': leitura['StatusEtiqueta']
                    }
                    
                    # Formatar horário se for datetime
                    if isinstance(leitura['Horario'], datetime):
                        leitura_processada['horario_formatado'] = leitura['Horario'].strftime('%d/%m/%Y %H:%M:%S')
                    else:
                        leitura_processada['horario_formatado'] = str(leitura['Horario'])
                    
                    leituras.append(leitura_processada)
                
            except Exception as e:
                self.logger.error(f"Erro ao buscar leituras: {e}")
                raise
            finally:
                if cursor2:
                    cursor2.close()
                if connection2:
                    connection2.close()
            
            result = {
                'success': True,
                'leituras': leituras,
                'total': total,
                'limite': limite,
                'offset': offset,
                'from_cache': False
            }
            
            # Armazenar no cache
            self._set_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao obter leituras: {e}")
            return {
                'success': False,
                'error': str(e),
                'leituras': [],
                'total': 0,
                'from_cache': False
            }
    
    def obter_estatisticas_leituras(self, filtros=None, force_refresh=False):
        """
        Obtém estatísticas das leituras.
        
        Args:
            filtros (dict): Filtros opcionais
            force_refresh (bool): Força atualização ignorando o cache
            
        Returns:
            dict: Estatísticas das leituras
        """
        cache_key = self._get_cache_key('estatisticas_leituras', filtros)
        
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
                where_conditions = ["RSSI != 0"]
                params = []
                
                # Filtro de prefixos válidos
                prefixo_conditions = []
                for prefixo in self.PREFIXOS_VALIDOS:
                    prefixo_conditions.append("l.EtiquetaRFID_hex LIKE %s")
                    params.append(f"{prefixo}%")
                
                where_conditions.append(f"({' OR '.join(prefixo_conditions)})")
                
                # Aplicar filtros adicionais se fornecidos
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
                        COUNT(DISTINCT l.EtiquetaRFID_hex) as total_etiquetas_unicas,
                        COUNT(*) as total_leituras,
                        COUNT(DISTINCT l.Antena) as total_antenas,
                        COUNT(DISTINCT DATE(l.Horario)) as dias_com_leitura,
                        MIN(l.Horario) as primeira_leitura,
                        MAX(l.Horario) as ultima_leitura,
                        COUNT(DISTINCT CASE WHEN e.id_listaEtiquetasRFID IS NOT NULL THEN l.EtiquetaRFID_hex END) as etiquetas_cadastradas,
                        COUNT(DISTINCT CASE WHEN e.id_listaEtiquetasRFID IS NULL THEN l.EtiquetaRFID_hex END) as etiquetas_nao_cadastradas
                    FROM leitoresRFID l
                    LEFT JOIN etiquetasRFID e ON l.EtiquetaRFID_hex = e.EtiquetaRFID_hex
                    WHERE {where_clause}
                """
                
                cursor.execute(stats_query, params)
                stats = cursor.fetchone()
                
                # Formatar datas
                if stats['primeira_leitura']:
                    stats['primeira_leitura_formatada'] = stats['primeira_leitura'].strftime('%d/%m/%Y %H:%M')
                if stats['ultima_leitura']:
                    stats['ultima_leitura_formatada'] = stats['ultima_leitura'].strftime('%d/%m/%Y %H:%M')
                
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
            self.logger.error(f"Erro ao obter estatísticas de leituras: {e}")
            return {
                'success': False,
                'error': str(e),
                'estatisticas': {},
                'from_cache': False
            }
    
    def obter_leituras_por_etiqueta(self, etiqueta_hex, limite=50):
        """
        Obtém histórico de leituras de uma etiqueta específica.
        
        Args:
            etiqueta_hex (str): Código hexadecimal da etiqueta
            limite (int): Número máximo de leituras a retornar
            
        Returns:
            dict: Histórico de leituras da etiqueta
        """
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT 
                    CodigoLeitor,
                    Horario,
                    Antena,
                    RSSI
                FROM leitoresRFID
                WHERE EtiquetaRFID_hex = %s AND RSSI != 0
                ORDER BY Horario DESC
                LIMIT %s
            """
            
            cursor.execute(query, (etiqueta_hex, limite))
            leituras = cursor.fetchall()
            
            # Formatar horários
            for leitura in leituras:
                if isinstance(leitura['Horario'], datetime):
                    leitura['horario_formatado'] = leitura['Horario'].strftime('%d/%m/%Y %H:%M:%S')
            
            return {
                'success': True,
                'etiqueta': etiqueta_hex,
                'leituras': leituras,
                'total': len(leituras)
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter leituras da etiqueta {etiqueta_hex}: {e}")
            return {
                'success': False,
                'error': str(e),
                'leituras': []
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
        cache_key = 'antenas_com_leitor'
        
        if not force_refresh:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Query para obter antenas únicas com código do leitor
            query = """
                SELECT 
                    CodigoLeitor,
                    Antena,
                    COUNT(*) as total_leituras,
                    COUNT(DISTINCT EtiquetaRFID_hex) as etiquetas_unicas,
                    MAX(Horario) as ultima_leitura
                FROM leitoresRFID
                WHERE RSSI != 0
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
                    'total_leituras': resultado['total_leituras'],
                    'etiquetas_unicas': resultado['etiquetas_unicas'],
                    'ultima_leitura': resultado['ultima_leitura']
                }
                
                if resultado['ultima_leitura']:
                    antena_info['ultima_leitura_formatada'] = resultado['ultima_leitura'].strftime('%d/%m/%Y %H:%M')
                
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
            self.logger.error(f"Erro ao obter antenas com leitor: {e}")
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