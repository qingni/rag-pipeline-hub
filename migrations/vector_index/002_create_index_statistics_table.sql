-- ==============================================================================
-- Migration: 002 - Create index_statistics table
-- ==============================================================================
-- Description: Create the index_statistics table for storing performance metrics
-- Author: RAG Framework Team
-- Date: 2025-12-23
-- ==============================================================================

-- Drop table if exists (for development only)
-- DROP TABLE IF EXISTS index_statistics CASCADE;

-- Create index_statistics table
CREATE TABLE IF NOT EXISTS index_statistics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    index_id UUID NOT NULL REFERENCES vector_indexes(id) ON DELETE CASCADE,
    vector_count INTEGER DEFAULT 0 CHECK (vector_count >= 0),
    index_size_bytes BIGINT DEFAULT 0 CHECK (index_size_bytes >= 0),
    avg_vector_norm FLOAT,
    query_count_24h INTEGER DEFAULT 0 CHECK (query_count_24h >= 0),
    avg_query_latency_ms FLOAT DEFAULT 0 CHECK (avg_query_latency_ms >= 0),
    last_build_duration_s FLOAT,
    last_persist_at TIMESTAMP WITH TIME ZONE,
    error_count_24h INTEGER DEFAULT 0 CHECK (error_count_24h >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(index_id)  -- One stats record per index
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_index_statistics_index_id ON index_statistics(index_id);
CREATE INDEX IF NOT EXISTS idx_index_statistics_updated_at ON index_statistics(updated_at DESC);

-- Create trigger for auto-updating updated_at
DROP TRIGGER IF EXISTS update_index_statistics_updated_at ON index_statistics;
CREATE TRIGGER update_index_statistics_updated_at
    BEFORE UPDATE ON index_statistics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE index_statistics IS 'Stores runtime statistics and performance metrics for vector indexes';
COMMENT ON COLUMN index_statistics.id IS 'Unique identifier for the statistics record';
COMMENT ON COLUMN index_statistics.index_id IS 'Foreign key to vector_indexes table';
COMMENT ON COLUMN index_statistics.vector_count IS 'Total number of vectors in the index';
COMMENT ON COLUMN index_statistics.index_size_bytes IS 'Index size in bytes (on disk)';
COMMENT ON COLUMN index_statistics.avg_vector_norm IS 'Average L2 norm of vectors';
COMMENT ON COLUMN index_statistics.query_count_24h IS 'Number of queries in last 24 hours (rolling window)';
COMMENT ON COLUMN index_statistics.avg_query_latency_ms IS 'Average query latency in milliseconds (P95)';
COMMENT ON COLUMN index_statistics.last_build_duration_s IS 'Duration of last index build in seconds';
COMMENT ON COLUMN index_statistics.last_persist_at IS 'Timestamp of last persistence operation';
COMMENT ON COLUMN index_statistics.error_count_24h IS 'Number of errors in last 24 hours';
COMMENT ON COLUMN index_statistics.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN index_statistics.updated_at IS 'Last update timestamp (auto-updated)';

-- ==============================================================================
-- Migration Complete
-- ==============================================================================
