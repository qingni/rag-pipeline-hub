-- Migration: 002-chunking-opt-update
-- Description: 更新分块策略默认参数，优化混合分块和语义分块配置
-- Date: 2026-01-21

-- ============================================
-- 1. 更新 hybrid 策略的默认参数
-- ============================================
UPDATE chunking_strategies
SET default_params = '{"text_strategy": "semantic", "code_strategy": "lines", "table_strategy": "independent", "text_chunk_size": 500, "text_overlap": 50, "code_chunk_lines": 50, "code_overlap_lines": 5, "similarity_threshold": 0.5, "use_embedding": true}'
WHERE strategy_id = 'ps-hybrid';

-- ============================================
-- 2. 更新 multimodal 策略的默认参数（添加 base64 支持）
-- ============================================
UPDATE chunking_strategies
SET default_params = '{"include_tables": true, "include_images": true, "include_code": true, "text_strategy": "character", "text_chunk_size": 500, "text_overlap": 50, "min_table_rows": 2, "min_code_lines": 3, "extract_image_base64": false}'
WHERE strategy_id = 'ps-multimodal';

-- ============================================
-- 3. 更新 semantic 策略的默认参数（添加 embedding 支持）
-- ============================================
UPDATE chunking_strategies
SET default_params = '{"min_chunk_size": 300, "max_chunk_size": 1200, "similarity_threshold": 0.3, "use_embedding": true, "embedding_model": "text-embedding-ada-002", "breakpoint_threshold_type": "percentile", "breakpoint_threshold_amount": 95}'
WHERE strategy_type = 'semantic';

-- ============================================
-- 4. 更新策略描述以更清晰说明功能
-- ============================================
UPDATE chunking_strategies
SET description = '基于 Embedding 相似度的语义分块（支持 LangChain SemanticChunker），TF-IDF 作为降级策略'
WHERE strategy_type = 'semantic';

UPDATE chunking_strategies
SET description = '针对不同内容类型（正文、代码块、表格）应用最适合的分块方法，正文支持语义分块'
WHERE strategy_id = 'ps-hybrid';

UPDATE chunking_strategies
SET description = '将表格、图片、代码块等非文本内容独立分块，支持图片 base64 提取用于多模态向量化'
WHERE strategy_id = 'ps-multimodal';
