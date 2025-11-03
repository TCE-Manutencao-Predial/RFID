-- Script para adicionar colunas NumeroSerie e NumeroPatrimonio na tabela etiquetasRFID
-- Data: 2025-11-03
-- Descrição: Adiciona campos opcionais para número de série e número de patrimônio nas etiquetas RFID

USE ControleDeMateriais;

-- Adicionar coluna NumeroSerie (opcional)
ALTER TABLE etiquetasRFID 
ADD COLUMN NumeroSerie VARCHAR(100) NULL COMMENT 'Número de série do equipamento/material',
ADD UNIQUE KEY idx_numero_serie (NumeroSerie);

-- Adicionar coluna NumeroPatrimonio (opcional)
ALTER TABLE etiquetasRFID 
ADD COLUMN NumeroPatrimonio VARCHAR(100) NULL COMMENT 'Número de patrimônio do equipamento/material',
ADD UNIQUE KEY idx_numero_patrimonio (NumeroPatrimonio);

-- Verificar estrutura da tabela
DESCRIBE etiquetasRFID;
