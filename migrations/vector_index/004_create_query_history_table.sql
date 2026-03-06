-- ==============================================================================
-- Migration: 004 - Create query_history table
-- ==============================================================================
-- Description: Create query_history table for audit and analytics
-- Author: RAG Pipeline Hub Team
-- Date: 2025-12-23
-- ==============================================================================

-- Drop table if exists (for development only)
-- DROP TABLE IF EXISTS query_history CASCADE;

-- Create query_history table
CREATE TABLE IF NOT EXISTS query_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    index_id UUID NOT NULL REFERENCES vector_indexes(id) ON DELETE CASCADE,
    query_text TEXT,
    top_k INTEGER NOT NULL CHECK (top_k > 0),
    threshold FLOAT CHECK (threshold >= 0 AND threshold <= 1),
    result_count INTEGER DEFAULT 0,
    latency_ms FLOAT NOT NULL CHECK (latency_ms >= 0),
    filter_expr JSONB,
    user_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_query_history_index_id ON query_history(index_id);
CREATE INDEX IF NOT EXISTS idx_query_history_created_at ON query_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_history_user_id ON query_history(user_id);
CREATE INDEX IF NOT EXISTS idx_query_history_latency ON query_history(latency_ms);

-- Create GIN index for JSONB filter expressions
CREATE INDEX IF NOT EXISTS idx_query_history_filter_expr ON query_history USING GIN (filter_expr);

-- Add comments for documentation
COMMENT ON TABLE query_history IS 'Query operation history for audit and performance analysis';
COMMENT ON COLUMN query_history.id IS 'Unique identifier for the query record';
COMMENT ON COLUMN query_history.index_id IS 'Index ID where the query was executed';
COMMENT ON COLUMN query_history.query_text IS 'Query text (if available)';
COMMENT ON COLUMN query_history.top_k IS 'Number of results requested';
COMMENT ON COLUMN query_history.threshold IS 'Similarity threshold filter (0-1)';
COMMENT ON COLUMN query_history.result_count IS 'Actual number of results returned';
COMMENT ON COLUMN query_history.latency_ms IS 'Query latency in milliseconds';
COMMENT ON COLUMN query_history.filter_expr IS 'Milvus filter expression (JSONB)';
COMMENT ON COLUMN query_history.user_id IS 'User ID who executed the query';
COMMENT ON COLUMN query_history.created_at IS 'Query execution timestamp';

-- Create partition for query_history by month (optional, for high-volume scenarios)
-- This can be uncommented in production environments
-- CREATE TABLE query_history_2025_12 PARTITION OF query_history
--     FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- ==============================================================================
-- Migration Complete
-- ==============================================================================
