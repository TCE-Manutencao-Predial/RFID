# Correção da Configuração do Apache para Passar REMOTE_USER

## Problema

O Apache está fazendo autenticação HTTP Basic Auth, mas não está passando a variável `REMOTE_USER` para a aplicação Flask que roda via Waitress (WSGI server) na porta 5074.

## Sintomas

- Logs mostram: `Usuário 'None' tentou acessar...`
- Erro 403 Forbidden para todos os usuários
- Sistema de competências não funciona porque não identifica o usuário

## Solução

### 1. Localizar o arquivo de configuração do Apache

O arquivo de configuração do VirtualHost deve estar em:
- `/etc/httpd/conf.d/automacao.tce.go.gov.br.conf` ou
- `/etc/httpd/sites-available/automacao.tce.go.gov.br.conf`

### 2. Adicionar as diretivas necessárias

Dentro da seção `<Location /RFID>` ou equivalente, adicione:

```apache
<Location /RFID>
    # Autenticação HTTP Basic
    AuthType Basic
    AuthName "Área restrita"
    AuthUserFile /etc/httpd/.htpasswd
    Require valid-user
    
    # IMPORTANTE: Passar o usuário autenticado para o proxy
    RequestHeader set REMOTE_USER %{REMOTE_USER}s
    RequestHeader set X-Remote-User %{REMOTE_USER}s
    
    # Proxy reverso para Waitress
    ProxyPass http://127.0.0.1:5074
    ProxyPassReverse http://127.0.0.1:5074
    
    # Preservar informações do proxy
    ProxyPreserveHost On
</Location>
```

### 3. Habilitar módulos necessários

Certifique-se de que os módulos estão habilitados:

```bash
sudo a2enmod headers
sudo a2enmod proxy
sudo a2enmod proxy_http
```

Ou para RHEL/CentOS, verifique se estão carregados em `/etc/httpd/conf.modules.d/`:

```bash
sudo grep -r "mod_headers\|mod_proxy" /etc/httpd/conf.modules.d/
```

### 4. Reiniciar o Apache

```bash
sudo systemctl restart httpd
```

### 5. Testar a configuração

Acesse o endpoint de debug (após fazer login):
```
https://automacao.tce.go.gov.br/RFID/debug/auth
```

Você deve ver algo como:
```json
{
  "usuario_detectado": "pedro",
  "competencias": ["RFID", "TI"],
  "pode_acessar_sistema": true,
  "pode_acessar_ping": true,
  "environ": {
    "REMOTE_USER": "pedro",
    ...
  }
}
```

Se `usuario_detectado` ainda for `null`, verifique os headers HTTP.

## Alternativa: Configuração no .htaccess

Se não puder modificar o VirtualHost, tente adicionar ao arquivo `.htaccess` em `/var/www/automacao.tce.go.gov.br/RFID/`:

```apache
AuthType Basic
AuthName "Área restrita"
AuthUserFile /etc/httpd/.htpasswd
Require valid-user

# Passar o usuário autenticado
RequestHeader set REMOTE_USER %{REMOTE_USER}s
RequestHeader set X-Remote-User %{REMOTE_USER}s
```

**NOTA:** `.htaccess` requer `AllowOverride All` no VirtualHost.

## Verificação Adicional

Se o problema persistir, modifique o código Python para também verificar headers HTTP:

O código em `app/routes/web.py` já foi atualizado para verificar:
1. `request.environ.get('REMOTE_USER')`
2. `request.environ.get('HTTP_REMOTE_USER')`  
3. `request.headers.get('X-Remote-User')` (novo)
4. `request.headers.get('Remote-User')` (novo)

Adicione esta linha na função `obter_usuario_atual()` se necessário:

```python
usuario = (request.environ.get('REMOTE_USER') or 
           request.environ.get('HTTP_REMOTE_USER') or
           request.headers.get('X-Remote-User') or
           request.headers.get('Remote-User') or
           getattr(request, 'remote_user', None) or '')
```

## Comandos de Diagnóstico

```bash
# Ver logs do Apache
sudo tail -f /var/log/httpd/error_log
sudo tail -f /var/log/httpd/access_log

# Ver logs da aplicação RFID
sudo journalctl -u RFID.service -f

# Testar autenticação básica
curl -u usuario:senha https://automacao.tce.go.gov.br/RFID/debug/auth
```

## Referências

- [Apache mod_headers](https://httpd.apache.org/docs/2.4/mod/mod_headers.html)
- [Flask ProxyFix](https://flask.palletsprojects.com/en/2.3.x/deploying/proxy_fix/)
- [Waitress Documentation](https://docs.pylonsproject.org/projects/waitress/)
