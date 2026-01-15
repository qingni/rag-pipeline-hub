-- Migration: Create loading_tasks table for async document processing
-- Version: 007
-- Description: Adds support for async document loading via Docling Serve

-- Create loading_tasks table
CREATE TABLE IF NOT EXISTS loading_tasks (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL,
    external_task_id VARCHAR(100),
    loader_type VARCHAR(50) NOT NULL DEFAULT 'docling_serve',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result_path VARCHAR(500),
    error_message TEXT,
    processing_time REAL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_loading_tasks_document_id ON loading_tasks(document_id);
CREATE INDEX IF NOT EXISTS idx_loading_tasks_status ON loading_tasks(status);
CREATE INDEX IF NOT EXISTS idx_loading_tasks_created_at ON loading_tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_loading_tasks_external_task_id ON loading_tasks(external_task_id);

-- Add comments (PostgreSQL syntax, SQLite will ignore)
-- COMMENT ON TABLE loading_tasks IS 'Tracks async document loading tasks for Docling Serve';
-- COMMENT ON COLUMN loading_tasks.external_task_id IS 'Task ID returned by Docling Serve';
-- COMMENT ON COLUMN loading_tasks.status IS 'Task status: pending, started, success, failure, cancelled';
-- COMMENT ON COLUMN loading_tasks.progress IS 'Processing progress 0-100';
