# Quickstart: 检索查询模块优化版

**Feature**: 005-search-query-opt | **Date**: 2026-02-26

## 前提条件

1. **已完成的模块**:
   - 004-vector-index-opt: Milvus Collection 已创建，含稠密+稀疏向量字段，BM25 统计已持久化
   - 003-vector-embedding: Embedding 服务已配置（OpenAI/Bedrock/HuggingFace）
   - 005-search-query: 基础搜索功能已实现

2. **环境依赖**:
   - Python 3.11+
   - Milvus 2.x 运行中
   - FlagEmbedding >= 1.2.0 已安装（用于 Reranker）
   - jieba 已安装（用于 BM25 分词）

3. **环境变量配置**:
   ```bash
   # .env 文件中确认以下配置
   MILVUS_HOST=localhost
   MILVUS_PORT=19530
   EMBEDDING_API_KEY=your_key
   EMBEDDING_API_BASE_URL=your_url
   EMBEDDING_DEFAULT_MODEL=your_model
   
   # 新增配置（可选，有默认值）
   RRF_K=60                    # RRF 融合参数
   RERANKER_TOP_N=20           # Reranker 候选集大小
   MAX_COLLECTIONS=5           # 联合搜索最大 Collection 数
   DEFAULT_SEARCH_MODE=auto    # 默认检索模式
   RERANKER_MODEL=qwen3-reranker-4b  # Reranker 模型
   ```

## 快速验证

### Step 1: 启动后端服务

```bash
cd backend
source .venv/bin/activate
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 2: 验证 Reranker 健康检查

```bash
# 检查 Reranker 服务状态
curl http://localhost:8000/api/v1/search/reranker/health

# 预期响应
{
  "success": true,
  "data": {
    "available": true,
    "model_name": "qwen3-reranker-4b",
    "use_fp16": true,
    "flag_embedding_installed": true,
    "model_loaded": true
  }
}
```

### Step 3: 获取可用 Collection 列表

```bash
curl http://localhost:8000/api/v1/search/collections

# 预期响应
{
  "success": true,
  "data": [
    {
      "id": "1",
      "name": "tech_docs",
      "has_sparse": true,
      "vector_count": 1000,
      "dimension": 1024
    }
  ]
}
```

### Step 4: 执行混合检索

```bash
curl -X POST http://localhost:8000/api/v1/search/hybrid \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "如何使用 Python 连接数据库",
    "collection_ids": ["1"],
    "top_k": 5,
    "search_mode": "auto",
    "reranker_top_n": 20
  }'

# 预期响应
{
  "success": true,
  "data": {
    "query_id": "uuid-xxx",
    "query_text": "如何使用 Python 连接数据库",
    "search_mode": "hybrid",
    "reranker_available": true,
    "results": [
      {
        "id": "uuid-xxx",
        "chunk_id": "123",
        "text_summary": "Python 连接数据库的常见方法...",
        "rrf_score": 0.033,
        "reranker_score": 0.892,
        "search_mode": "hybrid",
        "source_collection": "tech_docs",
        "source_document": "python-guide.pdf",
        "rank": 1
      }
    ],
    "total_count": 5,
    "execution_time_ms": 180,
    "timing": {
      "embedding_ms": 50,
      "bm25_ms": 5,
      "search_ms": 45,
      "reranker_ms": 80,
      "total_ms": 180
    }
  }
}
```

### Step 5: 多 Collection 联合搜索

```bash
curl -X POST http://localhost:8000/api/v1/search/hybrid \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "向量数据库的性能优化",
    "collection_ids": ["1", "2"],
    "top_k": 10,
    "search_mode": "auto"
  }'

# 预期响应中每条结果标注 source_collection
```

### Step 6: 验证降级场景

```bash
# 纯稠密检索（强制模式）
curl -X POST http://localhost:8000/api/v1/search/hybrid \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "什么是向量数据库",
    "search_mode": "dense_only",
    "top_k": 5
  }'

# 预期: search_mode = "dense_only"
```

### Step 7: 前端验证

```bash
cd frontend
npm run dev
```

1. 打开 http://localhost:5173
2. 进入「搜索查询」页面
3. 在搜索配置面板中：
   - 选择目标 Collection（应显示 `has_sparse` 标识）
   - 检索模式默认为「自动」
   - 混合检索模式下显示 Reranker 参数配置
4. 输入查询文本，执行搜索
5. 验证结果卡片显示 search_mode 标签、rrf_score、reranker_score

## 常见问题

### Q: Reranker 模型首次加载很慢？
A: qwen3-reranker-4b 通过远程 API 调用，无需本地加载模型。如果首次调用较慢，请检查 API 服务是否正常运行。

### Q: 混合检索自动降级为纯稠密？
A: 检查以下条件：
1. Collection 是否创建时包含了稀疏向量字段 (`sparse_embedding`)
2. BM25 统计文件是否存在 (`results/bm25_stats/{index_id}_bm25_stats.json`)
3. 日志中是否有 BM25 相关警告

### Q: 多 Collection 搜索超过 5 个？
A: 系统限制最大 5 个 Collection 联合搜索。如需检索更多 Collection，建议分批查询或重新组织知识库结构。
