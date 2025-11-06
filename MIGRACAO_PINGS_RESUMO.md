# Resumo da Migração para Tabela pingsRFID

## Comando SQL de Migração

```sql
-- Migrar registros PING da tabela leitoresRFID para pingsRFID
INSERT INTO pingsRFID (Horario, Foto, Local, antena)
SELECT 
    Horario,
    Foto,
    CASE 
        WHEN CodigoLeitor = 'B1' THEN 'B1'
        WHEN CodigoLeitor = 'B2' THEN 'B2'
        WHEN CodigoLeitor = 'S1' THEN 'S1'
        ELSE NULL  -- Ajuste se houver outros códigos
    END AS Local,
    Antena AS antena
FROM leitoresRFID
WHERE EtiquetaRFID_hex LIKE 'PING_PERIODICO_%'
  AND Foto IS NOT NULL;

-- Após migração e validação, remover da tabela original:
DELETE FROM leitoresRFID 
WHERE EtiquetaRFID_hex LIKE 'PING_PERIODICO_%';
```

## Alterações Realizadas no Backend

### 1. `app/utils/GerenciadorPingRFID.py` ✅
- **Atualizado** para acessar tabela `pingsRFID`
- Removido método `_obter_pings_incremental` (não mais necessário)
- Removido método `obter_pings_por_etiqueta` (pings não têm mais etiqueta)
- **Alterado** `obter_antenas_com_leitor` → `obter_locais_com_antena`
- **Alterada** estrutura de dados retornada:
  - `codigo_leitor` → `local`
  - `etiqueta_hex` → removido
  - `RSSI` → removido
  - `antena_completa` → `local_antena`

### 2. `app/routes/api_ping.py` ✅
- **Removidos endpoints**:
  - `/ping/etiqueta/<etiqueta_hex>` (histórico por etiqueta)
  - `/ping/ultimos/<minutos>` (substituído por filtros de data)
  - `/ping/antenas` (GET)
  - `/ping/foto/<etiqueta_hex>` (GET)
  - `/ping/foto/info/<etiqueta_hex>` (GET)

- **Novos/Atualizados endpoints**:
  - `/ping/locais` (GET) - Lista locais e antenas
  - `/ping/foto` (GET com query params: local, antena, horario)
  - `/ping/foto/info` (GET com query params: local, antena, horario)

- **Filtros atualizados** em `/ping`:
  - `etiqueta` → removido
  - `local` → adicionado (B1, B2, S1)
  - `antena` → mantido (apenas número)

## Alterações Necessárias no Frontend

### 3. `app/templates/ping.html` - PENDENTE ⚠️

**Remover campos**:
```html
<!-- REMOVER: -->
<div class="rfid-filter-group">
  <label class="rfid-filter-label"> <i class="fas fa-barcode"></i> Código da Etiqueta </label>
  <input type="text" id="filtroEtiqueta" class="rfid-filter-input" placeholder="Digite o código PING..." />
</div>

<div class="rfid-filter-group">
  <label class="rfid-filter-label"> <i class="fas fa-clock"></i> PINGs Recentes </label>
  <select id="filtroRecentes" class="rfid-filter-select">
    <option value="">Todos</option>
    <option value="5">Últimos 5 minutos</option>
    <!-- ... -->
  </select>
</div>
```

**Adicionar campos**:
```html
<!-- ADICIONAR: -->
<div class="rfid-filter-group">
  <label class="rfid-filter-label"> <i class="fas fa-map-marker-alt"></i> Local </label>
  <select id="filtroLocal" class="rfid-filter-select">
    <option value="">Todos os Locais</option>
    <option value="B1">B1</option>
    <option value="B2">B2</option>
    <option value="S1">S1</option>
  </select>
</div>
```

**Atualizar cabeçalho da tabela**:
```html
<!-- DE: -->
<thead>
  <tr>
    <th>Horário</th>
    <th>Leitor</th>
    <th>Antena</th>
    <th>Código</th>
    <th>RSSI</th>
    <th>Ações</th>
  </tr>
</thead>

<!-- PARA: -->
<thead>
  <tr>
    <th>Horário</th>
    <th>Local</th>
    <th>Antena</th>
    <th>Ações</th>
  </tr>
</thead>
```

**Remover estatística "PINGs Únicos"**:
```html
<!-- REMOVER este card: -->
<div class="rfid-stat-card">
  <i class="fas fa-tag rfid-stat-icon"></i>
  <h2 class="rfid-stat-value" id="pingsUnicos">0</h2>
  <p class="rfid-stat-label">PINGs Únicos</p>
</div>
```

### 4. `app/static/js/ping.js` - PARCIALMENTE ATUALIZADO ⚠️

**Já atualizados** ✅:
- `formatarEtiquetaRFID` → `formatarLocalAntena`
- `antenasDisponiveis` → `locaisDisponiveis`
- `inicializarEventos` - removido filtro de etiqueta e recentes
- `obterFiltros` - atualizado para `local` e `antena`
- `renderizarTabela` - atualizada estrutura da tabela
- `carregarAntenas` → `carregarLocais`
- `verFotoPing` - atualizada assinatura (local, antena, horario)

**Funções a REMOVER** ⚠️:
- `verDetalhesPing(codigo)` - não há mais histórico por etiqueta
- `carregarHistoricoPing(codigo)` - mesmo motivo
- `navegarFoto` - removida navegação entre fotos de mesma etiqueta
- `getRSSIClass(rssi)` - RSSI não existe mais

**Funções a ATUALIZAR** ⚠️:
- `downloadFoto(codigo, codigoLeitor, antena, horario)` → `downloadFoto(local, antena, horario)`
- `exportarDados()` - remover colunas de etiqueta e RSSI
- `carregarEstatisticas` - remover referência a `pings_unicos`

### 5. `app/static/css/ping.css` - OPCIONAL

**Classes CSS a revisar**:
- `.ping-badge` - pode ser removida (era para código de etiqueta)
- `.rssi-indicator`, `.rssi-bars`, `.rssi-value` - remover (RSSI não existe mais)
- `.local-badge` - adicionar/estilizar para locais (B1, B2, S1)

## Testes Recomendados

1. **Após migração SQL**:
   - Verificar quantidade de registros migrados
   - Validar mapeamento Local ↔ CodigoLeitor
   - Conferir se todas as fotos foram migradas

2. **Backend**:
   - GET `/RFID/api/ping` - listagem funcionando
   - GET `/RFID/api/ping/estatisticas` - sem `pings_unicos`
   - GET `/RFID/api/ping/locais` - retorna locais e antenas
   - GET `/RFID/api/ping/foto?local=B1&antena=1&horario=...` - foto carrega

3. **Frontend**:
   - Filtros por Local e Antena funcionando
   - Tabela exibindo: Horário, Local, Antena, Ações
   - Botão "Ver Foto" abrindo modal corretamente
   - Estatísticas corretas (sem PINGs Únicos)

## Arquivos Modificados

- ✅ `app/utils/GerenciadorPingRFID.py` - COMPLETO
- ✅ `app/routes/api_ping.py` - COMPLETO
- ⚠️ `app/static/js/ping.js` - PARCIAL (funções de navegação/histórico precisam ser removidas)
- ⚠️ `app/templates/ping.html` - PENDENTE (atualizar filtros e tabela)
- ❓ `app/static/css/ping.css` - OPCIONAL (revisar classes CSS)

## Próximos Passos

1. Executar o comando SQL de migração no MySQL Workbench
2. Finalizar ajustes no `ping.html` (filtros e estrutura da tabela)
3. Remover funções obsoletas do `ping.js`
4. Testar toda a funcionalidade
5. Se tudo estiver ok, executar o DELETE dos registros da tabela antiga
