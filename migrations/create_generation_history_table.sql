-- Migration: Create generation_history table
-- Feature: 006-text-generation
-- Date: 2025-12-26

-- 创建生成历史表
CREATE TABLE IF NOT EXISTS generation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id VARCHAR(36) NOT NULL UNIQUE,
    question TEXT NOT NULL,
    model VARCHAR(50) NOT NULL,
    temperature REAL DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 4096,
    context_summary TEXT,
    context_sources JSON,
    answer TEXT,
    token_usage JSON,
    processing_time_ms REAL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_generation_history_request_id ON generation_history(request_id);
CREATE INDEX IF NOT EXISTS idx_generation_history_created_at ON generation_history(created_at);
CREATE INDEX IF NOT EXISTS idx_generation_history_status ON generation_history(status);
CREATE INDEX IF NOT EXISTS idx_generation_history_is_deleted ON generation_history(is_deleted);

-- 创建触发器：自动更新 updated_at
CREATE TRIGGER IF NOT EXISTS update_generation_history_updated_at
    AFTER UPDATE ON generation_history
    FOR EACH ROW
BEGIN
    UPDATE generation_history SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;
