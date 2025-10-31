-- Script de otimização para queries de PING RFID
-- Autor: Sistema de otimização automática
-- Data: 2025-10-31
-- Objetivo: Acelerar queries da página de PING que estavam travando o Waitress

-- ============================================================================
-- ANÁLISE DO PROBLEMA
-- ============================================================================
-- 1. Queries estavam usando LENGTH(Foto) em WHERE - scan completo de BLOBs
-- 2. Sem índices adequados para filtros PING_PERIODICO_*
-- 3. ORDER BY Horario DESC sem índice otimizado
-- 4. Task queue depth aumentando (Waitress bloqueado)

-- ============================================================================
-- VERIFICAÇÃO ATUAL DE ÍNDICES
-- ============================================================================
-- Execute primeiro para ver índices existentes:
-- SHOW INDEX FROM leitoresRFID;

-- ============================================================================
-- ÍNDICE PRINCIPAL PARA QUERIES DE PING
-- ============================================================================
-- Este índice cobre:
-- - Filtro: EtiquetaRFID_hex LIKE 'PING_PERIODICO_%'
-- - Filtro: Foto IS NOT NULL (coluna incluída)
-- - Ordem: Horario DESC
-- - Filtros adicionais: CodigoLeitor, Antena

-- Verificar se o índice já existe
SELECT 
    COUNT(*) as index_exists,
    'idx_ping_optimized' as index_name
FROM information_schema.statistics 
WHERE table_schema = DATABASE()
  AND table_name = 'leitoresRFID'
  AND index_name = 'idx_ping_optimized';

-- Criar índice otimizado (executar apenas se não existir)
CREATE INDEX idx_ping_optimized 
ON leitoresRFID (EtiquetaRFID_hex(20), Horario DESC, CodigoLeitor, Antena)
WHERE Foto IS NOT NULL;

-- Nota: Se o MySQL não suportar índices parciais (WHERE), usar:
-- CREATE INDEX idx_ping_optimized 
-- ON leitoresRFID (EtiquetaRFID_hex(20), Horario DESC, CodigoLeitor, Antena);

-- ============================================================================
-- ÍNDICE ADICIONAL PARA ESTATÍSTICAS
-- ============================================================================
-- Para acelerar queries de agregação (COUNT, MIN, MAX)
CREATE INDEX idx_ping_stats 
ON leitoresRFID (EtiquetaRFID_hex(20), Horario);

-- ============================================================================
-- ÍNDICE PARA FILTROS POR ANTENA
-- ============================================================================
-- Acelera filtros específicos por leitor e antena
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
    AVG(LENGTH(Foto)) as tamanho_medio_foto_bytes
FROM leitoresRFID
WHERE EtiquetaRFID_hex LIKE 'PING_PERIODICO_%'
  AND Foto IS NOT NULL;

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
-- DROP INDEX idx_ping_optimized ON leitoresRFID;
-- DROP INDEX idx_ping_stats ON leitoresRFID;
-- DROP INDEX idx_ping_antenna ON leitoresRFID;

-- ============================================================================
-- CONFIGURAÇÕES ADICIONAIS DO MYSQL (opcional)
-- ============================================================================
-- Para melhorar performance geral de queries PING:

-- Aumentar buffer de ordenação (se houver muitos ORDER BY)
-- SET GLOBAL sort_buffer_size = 2097152;  -- 2MB

-- Aumentar cache de queries (MySQL < 8.0)
-- SET GLOBAL query_cache_size = 67108864;  -- 64MB
-- SET GLOBAL query_cache_type = 1;

-- Aumentar pool de threads para Waitress/conexões simultâneas
-- SET GLOBAL thread_pool_size = 8;

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
-- 2. Durante criação, a tabela pode ficar bloqueada (usar ONLINE se disponível)
-- 3. Índices ocupam espaço em disco - monitorar crescimento
-- 4. Testar performance antes/depois com EXPLAIN
-- 5. Executar em horário de baixo uso se possível

-- Versão alternativa com ALGORITHM=INPLACE para evitar bloqueio:
-- CREATE INDEX idx_ping_optimized 
-- ON leitoresRFID (EtiquetaRFID_hex(20), Horario DESC, CodigoLeitor, Antena)
-- ALGORITHM=INPLACE, LOCK=NONE;
