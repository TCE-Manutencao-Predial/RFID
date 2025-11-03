-- Script de otimização para queries de PING RFID
-- Autor: Sistema de otimização automática
-- Data: 2025-11-03
-- Objetivo: Acelerar queries da página de PING que estavam excedendo timeout
-- Versão: 4.0 - BUSCA INCREMENTAL (sem necessidade de novos índices)

-- ============================================================================
-- ANÁLISE DO PROBLEMA E SOLUÇÃO
-- ============================================================================
-- PROBLEMA:
-- 1. Erro: "1028 (HY000): Sort aborted: Query execution was interrupted"
-- 2. ORDER BY Horario DESC em milhões de registros causava timeout
-- 3. Criação de novos índices é demorada e bloqueia a tabela

-- SOLUÇÃO IMPLEMENTADA (v4.0):
-- Em vez de ORDER BY em toda a tabela, o sistema agora usa BUSCA INCREMENTAL:
-- - Busca dados em chunks de 7 dias (dos mais recentes para os mais antigos)
-- - Para cada chunk, ORDER BY é rápido (poucos registros por semana)
-- - Para até encontrar a quantidade de registros solicitada
-- - Máximo de 90 dias de busca

-- VANTAGENS:
-- ✅ Não precisa criar novos índices (economia de tempo e espaço)
-- ✅ Usa os índices existentes eficientemente
-- ✅ Performance previsível (cada chunk é pequeno)
-- ✅ Não trava a tabela para criar índices

-- ============================================================================
-- ÍNDICES EXISTENTES (suficientes para busca incremental)
-- ============================================================================
-- Os índices já criados na v2 são suficientes:
-- - idx_ping_optimized_v2: (EtiquetaRFID_hex, Horario DESC, Foto, CodigoLeitor, Antena)

-- VERIFICAR ÍNDICES EXISTENTES:
SHOW INDEX FROM leitoresRFID WHERE Key_name LIKE '%ping%';

-- ============================================================================
-- NENHUMA AÇÃO NECESSÁRIA
-- ============================================================================
-- A versão 4.0 funciona com os índices existentes.
-- Não é necessário criar novos índices nem executar este script.
-- O código da aplicação foi modificado para usar busca incremental automaticamente.

-- ============================================================================
-- ÍNDICE ADICIONAL PARA ESTATÍSTICAS
-- ============================================================================
-- Para acelerar queries de agregação (COUNT, MIN, MAX)
DROP INDEX IF EXISTS idx_ping_stats ON leitoresRFID;
CREATE INDEX idx_ping_stats 
ON leitoresRFID (EtiquetaRFID_hex(25), Horario);

-- ============================================================================
-- ÍNDICE PARA FILTROS POR ANTENA
-- ============================================================================
-- Acelera filtros específicos por leitor e antena
DROP INDEX IF EXISTS idx_ping_antenna ON leitoresRFID;
CREATE INDEX idx_ping_antenna 
ON leitoresRFID (CodigoLeitor, Antena, Horario DESC);

-- ============================================================================
-- ANÁLISE DE PERFORMANCE
-- ============================================================================
-- Execute EXPLAIN nas queries principais para verificar uso dos índices:

EXPLAIN 
SELECT 
    l.CodigoLeitor,
    l.Horario,
    l.Antena,
    l.EtiquetaRFID_hex,
    l.RSSI
FROM leitoresRFID l
WHERE l.EtiquetaRFID_hex LIKE 'PING_PERIODICO_%' 
  AND l.Foto IS NOT NULL
ORDER BY l.Horario DESC
LIMIT 50 OFFSET 0;

-- Deve mostrar:
-- - type: range ou ref
-- - possible_keys: idx_ping_optimized_v2
-- - key: idx_ping_optimized_v2
-- - Extra: Using index condition (SEM "Using filesort"!)

-- ============================================================================
-- ESTATÍSTICAS DA TABELA
-- ============================================================================
-- Verificar quantos registros PING existem
SELECT 
    COUNT(*) as total_pings,
    COUNT(DISTINCT EtiquetaRFID_hex) as etiquetas_unicas,
    COUNT(DISTINCT CONCAT(CodigoLeitor, ':', Antena)) as antenas_unicas,
    MIN(Horario) as primeiro_ping,
    MAX(Horario) as ultimo_ping,
    AVG(CASE WHEN Foto IS NOT NULL THEN LENGTH(Foto) ELSE 0 END) as tamanho_medio_foto_bytes,
    SUM(CASE WHEN Foto IS NOT NULL THEN 1 ELSE 0 END) as pings_com_foto,
    SUM(CASE WHEN Foto IS NULL THEN 1 ELSE 0 END) as pings_sem_foto
FROM leitoresRFID
WHERE EtiquetaRFID_hex LIKE 'PING_PERIODICO_%';

-- ============================================================================
-- MANUTENÇÃO DOS ÍNDICES
-- ============================================================================
-- Executar periodicamente para otimizar os índices:
-- OPTIMIZE TABLE leitoresRFID;
-- ANALYZE TABLE leitoresRFID;

-- ============================================================================
-- ROLLBACK (se necessário)
-- ============================================================================
-- Para remover os índices criados:
-- DROP INDEX idx_ping_optimized_v2 ON leitoresRFID;
-- DROP INDEX idx_ping_stats ON leitoresRFID;
-- DROP INDEX idx_ping_antenna ON leitoresRFID;

-- ============================================================================
-- CONFIGURAÇÕES ADICIONAIS DO MYSQL (opcional)
-- ============================================================================
-- Para melhorar performance geral de queries PING:

-- Aumentar timeout de execução de queries (em sessão ou global)
-- SET SESSION MAX_EXECUTION_TIME=60000;  -- 60 segundos (usado no código Python)
-- SET GLOBAL MAX_EXECUTION_TIME=60000;   -- Para todas as sessões

-- Aumentar buffer de ordenação (se houver muitos ORDER BY)
-- SET GLOBAL sort_buffer_size = 4194304;  -- 4MB (padrão: 256KB)

-- Aumentar read_rnd_buffer_size para ORDER BY otimizados
-- SET GLOBAL read_rnd_buffer_size = 2097152;  -- 2MB

-- ============================================================================
-- MONITORAMENTO
-- ============================================================================
-- Query para monitorar uso dos novos índices:
SELECT 
    table_name,
    index_name,
    cardinality,
    ROUND(cardinality / (SELECT table_rows FROM information_schema.tables 
                         WHERE table_schema = DATABASE() 
                         AND table_name = 'leitoresRFID') * 100, 2) as selectivity_pct
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'leitoresRFID'
  AND index_name LIKE 'idx_ping%'
ORDER BY index_name;

-- Monitorar queries lentas:
-- SELECT * FROM mysql.slow_log WHERE sql_text LIKE '%PING_PERIODICO%' LIMIT 10;

-- ============================================================================
-- NOTAS IMPORTANTES
-- ============================================================================
-- 1. Criação de índices em tabelas grandes pode levar tempo
-- 2. Durante criação, a tabela pode ficar bloqueada (usar ONLINE/INPLACE se disponível)
-- 3. Índices ocupam espaço em disco - monitorar crescimento
-- 4. Testar performance antes/depois com EXPLAIN
-- 5. Executar em horário de baixo uso se possível
-- 6. TIMEOUT aumentado de 30s para 60s no código Python
-- 7. Índice com Horario DESC evita filesort que causava timeout

-- ============================================================================
-- RESUMO DAS OTIMIZAÇÕES APLICADAS
-- ============================================================================
-- 1. Índice idx_ping_optimized_v2:
--    - Cobre EtiquetaRFID_hex LIKE 'PING_PERIODICO_%'
--    - Horario DESC para evitar filesort (principal causa do timeout)
--    - Foto(1) para filtrar IS NOT NULL sem scan de BLOB
--    - CodigoLeitor e Antena para filtros adicionais
--
-- 2. Timeout de execução aumentado:
--    - De 30 segundos para 60 segundos
--    - Aplicado via SET SESSION MAX_EXECUTION_TIME=60000
--
-- 3. Interface melhorada:
--    - Erro 500 (timeout) não exibe botão "Tentar Novamente"
--    - Evita requisições repetidas que sobrecarregam o servidor

-- Versão alternativa com ALGORITHM=INPLACE para evitar bloqueio:
-- CREATE INDEX idx_ping_optimized_v2
-- ON leitoresRFID (EtiquetaRFID_hex(25), Horario DESC, Foto(1), CodigoLeitor, Antena)
-- ALGORITHM=INPLACE, LOCK=NONE;
