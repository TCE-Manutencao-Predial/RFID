# API Reference - HelpDesk Monitor

Documentação completa das APIs públicas do sistema HelpDesk Monitor.

## 🌐 URL Base

```
https://automacao.tce.go.gov.br/helpdeskmonitor
```

## 🔐 Autenticação

### APIs Públicas (sem autenticação)
- Consulta de usuários htpasswd
- Consulta de técnicos
- Consulta de contatos TCE
- Consulta de grupos WhatsApp

### APIs Protegidas (Bearer Token)
**Token:** `whatsapp_api_token_2025_helpdeskmonitor_tce`

**Header necessário:**
```
Authorization: Bearer whatsapp_api_token_2025_helpdeskmonitor_tce
```

Endpoints que requerem token:
- Envio de emails
- Envio de mensagens WhatsApp

---

## 📋 Endpoints Disponíveis

### 👤 Usuários htpasswd

#### Listar todos os usuários htpasswd
```
GET /api/usuarios_htpasswd
```

**Resposta:**
```json
[
  {
    "usuario_htpasswd": "joao.silva",
    "nome": "João Silva",
    "cargo": "Técnico em Elétrica",
    "disponivel": true,
    "telefone_principal": "5562999999999",
    "ferias": false,
    "id": 1
  }
]
```

#### Buscar usuário htpasswd específico
```
GET /api/usuarios_htpasswd/{nome_usuario_htpasswd}
```

**Resposta:**
```json
{
  "id": 1,
  "nome": "João Silva",
  "cargo": "Técnico em Elétrica",
  "telefone_principal": "5562999999999",
  "email": "joao.silva@tce.go.gov.br",
  "nome_usuario_htpasswd": "joao.silva",
  "disponivel": true,
  "ferias": false
}
```

#### Enviar mensagem WhatsApp para usuário htpasswd
```
POST /api/usuarios_htpasswd/{nome_usuario_htpasswd}/enviar_mensagem
```

**Body:**
```json
{
  "mensagem": "Texto da mensagem",
  "origem_api": "SISTEMA_ORIGEM",
  "force": false
}
```

**Resposta (202 Accepted):**
```json
{
  "message": "Mensagem enfileirada para envio",
  "status": "enfileirado",
  "job_id": "job_123456789",
  "usuario_htpasswd": "joao.silva",
  "telefone_principal": "5562999999999",
  "force": false
}
```

---

### 👷 Técnicos

#### Listar todos os técnicos (completo)
```
GET /api/contatos_tecnicos
```

**Resposta:**
```json
[
  {
    "id": 1,
    "nome": "João Silva",
    "cargo": "Técnico em Elétrica",
    "telefone": "5562999999999",
    "email": "joao.silva@tce.go.gov.br",
    "ramal": "1234",
    "ferias": false,
    "ativo": true,
    "funcoes": ["ELETRICA", "ILUMINACAO"],
    "jornada": [
      {
        "dia_semana": 0,
        "hora_inicio": "08:00",
        "hora_fim": "17:00"
      }
    ],
    "nome_usuario_htpasswd": "joao.silva",
    "disponivel_agora": true,
    "grupos_whatsapp": [1, 2]
  }
]
```

#### Listar técnicos (resumido)
```
GET /api/contatos_tecnicos/listar
```

**Resposta:**
```json
{
  "tecnicos": [
    {
      "id": 1,
      "nome": "João Silva",
      "cargo": "Técnico em Elétrica"
    }
  ],
  "sucesso": true,
  "total": 1
}
```

#### Buscar técnico por nome
```
GET /api/contatos_tecnicos/nome/{nome_contato}
```

**Resposta:**
```json
{
  "id": 1,
  "nome": "João Silva",
  "cargo": "Técnico em Elétrica",
  "telefone_principal": "5562999999999",
  "email": "joao.silva@tce.go.gov.br"
}
```

#### Listar técnicos por função/competência ⭐ NOVO
```
GET /api/tecnicos/por_funcao/{funcao}
```

**Exemplo:**
```bash
curl "https://automacao.tce.go.gov.br/helpdeskmonitor/api/tecnicos/por_funcao/limpeza"
```

**Resposta:**
```json
{
  "tecnicos": [
    {
      "id": 5,
      "nome": "Carlos Mendes",
      "cargo": "Auxiliar de Limpeza",
      "usuario_htpasswd": "carlos.mendes",
      "disponivel": true,
      "ferias": false,
      "telefone_principal": "5562966666666",
      "email": "carlos.mendes@tce.go.gov.br"
    }
  ],
  "funcao_pesquisada": "limpeza",
  "funcao_normalizada": "LIMPEZA",
  "total": 1
}
```

**Funções disponíveis:** LIMPEZA, ELETRICA, AR_CONDICIONADO, HIDRAULICA, ILUMINACAO, MARCENARIA, PINTURA, REFRIGERACAO, SERRALHERIA, ALVENARIA, JARDINAGEM

**Características:**
- Case-insensitive (limpeza = LIMPEZA)
- Retorna técnicos com `usuario_htpasswd` (pode ser null)
- Normalização automática de nomes de função

---

### 👥 Contatos TCE (Servidores)

#### Listar contatos TCE
```
GET /api/contatos_tce
```

**Resposta:**
```json
[
  {
    "id": 1,
    "nome": "Dr. Pedro Costa",
    "cargo": "Auditor",
    "telefone": "5562988888888",
    "lotacao": "Diretoria Administrativa",
    "propaganda_autorizada": true,
    "observacoes": ""
  }
]
```

---

### 👥 Grupos WhatsApp

#### Listar grupos WhatsApp
```
GET /api/grupos-whatsapp/listar
```

**Resposta:**
```json
{
  "grupos": [
    {
      "id": 1,
      "nome": "Equipe Elétrica",
      "telefone_grupo": "5562999999999@g.us",
      "descricao": "Grupo dos técnicos de elétrica",
      "funcoes": ["ELETRICA", "ILUMINACAO"]
    }
  ],
  "sucesso": true,
  "total": 1
}
```

---

### 📧 Email (Requer Autenticação)

#### Enviar email
```
POST /api/email/send
```

**Headers:**
```
Authorization: Bearer whatsapp_api_token_2025_helpdeskmonitor_tce
Content-Type: application/json
```

**Body:**
```json
{
  "email": "destino@tce.go.gov.br",
  "assunto": "Assunto do email",
  "mensagem": "Corpo do email",
  "reply_to": "opcional@tce.go.gov.br"
}
```

**Resposta:**
```json
{
  "sucesso": true,
  "mensagem": "E-mail enviado com sucesso",
  "codigo": 200,
  "timestamp": "2025-10-29T14:30:00"
}
```

**Variações:**
- `email`: string ou array de strings (múltiplos destinatários)
- `nome`: enviar por nome do contato ao invés de email
- `html`: true + `corpo_html`: para emails HTML

#### Enviar email por função
```
POST /api/email/send-by-function
```

**Body:**
```json
{
  "funcao": "ELETRICA",
  "assunto": "Assunto",
  "mensagem": "Mensagem"
}
```

---

### 💬 WhatsApp (Requer Autenticação)

#### Enviar mensagem WhatsApp
```
POST /api/whatsapp/send
```

**Headers:**
```
Authorization: Bearer whatsapp_api_token_2025_helpdeskmonitor_tce
Content-Type: application/json
```

**Body:**
```json
{
  "telefone": "5562999999999",
  "mensagem": "Texto da mensagem",
  "origem_api": "SISTEMA_ORIGEM"
}
```

**Resposta:**
```json
{
  "sucesso": true,
  "mensagem": "Mensagem enviada com sucesso",
  "timestamp": "2025-10-29T14:30:00"
}
```

---

## 📊 Exemplos de Uso

### PowerShell

```powershell
# Listar usuários htpasswd
$usuarios = Invoke-RestMethod -Uri "https://automacao.tce.go.gov.br/helpdeskmonitor/api/usuarios_htpasswd"
$usuarios | Format-Table usuario_htpasswd, nome, disponivel

# Buscar técnicos de limpeza
$tecnicos = Invoke-RestMethod -Uri "https://automacao.tce.go.gov.br/helpdeskmonitor/api/tecnicos/por_funcao/limpeza"
$tecnicos.tecnicos | Format-Table nome, usuario_htpasswd, disponivel

# Enviar email (com autenticação)
$headers = @{
    "Authorization" = "Bearer whatsapp_api_token_2025_helpdeskmonitor_tce"
}
$body = @{
    email = "destino@tce.go.gov.br"
    assunto = "Teste"
    mensagem = "Mensagem de teste"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://automacao.tce.go.gov.br/helpdeskmonitor/api/email/send" `
    -Method Post -Headers $headers -ContentType "application/json" -Body $body
```

### Bash/curl

```bash
# Listar usuários htpasswd
curl -s "https://automacao.tce.go.gov.br/helpdeskmonitor/api/usuarios_htpasswd" | jq '.'

# Buscar técnicos de limpeza
curl -s "https://automacao.tce.go.gov.br/helpdeskmonitor/api/tecnicos/por_funcao/limpeza" | \
  jq '.tecnicos[] | {nome, htpasswd: .usuario_htpasswd, disponivel}'

# Enviar email (com autenticação)
curl -X POST "https://automacao.tce.go.gov.br/helpdeskmonitor/api/email/send" \
  -H "Authorization: Bearer whatsapp_api_token_2025_helpdeskmonitor_tce" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "destino@tce.go.gov.br",
    "assunto": "Teste",
    "mensagem": "Mensagem de teste"
  }'
```

### Python

```python
import requests

BASE_URL = "https://automacao.tce.go.gov.br/helpdeskmonitor"
TOKEN = "whatsapp_api_token_2025_helpdeskmonitor_tce"

# Listar usuários htpasswd
response = requests.get(f"{BASE_URL}/api/usuarios_htpasswd")
usuarios = response.json()

# Buscar técnicos de limpeza
response = requests.get(f"{BASE_URL}/api/tecnicos/por_funcao/limpeza")
tecnicos = response.json()

# Enviar email (com autenticação)
headers = {"Authorization": f"Bearer {TOKEN}"}
data = {
    "email": "destino@tce.go.gov.br",
    "assunto": "Teste",
    "mensagem": "Mensagem de teste"
}
response = requests.post(
    f"{BASE_URL}/api/email/send",
    headers=headers,
    json=data
)
```

---

## 🔍 Códigos de Status HTTP

| Código | Descrição |
|--------|-----------|
| 200 | OK - Sucesso |
| 202 | Accepted - Requisição aceita (processamento assíncrono) |
| 400 | Bad Request - Parâmetros inválidos |
| 401 | Unauthorized - Token de autenticação inválido ou ausente |
| 404 | Not Found - Recurso não encontrado |
| 500 | Internal Server Error - Erro no servidor |

---

## 📝 Notas Importantes

1. **Encoding de URL**: Use URL encoding para nomes com espaços (ex: `João Silva` → `João%20Silva`)

2. **Disponibilidade**: O campo `disponivel_agora` considera:
   - Jornada de trabalho
   - Status de férias
   - Dia da semana e horário atual

3. **Dia da semana**: Na jornada, `dia_semana` usa o padrão Python:
   - 0 = Segunda-feira
   - 6 = Domingo

4. **Normalização de funções**: Funções são automaticamente normalizadas (remove acentos, converte para maiúsculas, substitui espaços por underscores)

5. **Envio assíncrono**: Mensagens WhatsApp são enfileiradas e processadas de forma assíncrona

6. **Token de API**: Mantenha o token seguro. Não o exponha em repositórios públicos ou código cliente

---

## 🆘 Suporte

Para dúvidas ou problemas, entre em contato com a equipe de TI do TCE-GO.
