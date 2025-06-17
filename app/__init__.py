from flask import Flask

app = Flask(__name__)

from app.logging_config import configure_logging
# Importa a função configure_logging do módulo logging_config dentro do pacote app.

configure_logging()
# Chama a função configure_logging para configurar o sistema de logging da aplicação.

from app import routes
from app import main


# Thread que executa a main a cada 2 horas
def loop():
    from time import sleep
    tempo = 4*60*60 # segundos

    while True:
        main.main()
        sleep(tempo)

import threading
threading.Thread(target=loop).start()

# Comentario para teste do autoupdate :3
