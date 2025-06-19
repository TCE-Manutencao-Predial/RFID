# app/utils/GerenciadorLeitoresRFID.py
import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime, timedelta
from ..config import MYSQL_CONFIG
import json
import hashlib

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
            
            # Filtro principal: RSSI diferente de 0
            where_conditions.append("RSSI != 0")
            
            # Filtro principal: apenas etiquetas com prefixos válidos
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
                
                if filtros.get('antena'):
                    where_conditions.append("l.Antena = %s")
                    params.append(filtros['antena'])
                
                if filtros.get('horario_inicio'):
                    where_conditions.append("l.Horario >= %s")
                    params.append(filtros['horario_inicio'])
                
                if filtros.get('horario_fim'):
                    where_conditions.append("l.Horario <= %s")
                    params.append(filtros['horario_fim'])
            
            where_clause = " AND ".join(where_conditions)
            
            # PRIMEIRA CONEXÃO: Obter o total
            connection1 = None
            cursor1 = None
            try:
                connection1 = self._get_connection()
                cursor1 = connection1.cursor(dictionary=True)
                
                count_query = f"SELECT COUNT(*) as total FROM leitoresRFID l WHERE {where_clause}"
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
            
            # SEGUNDA CONEXÃO: Obter os registros com JOIN para descrição
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

# app/routes/api_leitores.py
from flask import Blueprint, jsonify, request, current_app
import logging
import traceback
from datetime import datetime, timedelta

api_leitores_bp = Blueprint('api_leitores', __name__)
logger = logging.getLogger('RFID.api_leitores')

@api_leitores_bp.route('/leituras', methods=['GET'])
def listar_leituras():
    """
    API para listar leituras RFID com paginação e filtros.
    
    Query params:
        - limite: número de registros por página
        - offset: deslocamento
        - etiqueta: filtro por código da etiqueta
        - antena: filtro por antena
        - horario_inicio: filtro por data/hora inicial
        - horario_fim: filtro por data/hora final
    """
    try:
        gerenciador = current_app.config.get('GERENCIADOR_LEITORES')
        if not gerenciador:
            # Tentar criar o gerenciador se não existir
            from ..utils.GerenciadorLeitoresRFID import GerenciadorLeitoresRFID
            gerenciador = GerenciadorLeitoresRFID.get_instance()
            current_app.config['GERENCIADOR_LEITORES'] = gerenciador
        
        # Obter parâmetros com validação
        try:
            limite = int(request.args.get('limite', 50))
            offset = int(request.args.get('offset', 0))
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Parâmetros de paginação inválidos'
            }), 400
        
        # Filtros
        filtros = {}
        if request.args.get('etiqueta'):
            filtros['etiqueta'] = request.args.get('etiqueta')
        if request.args.get('antena'):
            filtros['antena'] = request.args.get('antena')
        if request.args.get('horario_inicio'):
            filtros['horario_inicio'] = request.args.get('horario_inicio')
        if request.args.get('horario_fim'):
            filtros['horario_fim'] = request.args.get('horario_fim')
        
        # Verificar se é uma atualização forçada
        force_refresh = request.args.get('force_refresh', '').lower() == 'true'
        
        logger.info(f"Buscando leituras com filtros: {filtros}, limite: {limite}, offset: {offset}")
        
        # Buscar leituras
        resultado = gerenciador.obter_leituras(
            filtros=filtros,
            limite=limite,
            offset=offset,
            force_refresh=force_refresh
        )
        
        if not resultado.get('success', False):
            logger.error(f"Erro ao obter leituras: {resultado.get('error')}")
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro ao buscar leituras')
            }), 500
        
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro não tratado ao listar leituras: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@api_leitores_bp.route('/leituras/estatisticas', methods=['GET'])
def obter_estatisticas_leituras():
    """Obtém estatísticas das leituras."""
    try:
        gerenciador = current_app.config.get('GERENCIADOR_LEITORES')
        if not gerenciador:
            from ..utils.GerenciadorLeitoresRFID import GerenciadorLeitoresRFID
            gerenciador = GerenciadorLeitoresRFID.get_instance()
            current_app.config['GERENCIADOR_LEITORES'] = gerenciador
        
        # Filtros opcionais
        filtros = {}
        if request.args.get('horario_inicio'):
            filtros['horario_inicio'] = request.args.get('horario_inicio')
        if request.args.get('horario_fim'):
            filtros['horario_fim'] = request.args.get('horario_fim')
        
        force_refresh = request.args.get('force_refresh', '').lower() == 'true'
        
        resultado = gerenciador.obter_estatisticas_leituras(
            filtros=filtros,
            force_refresh=force_refresh
        )
        
        if not resultado.get('success', False):
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro ao obter estatísticas')
            }), 500
        
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_leitores_bp.route('/leituras/etiqueta/<etiqueta_hex>', methods=['GET'])
def obter_historico_etiqueta(etiqueta_hex):
    """Obtém histórico de leituras de uma etiqueta específica."""
    try:
        gerenciador = current_app.config.get('GERENCIADOR_LEITORES')
        if not gerenciador:
            from ..utils.GerenciadorLeitoresRFID import GerenciadorLeitoresRFID
            gerenciador = GerenciadorLeitoresRFID.get_instance()
            current_app.config['GERENCIADOR_LEITORES'] = gerenciador
        
        limite = int(request.args.get('limite', 50))
        
        resultado = gerenciador.obter_leituras_por_etiqueta(etiqueta_hex, limite)
        
        if not resultado.get('success', False):
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro ao obter histórico')
            }), 500
        
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro ao obter histórico da etiqueta: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500