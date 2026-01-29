-- Migration: 002-chunking-opt-merge-multimodal
-- Description: 删除 multimodal 策略，完全使用 hybrid 策略
-- Date: 2026-01-29
-- Note: multimodal 策略功能已完全合并到 hybrid 策略中

-- ============================================
-- 1. 删除 multimodal 策略记录
-- ============================================
DELETE FROM chunking_strategies WHERE strategy_type = 'MULTIMODAL';

-- ============================================
-- 2. 更新 hybrid 策略的描述和默认参数
-- ============================================
UPDATE chunking_strategies 
SET description = '智能混合分块策略，针对不同内容类型（文本、代码、表格、图片）应用不同分块策略，支持多模态内容处理',
    default_params = '{"text_strategy": "semantic", "code_strategy": "lines", "table_strategy": "independent", "include_tables": true, "include_images": true, "include_code": true, "text_chunk_size": 600, "text_overlap": 100, "code_chunk_lines": 50, "code_overlap_lines": 8, "min_table_rows": 2, "min_code_lines": 3}'
WHERE strategy_type = 'HYBRID';
