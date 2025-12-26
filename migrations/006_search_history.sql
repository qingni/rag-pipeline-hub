-- 搜索查询功能数据库迁移脚本
-- 创建搜索历史和搜索配置表

-- 搜索历史表
CREATE TABLE IF NOT EXISTS search_history (
    id VARCHAR(36) PRIMARY KEY,
    query_text TEXT NOT NULL,
    index_ids JSON NOT NULL,
    config JSON NOT NULL,
    result_count INTEGER NOT NULL DEFAULT 0,
    execution_time_ms INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 搜索历史索引
CREATE INDEX IF NOT EXISTS idx_search_history_created 
ON search_history(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_search_history_query 
ON search_history(query_text);

-- 搜索配置表
CREATE TABLE IF NOT EXISTS search_config (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    default_index_id VARCHAR(36),
    default_top_k INTEGER NOT NULL DEFAULT 10,
    default_threshold REAL NOT NULL DEFAULT 0.5,
    default_metric VARCHAR(50) NOT NULL DEFAULT 'cosine',
    is_default BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 插入默认配置
INSERT OR IGNORE INTO search_config (
    id, 
    name, 
    default_top_k, 
    default_threshold, 
    default_metric, 
    is_default
) VALUES (
    'default-config',
    '默认配置',
    10,
    0.5,
    'cosine',
    1
);
