from openai import OpenAI
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# Obtenha o logger já configurado
logger = logging.getLogger('RFID')

import random
from datetime import datetime

temas = [

    # Eletrônica Analógica (intermediário)
    "Filtros analógicos com circuitos práticos",
    "Amplificadores operacionais com circuitos práticos",
    "Amplificadores diferenciais com circuitos práticos",
    "Amplificadores de potência com circuitos práticos",
    "Transistores bipolares de junção (BJTs) com circuitos práticos",
    "Transistores de efeito de campo (FETs) com circuitos práticos",
    "Circuitos intermediários ou avançados de polarização de transistores com circuitos práticos",
    "Circuitos amplificadores com BJTs com circuitos práticos",
    "Circuitos amplificadores com FETs com circuitos práticos",
    "Resposta em frequência de amplificadores com circuitos práticos",
    "Realimentação em amplificadores com circuitos práticos",
    "Circuitos intermediários ou avançados de temporização com circuitos práticos",
    "Circuitos intermediários ou avançados de chaveamento com circuitos práticos",
    "Reguladores de tensão com circuitos práticos",
    "Fontes de alimentação com circuitos práticos",
    "Conversores DC-DC com circuitos práticos",
    "Conversores AC-DC com circuitos práticos",
    "Conversores DC-AC com circuitos práticos",
    "Conversores AC-AC com circuitos práticos",
    "dspic com circuitos práticos",
    "Microcontroladores PIC18 com circuitos práticos",
    "Microcontroladores Microchip com circuitos práticos",
    "FPGA em 2025",
    "Microcontroladores PIC em 2025",
    "É possível construir dispositivos wifi estáveis com Arduino?",
    "Como dispositivos wifi compatíveis com alexa foram ?",

    
    #   Python:
    "Python: Ambientes de Desenvolvimento Modernos em Python",
    "Python: Isolamento do ambiente de execução",
    "Python: Ferramentas de produtividade populares",
    "Python: Novidades no Python",
    "Python: Operadores de mesclagem e atualização de dicionários",
    "Python: Expressões de atribuição",
    "Python: Tipagem genérica",
    "Python: Parâmetros somente posicionais",
    "Python: Função breakpoint()",
    "Python: Literais numéricos com underscores",
    "Python: Módulo secrets",
    "Python: Comparação do Python com Outras Linguagens",
    "Python: Modelo de classes e programação orientada a objetos",
    "Python: Polimorfismo dinâmico",
    "Python: Classes de dados",
    "Python: Programação funcional",
    "Python: Enumerações",
    "Python: Interfaces, Padrões e Modularidade",
    "Python: Uso de classes base abstratas",
    "Python: Inversão de controle e injeção de dependência",
    "Python: Concorrência",
    "Python: Multithreading",
    "Python: Multiprocessing",
    "Python: Programação assíncrona",
    "Python: Programação Orientada a Eventos",
    "Python: Conceitos de programação orientada a eventos",
    "Python: Diferentes estilos de programação orientada a eventos",
    "Python: Arquiteturas orientadas a eventos",
    "Python: Uso de decoradores",
    "Python: Criação de executáveis standalone",
    "Python: Observação do Comportamento e Desempenho da Aplicação",
    "Python: Captura de erros e logs",
    "Python: Instrumentação de código com métricas personalizadas",
    "Python: Rastreamento de aplicações distribuídas",
    "Python: Redução de complexidade através da escolha de estruturas de dados apropriadas",
    "Python: Aproveitamento de trade-offs arquiteturais",

    # Parte I: Estruturas de dados
    "Python: O modelo de dados do Python",
    "Python: Uma coleção de sequências",
    "Python: Dicionários e conjuntos",
    
    # Parte II: Funções como objetos
    "Python: Funções como objetos de primeira classe",
    "Python: Dicas de tipo em funções",
    "Python: Decoradores e clausuras",
    "Python: Padrões de projetos com funções de primeira classe",
    
    # Parte III: Classes e protocolos
    "Python: Um objeto pythônico",
    "Python: Métodos especiais para sequências",
    "Python: Interfaces, protocolos e ABCs",
    "Python: Herança: para o bem ou para o mal",
    "Python: Sobrecarga de operadores",
    
    # Parte IV: Controle de fluxo
    "Python: Iteradores, geradores e corrotinas clássicas",
    "Python: Instruções with, match e blocos else",
    "Python: Modelos de concorrência no Python",
    "Python: Executores concorrentes",
    "Python: Programação assíncrona",

     
    # Python
    "Otimização de loops no Python",
    "Uso de decoradores em funções Python",
    "Tratamento de exceções com blocos try-except em Python",
    "Manipulação de arquivos e diretórios no Python",
    "Integração de Python com APIs REST",
    "Automação de tarefas com Python e Selenium",
    "Uso de generators e iteradores no Python",
    "Testes unitários no Python com pytest",
    "Novas bibliotecas de programação em Python",
    "Bibliotecas de destaque na programação em python em 2024",
    
    # Python (avançado)
    "Programação assíncrona com asyncio em Python",
    "Implementação de servidores WebSockets com Python",
    "Criação de APIs assíncronas com FastAPI",
    "Manipulação de arquivos binários no Python",
    "Uso de type hints e tipagem estática no Python com mypy",
    "Otimização de desempenho de código Python com Cython",
    "Manipulação avançada de strings com regex em Python",
    "Uso de Multiprocessing para processamento paralelo em Python",
    "Criação de microserviços com Python e Docker",
    
    # Python (avançado, novos tópicos)
    "Criação de sistemas de inteligência artificial com TensorFlow em Python",
    "Uso de Pandas para análise de grandes volumes de dados no Python",
    "Otimização de algoritmos de busca e ordenação com Python",
    "Otimização de operações de I/O intensivas com asyncio no Python",
    "Implementação de sistemas de recomendação com Python e machine learning",
    "Uso de ferramentas de profiling para otimização de código Python",
  
    # Pandas
    "Otimização de consultas em DataFrames grandes com Pandas",
    "Uso de Pandas para manipulação de dados temporais complexos",
    "Criação de pipelines de dados com Pandas e Dask para Big Data",
    "Gerenciamento de dados faltantes e inconsistentes com Pandas",
    "Otimização de operações de agrupamento e agregação em Pandas",
    "Manipulação avançada de índices em DataFrames com Pandas",
    "Integração de Pandas com SQL para consultas eficientes",
    "Visualização de dados com Pandas e Matplotlib",
    "Uso de Pandas para análise exploratória de dados",
    "Criação de relatórios automatizados com Pandas",
    
    # NumPy
    "Uso avançado de operações vetorizadas com NumPy para otimizar desempenho",
    "Trabalhando com matrizes multidimensionais em NumPy",
    "Uso de broadcasting em NumPy para operações eficientes em arrays",
    "Criação de algoritmos matemáticos avançados com NumPy",
    "Uso de manipulação de dados binários com NumPy",
    "Manipulação de dados faltantes em arrays NumPy",
    "Integração de NumPy com bibliotecas de visualização de dados",
    "Otimização de operações de álgebra linear com NumPy",
    "Uso de funções universais (ufuncs) em NumPy",
    "Criação de arrays estruturados e registros com NumPy",
    "Aplicação de transformações FFT (Fast Fourier Transform) com NumPy",
    "Uso de NumPy para análise estatística de grandes datasets",
    "Implementação de operações de convolução com NumPy",
    "Manipulação avançada de índices e slices em arrays NumPy",
    "Uso de NumPy para simulações numéricas e modelagem matemática",
    
    # Matplotlib
    "Criação de gráficos interativos com Matplotlib e widgets",
    "Personalização avançada de gráficos com estilos e temas no Matplotlib",
    "Visualização de grandes volumes de dados com subplots em Matplotlib",
    "Trabalhando com animações e gráficos dinâmicos no Matplotlib",
    "Criação de visualizações 3D avançadas com Matplotlib",
    
   
    # TensorFlow
    "Implementação de redes neurais convolucionais com TensorFlow",
    "Treinamento distribuído de modelos de machine learning com TensorFlow",
    "Otimização de pipelines de dados para treinamento de redes neurais em TensorFlow",
    "Implementação de aprendizado por reforço com TensorFlow",
    "Programação com TensorFlow",
    "Classificação de dados com TensorFlow",
    "Classificação de imagens com TensorFlow",
    "Classificação de texto com TensorFlow",
    "Classificação de áudio com TensorFlow",
    
        
    # PyTorch
    "Treinamento avançado de redes neurais profundas com PyTorch",
    "Uso de PyTorch para Transfer Learning em redes neurais",
    "Implementação de processamento paralelo em PyTorch para grandes datasets",
    "Desenvolvimento de redes neurais dinâmicas com PyTorch",
    "Integração de PyTorch com frameworks de deploy como Flask e FastAPI",
    "Classificação de dados com PyTorch",
    "Classificação de imagens com PyTorch",
    "Classificação de texto com PyTorch",
    "Classificação de áudio com PyTorch",
    
    # scikit-learn
    "Classificação de dados com scikit-learn",
    "Classificação de imagens com scikit-learn",
    "Classificação de texto com scikit-learn",
    "Classificação de áudio com scikit-learn",
    
    # SQLAlchemy
    "Uso básico do SQLAlchemy",
    "Consultas otimizadas com SQLAlchemy e SQL bruto",
    "Criação de migrações de banco de dados automatizadas com Alembic e SQLAlchemy",
    "Uso de SQLAlchemy para gerenciamento de banco de dados distribuído",
    

       
    # Keras
    "Construção de modelos de classificação com Keras",
    "Ajuste fino de hiperparâmetros em Keras usando Keras Tuner",
    "Implementação de redes neurais convolucionais em Keras",
    "Uso de Callbacks personalizados para monitoramento de treinamento em Keras",
    "Criação de modelos de NLP com Keras e TensorFlow",
    "Transfer learning em Keras com modelos pré-treinados",
    "Implementação de redes LSTM para análise de séries temporais com Keras",
    "Introdução ao uso de camadas personalizadas em Keras",
    "Aplicação de regularização para evitar overfitting em Keras",
    "Visualização do treinamento com TensorBoard e Keras",

# scikit-learn
    "Criação de pipelines de pré-processamento com scikit-learn",
    "Implementação de modelos de regressão logística em scikit-learn",
    "Uso de GridSearchCV para ajuste de hiperparâmetros em scikit-learn",
    "Aplicação de técnicas de clusterização com KMeans em scikit-learn",
    "Análise de componentes principais (PCA) em scikit-learn",
    "Implementação de árvores de decisão e Random Forest em scikit-learn",
    "Uso de modelos de Support Vector Machines (SVM) em scikit-learn",
    "Criação de validadores de cross-validation personalizados em scikit-learn",
    "Aplicação de técnicas de ensemble learning com scikit-learn",
    "Uso de métricas de avaliação para classificação com scikit-learn",

    # TensorFlow
    "Treinamento de redes neurais em larga escala com TensorFlow",
    "Uso de TensorFlow Datasets para carregar grandes volumes de dados",
    "Implementação de modelos de reconhecimento de imagem com TensorFlow",
    "Aplicação de redes neurais profundas para classificação de texto com TensorFlow",
    "Utilização do TensorFlow Lite para otimização de modelos em dispositivos móveis",
    "Criação de modelos GANs (Generative Adversarial Networks) com TensorFlow",
    "Implementação de redes de atenção para tarefas de NLP em TensorFlow",
    "Uso de TPU (Tensor Processing Unit) com TensorFlow para acelerar o treinamento",
    "Monitoramento e ajuste de treinamento com TensorBoard em TensorFlow",
    "Estratégias de paralelização de modelos em TensorFlow para uso em GPUs",

    # Keras e TensorFlow
    "Integração entre Keras e TensorFlow para construção de modelos híbridos",
    "Implementação de redes sequenciais e funcionais com Keras e TensorFlow",
    "Uso de Keras para criar modelos embarcados em TensorFlow Serving",
    "Aplicação de aprendizado por transferência com TensorFlow e Keras",
    "Comparação entre Keras Sequential API e Functional API",
    "Uso de Data Augmentation em Keras e TensorFlow para melhorar generalização",
    "Implementação de redes RNN para análise de texto em Keras e TensorFlow",
    "Criação de gráficos computacionais customizados com TensorFlow e Keras",
    "Uso de callbacks de Early Stopping para otimização em Keras e TensorFlow",
    "Estratégias de checkpoint para salvar o estado do treinamento em Keras e TensorFlow",

# scikit-learn e Keras
    "Integração de modelos de aprendizado de máquina em scikit-learn com redes neurais de Keras",
    "Uso de scikit-learn para pré-processamento de dados antes do treinamento em Keras",
    "Comparação entre algoritmos de machine learning tradicionais e redes neurais em Keras",
    "Treinamento de modelos híbridos usando scikit-learn e Keras",
    "Aplicação de técnicas de feature engineering em scikit-learn para uso em Keras",
    "Validação cruzada em scikit-learn com redes neurais de Keras",
    "Uso de scikit-learn para métricas de avaliação de modelos treinados em Keras",
    "Implementação de modelos de machine learning explicáveis usando Keras e scikit-learn",
    "Criação de pipelines que integram pré-processamento e redes neurais com scikit-learn e Keras",
    "Comparação de tempos de execução entre modelos em scikit-learn e Keras"

]

client = OpenAI()

def perguntarChatGPT(pergunta):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Você é um programador ou engenheiro experiente."},
            {
                "role": "user",
                "content": pergunta,
                "temperature": 1
                
            }
        ]
    )
    return completion.choices[0].message.content;
    
def send_email(subject, body, to_email):
    # Configurações do servidor SMTP
    smtp_server = '172.17.120.1' # servidor livre do TCE-GO
    smtp_port = 25
    from_email = 'automacao@tce.go.gov.br'

    # Cria a mensagem de e-mail
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    # Adiciona o corpo do e-mail (texto simples)
    # Em vez de usar 'plain', use 'html' no MIMEText
    msg.attach(MIMEText(body, 'html'))


    try:
        # Conecta ao servidor SMTP
        server = smtplib.SMTP(smtp_server, smtp_port)
        #server.login(from_email, password)

        # Envia o e-mail
        server.sendmail(from_email, to_email, msg.as_string())

        print("Email enviado com sucesso!")
        logger.info(f"Sucesso ao enviar email para {to_email}.")
    except Exception as e:
        print(f"Erro ao enviar o email: {e}")
        logger.error(f"Erro ao enviar email para {to_email}.")
    finally:
        server.quit()
    

def main():
    tema_escolhido = random.choice(temas)
    resultado = perguntarChatGPT(f"Quero uma ampla discussão acerca de: {tema_escolhido}. Discorra sobre o tema e retorne conteúdo relevante e extensivo com exemplos se possível, em formato HTML para ser enviado por email para Gmail (seção body). Não faça introduções: apenas a resposta. Um texto bem avançado.")    
    # Obtém a data e hora atual
    now = datetime.now()
    formatted_date = now.strftime("%Y-%m-%d %H:%M")

    # Adiciona a data e hora ao assunto do email
    subject = f"Programação: Dicas - {formatted_date}"

    send_email(subject, resultado, "phmotaemiliano@gmail.com")
    print(resultado)

