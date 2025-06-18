# app/utils/GerenciadorEtiquetasRFID.py
import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime
from ..config import MYSQL_CONFIG

class GerenciadorEtiquetasRFID:
    """Gerenciador para operações com etiquetas RFID no MySQL."""
    
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
        self.logger.info("Gerenciador de Etiquetas RFID inicializado")
    
    def _get_connection(self):
        """Cria e retorna uma conexão com o MySQL."""
        try:
            connection = mysql.connector.connect(
                host=self.config['host'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password'],
                connection_timeout=self.config['connection_timeout']
            )
            return connection
        except Error as e:
            self.logger.error(f"Erro ao conectar ao MySQL: {e}")
            raise
    
    def obter_etiquetas(self, filtros=None, limite=100, offset=0):
        """
        Obtém lista de etiquetas com filtros opcionais.
        
        Args:
            filtros (dict): Dicionário com filtros (etiqueta, descricao, destruida)
            limite (int): Número máximo de registros
            offset (int): Deslocamento para paginação
            
        Returns:
            dict: Resultado com etiquetas e total
        """
        connection = None
        cursor = None
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Query base
            query = """
                SELECT 
                    id_listaEtiquetasRFID,
                    EtiquetaRFID_hex,
                    Descricao,
                    Destruida
                FROM etiquetasRFID
                WHERE 1=1
            """
            params = []
            
            # Aplicar filtros
            if filtros:
                if filtros.get('etiqueta'):
                    query += " AND EtiquetaRFID_hex LIKE %s"
                    params.append(f"%{filtros['etiqueta']}%")
                
                if filtros.get('descricao'):
                    query += " AND Descricao LIKE %s"
                    params.append(f"%{filtros['descricao']}%")
                
                if filtros.get('destruida') is not None:
                    query += " AND Destruida = %s"
                    params.append(filtros['destruida'])
            
            # PRIMEIRO: Obter o total usando um cursor separado
            count_cursor = connection.cursor(dictionary=True)
            count_query = query.replace(
                "SELECT id_listaEtiquetasRFID, EtiquetaRFID_hex, Descricao, Destruida", 
                "SELECT COUNT(*) as total"
            )
            
            count_cursor.execute(count_query, params)
            result = count_cursor.fetchone()
            total = result['total'] if result else 0
            count_cursor.close()  # Fechar o cursor de contagem
            
            # SEGUNDO: Obter os registros com limite e offset
            query += " ORDER BY id_listaEtiquetasRFID DESC LIMIT %s OFFSET %s"
            params.extend([limite, offset])
            
            cursor.execute(query, params)
            etiquetas = cursor.fetchall()
            
            return {
                'success': True,
                'etiquetas': etiquetas,
                'total': total,
                'limite': limite,
                'offset': offset
            }
            
        except Error as e:
            self.logger.error(f"Erro ao obter etiquetas: {e}")
            return {
                'success': False,
                'error': str(e),
                'etiquetas': [],
                'total': 0
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def obter_etiqueta_por_id(self, id_etiqueta):
        """
        Obtém uma etiqueta específica pelo ID.
        
        Args:
            id_etiqueta (int): ID da etiqueta
            
        Returns:
            dict: Dados da etiqueta ou None
        """
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
            connection.commit()
            
            return {
                'success': True,
                'message': 'Etiqueta atualizada com sucesso',
                'affected_rows': cursor.rowcount
            }
            
        except Error as e:
            self.logger.error(f"Erro ao atualizar etiqueta {id_etiqueta}: {e}")
            if connection:
                connection.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def obter_estatisticas(self):
        """
        Obtém estatísticas gerais das etiquetas.
        
        Returns:
            dict: Estatísticas
        """
        connection = None
        cursor = None
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Total de etiquetas
            cursor.execute("SELECT COUNT(*) as total FROM etiquetasRFID")
            result = cursor.fetchone()
            total = result['total'] if result else 0
            
            # Limpar o cursor antes da próxima query
            cursor.fetchall()  # Garantir que todos os resultados foram lidos
            
            # Total de etiquetas destruídas
            cursor.execute("SELECT COUNT(*) as destruidas FROM etiquetasRFID WHERE Destruida = 1")
            result = cursor.fetchone()
            destruidas = result['destruidas'] if result else 0
            
            # Total de etiquetas ativas
            ativas = total - destruidas
            
            return {
                'success': True,
                'estatisticas': {
                    'total': total,
                    'ativas': ativas,
                    'destruidas': destruidas,
                    'percentual_ativas': round((ativas / total * 100) if total > 0 else 0, 2)
                }
            }
            
        except Error as e:
            self.logger.error(f"Erro ao obter estatísticas: {e}")
            return {
                'success': False,
                'error': str(e),
                'estatisticas': {
                    'total': 0,
                    'ativas': 0,
                    'destruidas': 0,
                    'percentual_ativas': 0
                }
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()