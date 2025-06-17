
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

   
def enviar_email(subject, body, to_email):
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
    except Exception as e:
        print(f"Erro ao enviar o email: {e}")
    finally:
        server.quit()
    
