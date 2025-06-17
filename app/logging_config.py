import logging

def configure_logging():
    # Configuração do scadaweb_logger
    logger = logging.getLogger('RFID')
    logger.setLevel(logging.INFO)

    chatgpt_handler = logging.FileHandler('RFID.log')
    chatgpt_handler.setLevel(logging.INFO)

    app_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    chatgpt_handler.setFormatter(app_formatter)

    logger.addHandler(chatgpt_handler)


