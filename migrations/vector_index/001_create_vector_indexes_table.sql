-- ==============================================================================
-- Migration: 001 - Create vector_indexes table
-- ==============================================================================
-- Description: Create the main vector_indexes table for storing index configuration
-- Author: RAG Pipeline Hub Team
-- Date: 2025-12-23
-- ==============================================================================

-- Drop table if exists (for development only)
-- DROP TABLE IF EXISTS vector_indexes CASCADE;

-- Create vector_indexes table
CREATE TABLE IF NOT EXISTS vector_indexes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    provider VARCHAR(20) NOT NULL CHECK (provider IN ('milvus', 'faiss')),
    dimension INTEGER NOT NULL CHECK (dimension IN (128, 256, 512, 768, 1536, 3072)),
    index_type VARCHAR(50) NOT NULL,
    metric_type VARCHAR(20) NOT NULL CHECK (metric_type IN ('cosine', 'euclidean', 'dot_product')),
    index_params JSONB DEFAULT '{}',
    namespace VARCHAR(255) DEFAULT 'default',
    vector_count INTEGER DEFAULT 0 CHECK (vector_count >= 0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('building', 'ready', 'updating', 'error')),
    file_path VARCHAR(512),  -- FAISS only
    milvus_collection VARCHAR(255),  -- Milvus only
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_vector_indexes_name ON vector_indexes(name);
CREATE INDEX IF NOT EXISTS idx_vector_indexes_provider ON vector_indexes(provider);
CREATE INDEX IF NOT EXISTS idx_vector_indexes_namespace ON vector_indexes(namespace);
CREATE INDEX IF NOT EXISTS idx_vector_indexes_status ON vector_indexes(status);
CREATE INDEX IF NOT EXISTS idx_vector_indexes_created_at ON vector_indexes(created_at DESC);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for auto-updating updated_at
DROP TRIGGER IF EXISTS update_vector_indexes_updated_at ON vector_indexes;
CREATE TRIGGER update_vector_indexes_updated_at
    BEFORE UPDATE ON vector_indexes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE vector_indexes IS 'Stores configuration and metadata for vector indexes (Milvus and FAISS)';
COMMENT ON COLUMN vector_indexes.id IS 'Unique identifier for the index';
COMMENT ON COLUMN vector_indexes.name IS 'Human-readable index name (must be unique)';
COMMENT ON COLUMN vector_indexes.provider IS 'Vector database provider: milvus or faiss';
COMMENT ON COLUMN vector_indexes.dimension IS 'Vector dimensionality (128, 256, 512, 768, 1536, or 3072)';
COMMENT ON COLUMN vector_indexes.index_type IS 'Index algorithm type (provider-specific)';
COMMENT ON COLUMN vector_indexes.metric_type IS 'Similarity metric: cosine, euclidean, or dot_product';
COMMENT ON COLUMN vector_indexes.index_params IS 'Provider-specific index parameters (JSONB)';
COMMENT ON COLUMN vector_indexes.namespace IS 'Namespace for multi-tenant isolation';
COMMENT ON COLUMN vector_indexes.vector_count IS 'Current number of vectors in the index';
COMMENT ON COLUMN vector_indexes.status IS 'Index status: building, ready, updating, or error';
COMMENT ON COLUMN vector_indexes.file_path IS 'File path for FAISS index storage';
COMMENT ON COLUMN vector_indexes.milvus_collection IS 'Milvus collection name';
COMMENT ON COLUMN vector_indexes.created_at IS 'Index creation timestamp';
COMMENT ON COLUMN vector_indexes.updated_at IS 'Last update timestamp (auto-updated)';
COMMENT ON COLUMN vector_indexes.created_by IS 'User ID who created the index';

-- Insert sample data for development
-- Uncomment for development environment
-- INSERT INTO vector_indexes (name, provider, dimension, index_type, metric_type, namespace, status)
-- VALUES ('dev_test_index', 'faiss', 1536, 'IndexFlatIP', 'cosine', 'default', 'ready');

-- ==============================================================================
-- Migration Complete
-- ==============================================================================
