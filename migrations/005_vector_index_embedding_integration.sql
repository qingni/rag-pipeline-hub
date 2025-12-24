-- Migration: 005_vector_index_embedding_integration.sql
-- Description: 向量索引模块与向量化任务集成
-- Date: 2025-12-24
-- Feature: 004-vector-index

-- ============================================================================
-- 1. 扩展 vector_indexes 表，添加向量化任务关联字段
-- ============================================================================

-- 添加 embedding_result_id 字段（关联向量化任务）
ALTER TABLE vector_indexes 
ADD COLUMN IF NOT EXISTS embedding_result_id VARCHAR(36) REFERENCES embedding_results(result_id);

-- 添加 source_document_name 字段（冗余存储，便于展示）
ALTER TABLE vector_indexes 
ADD COLUMN IF NOT EXISTS source_document_name VARCHAR(255);

-- 添加 source_model 字段（冗余存储）
ALTER TABLE vector_indexes 
ADD COLUMN IF NOT EXISTS source_model VARCHAR(50);

-- 添加 error_message 字段（错误信息）
ALTER TABLE vector_indexes 
ADD COLUMN IF NOT EXISTS error_message TEXT;

-- 添加 namespace 字段
ALTER TABLE vector_indexes 
ADD COLUMN IF NOT EXISTS namespace VARCHAR(255) DEFAULT 'default';

-- 添加 index_params 字段（JSON格式的索引参数）
ALTER TABLE vector_indexes 
ADD COLUMN IF NOT EXISTS index_params JSONB DEFAULT '{}';

-- 添加 file_path 字段（FAISS索引文件路径）
ALTER TABLE vector_indexes 
ADD COLUMN IF NOT EXISTS file_path VARCHAR(512);

-- 添加 milvus_collection 字段（Milvus Collection名称）
ALTER TABLE vector_indexes 
ADD COLUMN IF NOT EXISTS milvus_collection VARCHAR(255);

-- ============================================================================
-- 2. 创建索引以优化查询性能
-- ============================================================================

-- 创建 embedding_result_id 索引
CREATE INDEX IF NOT EXISTS idx_vector_indexes_embedding_result 
ON vector_indexes(embedding_result_id);

-- 创建 namespace 索引
CREATE INDEX IF NOT EXISTS idx_vector_indexes_namespace 
ON vector_indexes(namespace);

-- 创建 status 索引（如果不存在）
CREATE INDEX IF NOT EXISTS idx_vector_indexes_status 
ON vector_indexes(status);

-- 创建 created_at 索引（如果不存在）
CREATE INDEX IF NOT EXISTS idx_vector_indexes_created_at 
ON vector_indexes(created_at DESC);

-- ============================================================================
-- 3. 更新 index_statistics 表
-- ============================================================================

-- 添加 index_size_bytes 字段
ALTER TABLE index_statistics 
ADD COLUMN IF NOT EXISTS index_size_bytes BIGINT DEFAULT 0;

-- 添加 avg_vector_norm 字段
ALTER TABLE index_statistics 
ADD COLUMN IF NOT EXISTS avg_vector_norm FLOAT;

-- 添加 query_count_24h 字段
ALTER TABLE index_statistics 
ADD COLUMN IF NOT EXISTS query_count_24h INTEGER DEFAULT 0;

-- 添加 last_build_duration_s 字段
ALTER TABLE index_statistics 
ADD COLUMN IF NOT EXISTS last_build_duration_s FLOAT;

-- 添加 last_persist_at 字段
ALTER TABLE index_statistics 
ADD COLUMN IF NOT EXISTS last_persist_at TIMESTAMP WITH TIME ZONE;

-- 添加 error_count_24h 字段
ALTER TABLE index_statistics 
ADD COLUMN IF NOT EXISTS error_count_24h INTEGER DEFAULT 0;

-- ============================================================================
-- 4. 创建索引操作日志表
-- ============================================================================

CREATE TABLE IF NOT EXISTS index_operation_logs (
    id SERIAL PRIMARY KEY,
    index_id INTEGER REFERENCES vector_indexes(id) ON DELETE CASCADE,
    operation_type VARCHAR(50) NOT NULL,  -- CREATE, UPDATE, DELETE, SEARCH, PERSIST, RECOVER
    user_id VARCHAR(255),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms FLOAT,
    status VARCHAR(20) NOT NULL DEFAULT 'STARTED',  -- STARTED, SUCCESS, FAILED
    details JSONB DEFAULT '{}',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_operation_logs_index_id 
ON index_operation_logs(index_id);

CREATE INDEX IF NOT EXISTS idx_operation_logs_operation_type 
ON index_operation_logs(operation_type);

CREATE INDEX IF NOT EXISTS idx_operation_logs_created_at 
ON index_operation_logs(created_at DESC);

-- ============================================================================
-- 5. 添加约束检查
-- ============================================================================

-- 确保 provider/index_type 字段使用正确的枚举值
-- 注意：如果已有数据，需要先更新数据再添加约束

-- 检查 dimension 是否在有效范围内
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'check_vector_indexes_dimension'
    ) THEN
        ALTER TABLE vector_indexes 
        ADD CONSTRAINT check_vector_indexes_dimension 
        CHECK (dimension IN (128, 256, 512, 768, 1024, 1536, 2048, 3072, 4096));
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Constraint check_vector_indexes_dimension already exists or cannot be added';
END $$;

-- ============================================================================
-- 6. 注释说明
-- ============================================================================

COMMENT ON COLUMN vector_indexes.embedding_result_id IS '关联的向量化任务ID';
COMMENT ON COLUMN vector_indexes.source_document_name IS '源文档名称（冗余存储，便于展示）';
COMMENT ON COLUMN vector_indexes.source_model IS '源向量化模型（冗余存储）';
COMMENT ON COLUMN vector_indexes.error_message IS '索引构建错误信息';
COMMENT ON COLUMN vector_indexes.namespace IS '命名空间（用于多租户）';
COMMENT ON COLUMN vector_indexes.index_params IS '索引算法参数（JSON格式）';
COMMENT ON COLUMN vector_indexes.file_path IS 'FAISS索引文件路径';
COMMENT ON COLUMN vector_indexes.milvus_collection IS 'Milvus Collection名称';

COMMENT ON TABLE index_operation_logs IS '索引操作日志表，记录所有索引相关操作';
