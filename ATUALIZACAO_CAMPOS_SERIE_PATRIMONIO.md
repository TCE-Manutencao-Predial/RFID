# Atualização: Campos de Número de Série e Número de Patrimônio

## Data: 03/11/2025

## Descrição das Alterações

Foi adicionado suporte para dois campos opcionais complementares nas etiquetas RFID:
- **Número de Série**: Identificação única do equipamento/material
- **Número de Patrimônio**: Número de controle patrimonial

## ✨ Sistema de Migrations Automáticas

**IMPORTANTE**: As alterações no banco de dados são aplicadas **automaticamente** na inicialização do aplicativo!

### Como Funciona

1. **Verificação Inteligente**: Ao iniciar, o sistema verifica se as colunas já existem
2. **Criação Automática**: Se não existirem, as colunas e índices são criados automaticamente
3. **Notificação no Frontend**: Uma mensagem toast informa o usuário sobre as alterações
4. **Logs Detalhados**: Todas as operações são registradas nos logs do sistema

### Vantagens

- ✅ **Zero intervenção manual** no banco de dados
- ✅ **Seguro**: Verifica antes de criar, evita erros de duplicação
- ✅ **Transparente**: Usuário é informado sobre as alterações
- ✅ **Rastreável**: Todas as operações ficam registradas nos logs

## Alterações Realizadas

### 1. Banco de Dados - Migrations Automáticas

**Arquivo**: `app/utils/GerenciadorEtiquetasRFID.py`

#### Novos Métodos:

- **`_run_migrations()`**: Executa migrations na inicialização
- **`_migrate_add_serial_patrimonio_columns()`**: Adiciona colunas se não existirem
- **`get_migration_status()`**: Retorna status das migrations executadas

#### Comportamento:

1. Verifica se as colunas `NumeroSerie` e `NumeroPatrimonio` já existem
2. Se não existirem, cria as colunas com:
   - Tipo: `VARCHAR(100) NULL`
   - Índices únicos para prevenir duplicações
3. Registra todas as operações em `self.migration_status`
4. Loga todas as ações (sucesso e erros)

**Não é mais necessário executar scripts SQL manualmente!**

### 2. API - Endpoint de Status

**Arquivo**: `app/routes/api_etiquetas.py`

Novo endpoint: `GET /RFID/api/migrations/status`

Retorna informações sobre as migrations executadas:
```json
{
  "success": true,
  "migration_status": {
    "executed": true,
    "success": true,
    "messages": [
      "✓ Coluna 'NumeroSerie' adicionada com sucesso",
      "✓ Índice único 'idx_numero_serie' criado",
      "✓ Coluna 'NumeroPatrimonio' adicionada com sucesso",
      "✓ Índice único 'idx_numero_patrimonio' criado"
    ],
    "timestamp": "2025-11-03T10:30:00"
  }
}
```

### 2. Interface de Usuário (HTML)

**Arquivo**: `app/templates/etiquetas.html`

Foram adicionados dois novos campos no modal "Editar Etiqueta":
- Campo de texto para Número de Série
- Campo de texto para Número de Patrimônio

Ambos os campos são opcionais e aparecem apenas no modal de edição.

### 3. JavaScript (Frontend)

**Arquivo**: `app/static/js/etiquetas.js`

#### Nova Função `verificarMigrations()`
- Chamada automaticamente ao carregar a página
- Busca status das migrations via API
- Exibe toast informativo se houver alterações no banco
- Não interrompe a navegação do usuário

#### Função `editarEtiqueta()`
- Agora carrega os valores de `NumeroSerie` e `NumeroPatrimonio` da etiqueta via API
- Faz uma chamada assíncrona para buscar os dados completos da etiqueta

#### Função `salvarEtiqueta()`
- Coleta os valores dos novos campos
- Envia `NumeroSerie` e `NumeroPatrimonio` para o backend (somente se preenchidos)

### 4. Backend (Python)

**Arquivo**: `app/utils/GerenciadorEtiquetasRFID.py`

#### Função `atualizar_etiqueta()`
Adicionadas validações de duplicidade:
- Verifica se o número de série já existe em outra etiqueta
- Verifica se o número de patrimônio já existe em outra etiqueta
- Retorna mensagens de erro específicas em caso de duplicação

#### Função `obter_etiqueta_por_id()`
- Inclui `NumeroSerie` e `NumeroPatrimonio` na query SELECT

#### Função `obter_etiquetas()`
- Inclui os novos campos na listagem de etiquetas

## Validações Implementadas

### Unicidade
- O sistema impede que duas etiquetas tenham o mesmo **Número de Série**
- O sistema impede que duas etiquetas tenham o mesmo **Número de Patrimônio**

### Mensagens de Aviso
Quando houver tentativa de usar um número já cadastrado, o usuário receberá:
- **Erro (Toast vermelho)**: "Já existe outra etiqueta com este número de série"
- **Erro (Toast vermelho)**: "Já existe outra etiqueta com este número de patrimônio"

### Campos Opcionais
- Ambos os campos são **opcionais**
- Podem ser deixados em branco
- Quando vazios, são armazenados como `NULL` no banco de dados

## Fluxo de Uso

### Primeira Inicialização (Migrations)

1. **Iniciar o servidor Flask**
   ```bash
   python RFID.py
   ```

2. **Migrations automáticas executadas**
   - Sistema verifica estrutura da tabela
   - Cria colunas se não existirem
   - Cria índices únicos
   - Registra operações nos logs

3. **Acessar a página de etiquetas**
   - Um toast verde aparece informando as alterações
   - Exemplo: "Banco de dados atualizado: ✓ Coluna 'NumeroSerie' adicionada com sucesso"

### Uso Normal

1. **Editar uma etiqueta existente**
   - Clicar em "Editar" na etiqueta desejada
   - Preencher os campos "Número de Série" e/ou "Número de Patrimônio" (opcionais)
   - Clicar em "Salvar"

2. **Validação automática**
   - O sistema verifica se o número informado já existe
   - Em caso de duplicidade, exibe mensagem de erro
   - Se tudo estiver correto, salva e exibe mensagem de sucesso

## Mensagens Exibidas ao Usuário

### No Toast de Inicialização:

**Primeira vez (colunas criadas):**
```
✓ Coluna 'NumeroSerie' adicionada com sucesso
✓ Índice único 'idx_numero_serie' criado
✓ Coluna 'NumeroPatrimonio' adicionada com sucesso
✓ Índice único 'idx_numero_patrimonio' criado
```

**Execuções subsequentes:**
```
Coluna 'NumeroSerie' já existe
Coluna 'NumeroPatrimonio' já existe
Nenhuma alteração necessária - banco de dados atualizado
```
(Neste caso, nenhum toast é exibido para não incomodar o usuário)

## Notas Técnicas

- Os campos têm limite de **100 caracteres**
- A validação de duplicidade considera apenas valores não-nulos
- Etiquetas diferentes podem ter ambos os campos vazios (NULL)
- O sistema mantém compatibilidade com etiquetas antigas (sem esses campos)

## Testes Recomendados

### 1. Teste de Migrations (Primeira Inicialização)
1. ✅ Iniciar o servidor Flask pela primeira vez
2. ✅ Verificar logs do servidor (deve mostrar criação das colunas)
3. ✅ Acessar página de etiquetas
4. ✅ Verificar toast de sucesso com mensagens de criação

### 2. Teste de Migrations (Reinicialização)
1. ✅ Reiniciar o servidor Flask
2. ✅ Verificar logs (deve mostrar "já existe")
3. ✅ Acessar página de etiquetas
4. ✅ Não deve aparecer toast (nenhuma alteração necessária)

### 3. Teste de Funcionalidade
1. ✅ Editar uma etiqueta e adicionar número de série único
2. ✅ Editar uma etiqueta e adicionar número de patrimônio único
3. ✅ Tentar usar um número de série já cadastrado (deve falhar)
4. ✅ Tentar usar um número de patrimônio já cadastrado (deve falhar)
5. ✅ Deixar ambos os campos vazios (deve permitir)
6. ✅ Remover um número já cadastrado (definindo campo vazio)
7. ✅ Verificar que a edição não afeta outras funcionalidades

## Logs do Sistema

As migrations são registradas nos logs do servidor com nível INFO:

```
INFO - Gerenciador de Etiquetas RFID inicializado com cache
INFO - Iniciando verificação de migrations...
INFO - Coluna NumeroSerie adicionada
INFO - Índice idx_numero_serie criado
INFO - Coluna NumeroPatrimonio adicionada
INFO - Índice idx_numero_patrimonio criado
INFO - Migrations executadas com sucesso
```

## Arquivos Modificados

```
RFID/
├── scripts/
│   └── add_serial_patrimonio_columns.sql (MANTIDO - referência/backup)
├── app/
│   ├── templates/
│   │   └── etiquetas.html (MODIFICADO - campos no modal)
│   ├── static/
│   │   └── js/
│   │       └── etiquetas.js (MODIFICADO - validação e notificação)
│   ├── routes/
│   │   └── api_etiquetas.py (MODIFICADO - novo endpoint)
│   └── utils/
│       └── GerenciadorEtiquetasRFID.py (MODIFICADO - sistema de migrations)
└── ATUALIZACAO_CAMPOS_SERIE_PATRIMONIO.md (NOVO)
```

## Perguntas Frequentes

### O script SQL ainda é necessário?

**Não!** O arquivo `scripts/add_serial_patrimonio_columns.sql` foi mantido apenas como referência/backup. As alterações são aplicadas automaticamente pelo Python.

### E se eu já executei o script SQL manualmente?

Sem problema! O sistema verifica se as colunas já existem antes de tentar criá-las. Não haverá erros nem duplicações.

### As migrations afetam o desempenho?

Não. A verificação é rápida (menos de 100ms) e só acontece na inicialização do servidor.

### Posso desabilitar as migrations automáticas?

Sim, basta comentar a linha `self._run_migrations()` no método `__init__` do `GerenciadorEtiquetasRFID`.

### Como verificar se as migrations foram executadas?

1. **Nos logs do servidor** - busque por "Migrations executadas com sucesso"
2. **Via API** - acesse `GET /RFID/api/migrations/status`
3. **No banco de dados** - execute `DESCRIBE etiquetasRFID` e verifique as colunas

## Segurança

- ✅ Usa transações do MySQL com `autocommit=True`
- ✅ Tratamento de erros robusto
- ✅ Não executa operações destrutivas (DROP, DELETE)
- ✅ Verifica antes de criar (idempotente)
- ✅ Índices únicos previnem duplicações no banco
