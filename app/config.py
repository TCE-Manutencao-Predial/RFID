# app/config.py
import os
import logging

# Configuração do diretório base
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'dados')

# Garante que o diretório de dados existe
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

ROUTES_PREFIX = '/RFID'

# Configurações do MySQL
MYSQL_CONFIG = {
    'host': 'bdserver.tce.go.gov.br',
    'database': 'equipamentos',
    'user': 'equipamentos_adm',
    'password': 'lOXidexutMoSNX',
    'connection_timeout': 30,
    'command_timeout': 60
}

# Configuração dos diretórios de logs
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'rfid.log')

def setup_logging():
    """Configura o sistema de logging da aplicação."""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)
        
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger('RFID')
    logger.info("Sistema de logging inicializado")
    
    return logger