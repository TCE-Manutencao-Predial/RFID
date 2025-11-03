# Atualização: Campos de Número de Série e Número de Patrimônio

## Data: 03/11/2025

## Descrição das Alterações

Foi adicionado suporte para dois campos opcionais complementares nas etiquetas RFID:
- **Número de Série**: Identificação única do equipamento/material
- **Número de Patrimônio**: Número de controle patrimonial

## ✨ Colunas Adicionadas no Banco de Dados

As seguintes colunas foram adicionadas à tabela `etiquetasRFID`:
- `NumeroSerie` (VARCHAR 100, NULL) - com índice único
- `NumeroPatrimonio` (VARCHAR 100, NULL) - com índice único

**Nota**: As colunas já foram criadas no banco de dados. Código temporário de migrations foi removido após aplicação bem-sucedida.

## Alterações Realizadas

### 1. Interface de Usuário (HTML)

**Arquivo**: `app/templates/etiquetas.html`

Foram adicionados dois novos campos no modal "Editar Etiqueta":
- Campo de texto para Número de Série
- Campo de texto para Número de Patrimônio

**Layout**: Os campos estão dispostos **lado a lado** em uma grade 2 colunas para melhor aproveitamento do espaço.

Ambos os campos são opcionais e aparecem no modal de edição.

### 2. JavaScript (Frontend)

**Arquivo**: `app/static/js/etiquetas.js`

#### Função `editarEtiqueta()`
- Carrega os valores de `NumeroSerie` e `NumeroPatrimonio` da etiqueta via API
- Faz uma chamada assíncrona para buscar os dados completos da etiqueta

#### Função `salvarEtiqueta()`
- Coleta os valores dos novos campos
- Envia `NumeroSerie` e `NumeroPatrimonio` para o backend (somente se preenchidos)

### 3. CSS (Estilos)

**Arquivo**: `app/static/css/etiquetas.css`

#### Melhorias no Modal:
- Modal agora usa **Flexbox** para garantir layout correto
- `modal-body` com scroll independente do header e footer
- Botão "Salvar" sempre visível no rodapé
- Header e footer fixos, corpo rolável

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

1. **Editar uma etiqueta existente**
   - Clicar em "Editar" na etiqueta desejada
   - Preencher os campos "Número de Série" e/ou "Número de Patrimônio" (opcionais) que aparecem lado a lado
   - Rolar o modal se necessário (botão Salvar sempre visível no rodapé)
   - Clicar em "Salvar"

2. **Validação automática**
   - O sistema verifica se o número informado já existe
   - Em caso de duplicidade, exibe mensagem de erro
   - Se tudo estiver correto, salva e exibe mensagem de sucesso

## Notas Técnicas

- Os campos têm limite de **100 caracteres**
- A validação de duplicidade considera apenas valores não-nulos
- Etiquetas diferentes podem ter ambos os campos vazios (NULL)
- O sistema mantém compatibilidade com etiquetas antigas (sem esses campos)

## Testes Recomendados

### Funcionalidade
1. ✅ Editar uma etiqueta e adicionar número de série único
2. ✅ Editar uma etiqueta e adicionar número de patrimônio único
3. ✅ Tentar usar um número de série já cadastrado (deve falhar com aviso)
4. ✅ Tentar usar um número de patrimônio já cadastrado (deve falhar com aviso)
5. ✅ Deixar ambos os campos vazios (deve permitir)
6. ✅ Remover um número já cadastrado (definindo campo vazio)
7. ✅ Verificar que o modal permite scroll e botão Salvar está sempre visível
8. ✅ Verificar layout lado a lado dos campos em telas médias/grandes

## Arquivos Modificados

```
RFID/
├── app/
│   ├── templates/
│   │   └── etiquetas.html (MODIFICADO - campos lado a lado no modal)
│   ├── static/
│   │   ├── css/
│   │   │   └── etiquetas.css (MODIFICADO - modal flexbox com scroll correto)
│   │   └── js/
│   │       └── etiquetas.js (MODIFICADO - carregar e salvar novos campos)
│   └── utils/
│       └── GerenciadorEtiquetasRFID.py (MODIFICADO - validação de duplicidade)
└── ATUALIZACAO_CAMPOS_SERIE_PATRIMONIO.md (ATUALIZADO)
```

## Melhorias de UX

### Layout do Modal
- ✅ Campos Número de Série e Número de Patrimônio agora aparecem **lado a lado**
- ✅ Melhor aproveitamento do espaço horizontal
- ✅ Modal com sistema de **scroll inteligente**:
  - Header fixo no topo
  - Footer (botões) fixo na parte inferior
  - Corpo do formulário rolável entre header e footer
  - Botão "Salvar" **sempre visível**

### Responsividade
Em telas menores, os campos podem se reorganizar verticalmente automaticamente graças ao CSS Grid.

## Perguntas Frequentes

### Os campos aparecem no modal de criação também?

Não, por enquanto apenas no modal de **Edição**. Para adicionar na criação, seria necessário modificar a função `abrirModalNovaEtiqueta()`.

### Posso deixar os campos vazios?

Sim, ambos são **opcionais**. Valores vazios são armazenados como `NULL` no banco.

### E se eu tentar usar um número duplicado?

O sistema exibirá um **toast vermelho de erro** informando qual campo está duplicado (série ou patrimônio).

### O scroll do modal funciona em todos os navegadores?

Sim, o modal usa **Flexbox moderno** compatível com todos os navegadores atuais (Chrome, Firefox, Edge, Safari).

## Segurança

- ✅ Índices únicos no banco de dados previnem duplicações
- ✅ Validação server-side antes de salvar
- ✅ Campos limitados a 100 caracteres
- ✅ Sanitização automática pelo ORM (mysql.connector)
