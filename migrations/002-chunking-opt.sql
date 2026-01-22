-- Migration: 002-chunking-opt
-- Description: 文档分块功能优化 - 添加父子分块、多模态分块、混合策略支持
-- Date: 2026-01-20

-- ============================================
-- 1. 扩展 chunks 表：添加 chunk_type 和 parent_id 字段
-- ============================================
ALTER TABLE chunks 
ADD COLUMN chunk_type VARCHAR(20) DEFAULT 'text' NOT NULL;

ALTER TABLE chunks
ADD COLUMN parent_id VARCHAR(36) NULL;

-- 创建索引
CREATE INDEX idx_chunk_parent ON chunks(parent_id);
CREATE INDEX idx_chunk_type ON chunks(chunk_type);

-- ============================================
-- 2. 创建 parent_chunks 表：存储父块信息
-- ============================================
CREATE TABLE IF NOT EXISTS parent_chunks (
    id VARCHAR(36) PRIMARY KEY,
    result_id VARCHAR(36) NOT NULL,
    sequence_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    start_position INTEGER,
    end_position INTEGER,
    child_count INTEGER DEFAULT 0,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (result_id) REFERENCES chunking_results(result_id) ON DELETE CASCADE
);

CREATE INDEX idx_parent_chunk_result ON parent_chunks(result_id);
CREATE INDEX idx_parent_chunk_sequence ON parent_chunks(result_id, sequence_number);

-- ============================================
-- 3. 创建 hybrid_chunking_configs 表：存储混合分块策略配置
-- ============================================
CREATE TABLE IF NOT EXISTS hybrid_chunking_configs (
    id VARCHAR(36) PRIMARY KEY,
    result_id VARCHAR(36) NOT NULL,
    content_type VARCHAR(20) NOT NULL,
    strategy_type VARCHAR(20) NOT NULL,
    strategy_params JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (result_id) REFERENCES chunking_results(result_id) ON DELETE CASCADE,
    UNIQUE(result_id, content_type)
);

CREATE INDEX idx_hybrid_config_result ON hybrid_chunking_configs(result_id);

-- ============================================
-- 4. 添加新的分块策略到 chunking_strategies 表
-- ============================================
INSERT OR IGNORE INTO chunking_strategies (strategy_id, strategy_name, strategy_type, description, default_params, is_enabled, requires_structure) VALUES
('ps-parent-child', '父子文档分块', 'parent_child', '生成父块和子块的两层结构，子块用于检索，父块提供上下文', '{"parent_chunk_size": 2000, "child_chunk_size": 500, "child_overlap": 50, "parent_overlap": 200}', 1, 0),
('ps-hybrid', '混合分块策略', 'hybrid', '针对不同内容类型（正文、代码、表格）应用不同分块策略', '{}', 1, 0),
('ps-multimodal', '多模态分块', 'multimodal', '将表格、图片等非文本内容独立分块', '{"include_tables": true, "include_images": true, "text_strategy": "semantic"}', 1, 0);

-- ============================================
-- 5. 添加外键约束（chunks.parent_id -> parent_chunks.id）
-- ============================================
-- Note: SQLite 不支持 ALTER TABLE ADD CONSTRAINT，外键在创建表时已定义
-- 对于 PostgreSQL，取消下面的注释：
-- ALTER TABLE chunks ADD CONSTRAINT fk_chunk_parent FOREIGN KEY (parent_id) REFERENCES parent_chunks(id) ON DELETE SET NULL;
