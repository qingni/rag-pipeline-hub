-- ==============================================================================
-- Migration: 003 - Create vector_metadata table
-- ==============================================================================
-- Description: Create vector_metadata table for extended metadata storage
-- Author: RAG Pipeline Hub Team
-- Date: 2025-12-23
-- ==============================================================================

-- Drop table if exists (for development only)
-- DROP TABLE IF EXISTS vector_metadata CASCADE;

-- Create vector_metadata table
CREATE TABLE IF NOT EXISTS vector_metadata (
    vector_id VARCHAR(255) PRIMARY KEY,
    index_id UUID NOT NULL REFERENCES vector_indexes(id) ON DELETE CASCADE,
    large_metadata JSONB,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_vector_metadata_index_id ON vector_metadata(index_id);
CREATE INDEX IF NOT EXISTS idx_vector_metadata_last_accessed ON vector_metadata(last_accessed DESC);
CREATE INDEX IF NOT EXISTS idx_vector_metadata_access_count ON vector_metadata(access_count DESC);

-- Create GIN index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_vector_metadata_large_metadata ON vector_metadata USING GIN (large_metadata);

-- Add comments for documentation
COMMENT ON TABLE vector_metadata IS 'Extended metadata storage for vectors (supplements Milvus/FAISS storage)';
COMMENT ON COLUMN vector_metadata.vector_id IS 'Vector ID (foreign key to Milvus/FAISS storage)';
COMMENT ON COLUMN vector_metadata.index_id IS 'Index ID this vector belongs to';
COMMENT ON COLUMN vector_metadata.large_metadata IS 'Large metadata (>1KB) stored as JSONB';
COMMENT ON COLUMN vector_metadata.access_count IS 'Number of times this vector was accessed';
COMMENT ON COLUMN vector_metadata.last_accessed IS 'Timestamp of last access';
COMMENT ON COLUMN vector_metadata.created_at IS 'Record creation timestamp';

-- ==============================================================================
-- Migration Complete
-- ==============================================================================
