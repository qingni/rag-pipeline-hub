# Quickstart: 文档向量化功能优化

**Branch**: `003-vector-embedding-opt` | **Date**: 2026-02-02

## 快速开始

### 1. 启动服务

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

### 2. 基础向量化（使用默认配置）

```bash
# 对文档分块结果进行向量化
curl -X POST http://localhost:8000/api/embedding/from-document \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc-123",
    "model": "bge-m3"
  }'

# 响应示例
{
  "task_id": "task-uuid",
  "result_id": "result-uuid",
  "status": "completed",
  "statistics": {
    "total_chunks": 100,
    "successful_count": 100,
    "cached_count": 0,
    "processing_time_ms": 5000.5
  }
}
```

### 3. 高级配置向量化

```bash
# 使用自定义配置进行向量化
curl -X POST http://localhost:8000/api/embedding/from-document \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc-123",
    "model": "qwen3-embedding-8b",
    "config": {
      "batch_size": 100,
      "concurrency": 10,
      "enable_cache": true,
      "incremental": true
    }
  }'
```

### 4. 多模态内容向量化

```bash
# 对包含图片和表格的文档进行向量化
curl -X POST http://localhost:8000/api/embedding/from-document \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc-with-images-123",
    "model": "bge-m3",
    "config": {
      "multimodal_model": "qwen3-vl-embedding-8b"
    }
  }'

# 响应中包含多模态处理统计
{
  "statistics": {
    "text_chunks": 80,
    "table_chunks": 10,
    "image_chunks": 10,
    "multimodal_stats": {
      "image_success": 8,
      "image_fallback": 2,
      "image_failed": 0
    }
  }
}
```

### 5. 增量向量化

```bash
# 文档更新后仅对变更分块进行向量化
curl -X POST http://localhost:8000/api/embedding/from-document \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc-123",
    "model": "bge-m3",
    "config": {
      "incremental": true
    }
  }'

# 响应示例（部分分块来自缓存）
{
  "statistics": {
    "total_chunks": 100,
    "successful_count": 100,
    "cached_count": 85,
    "computed_count": 15,
    "cache_hit_rate": 0.85
  }
}
```

### 6. 强制全量向量化

```bash
# 忽略缓存，重新计算所有向量
curl -X POST http://localhost:8000/api/embedding/from-document \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc-123",
    "model": "bge-m3",
    "config": {
      "force_recompute": true
    }
  }'
```

### 7. 实时进度查询

```bash
# 使用 SSE 订阅向量化进度
curl -N http://localhost:8000/api/embedding/progress/task-uuid

# SSE 事件示例
event: progress
data: {"total_chunks": 100, "completed": 50, "failed": 0, "cached": 20, "speed": 25.5, "eta_seconds": 2.0}

event: progress
data: {"total_chunks": 100, "completed": 100, "failed": 0, "cached": 20, "speed": 25.5, "eta_seconds": 0}

event: completed
data: {"result_id": "result-uuid", "status": "completed"}
```

### 8. 任务状态查询

```bash
# 查询任务当前状态
curl http://localhost:8000/api/embedding/task/task-uuid

# 响应示例
{
  "task_id": "task-uuid",
  "status": "running",
  "progress": {
    "total_chunks": 100,
    "completed": 50,
    "failed": 0,
    "cached": 20,
    "current_batch": 3,
    "speed": 25.5,
    "eta_seconds": 2.0
  }
}
```

### 9. 取消正在运行的任务

```bash
curl -X POST http://localhost:8000/api/embedding/task/task-uuid/cancel

# 响应示例
{
  "task_id": "task-uuid",
  "status": "cancelled",
  "partial_result_id": "partial-result-uuid"
}
```

### 10. 模型对比

```bash
# 对比不同模型的向量化结果
curl -X POST http://localhost:8000/api/embedding/compare \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc-123",
    "result_ids": ["result-bge-m3", "result-qwen3"]
  }'

# 响应示例
{
  "document_id": "doc-123",
  "results": [
    {
      "result_id": "result-bge-m3",
      "model": "bge-m3",
      "dimension": 1024,
      "processing_time_ms": 5000,
      "success_rate": 1.0,
      "cache_hit_rate": 0.3
    },
    {
      "result_id": "result-qwen3",
      "model": "qwen3-embedding-8b",
      "dimension": 4096,
      "processing_time_ms": 8000,
      "success_rate": 1.0,
      "cache_hit_rate": 0.0
    }
  ]
}
```

### 11. 设置活跃结果

```bash
# 将某个向量化结果设为活跃（用于后续检索）
curl -X POST http://localhost:8000/api/embedding/result/result-uuid/activate

# 响应示例
{
  "result_id": "result-uuid",
  "is_active": true
}
```

### 12. 智能模型推荐 🎯

```bash
# 获取单文档的模型推荐
curl -X POST http://localhost:8000/api/v1/embedding/recommend/single \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc-123",
    "document_name": "技术文档.pdf",
    "chunks": [
      {"chunk_id": "1", "content": "FastAPI 是一个现代化的高性能 Python Web 框架", "chunk_type": "text"},
      {"chunk_id": "2", "content": "使用 async/await 语法提供异步支持", "chunk_type": "text"}
    ],
    "top_n": 3
  }'

# 响应示例
{
  "document_analysis": {
    "document_id": "doc-123",
    "primary_language": "zh",
    "language_confidence": 0.95,
    "detected_domain": "tech",
    "domain_confidence": 0.88,
    "multimodal_ratio": 0.0,
    "total_chunks": 2
  },
  "recommendations": [
    {
      "rank": 1,
      "model": {
        "model_name": "qwen3-embedding-8b",
        "display_name": "通义千问 Embedding 8B",
        "total_score": 0.92,
        "dimension": 4096
      },
      "confidence": "high",
      "reasons": [
        {"key": "language_excellent", "description": "对zh语言支持出色", "impact": "positive"},
        {"key": "domain_expert", "description": "在tech领域有专长", "impact": "positive"}
      ]
    }
  ],
  "top_recommendation": {...}
}
```

### 13. 批量文档推荐

```bash
# 获取批量文档的统一推荐
curl -X POST http://localhost:8000/api/v1/embedding/recommend/batch \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "document_id": "doc-1",
        "document_name": "技术文档1.pdf",
        "chunks": [{"chunk_id": "1", "content": "Python 异步编程", "chunk_type": "text"}]
      },
      {
        "document_id": "doc-2",
        "document_name": "技术文档2.pdf",
        "chunks": [{"chunk_id": "1", "content": "FastAPI 路由配置", "chunk_type": "text"}]
      }
    ],
    "top_n": 3,
    "outlier_threshold": 0.3
  }'

# 响应示例（包含异常文档检测）
{
  "feature_summary": {
    "document_count": 2,
    "primary_language": "zh",
    "language_uniformity": 1.0,
    "primary_domain": "tech",
    "domain_uniformity": 1.0
  },
  "unified_recommendation": [...],
  "outlier_documents": []
}
```

### 14. 分析文档特征

```bash
# 仅分析文档特征，不获取推荐
curl -X POST http://localhost:8000/api/v1/embedding/recommend/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc-123",
    "document_name": "report.pdf",
    "chunks": [
      {"chunk_id": "1", "content": "Annual revenue increased by 20%", "chunk_type": "text"}
    ]
  }'

# 响应示例
{
  "document_id": "doc-123",
  "primary_language": "en",
  "language_confidence": 0.98,
  "detected_domain": "business",
  "domain_confidence": 0.85,
  "multimodal_ratio": 0.0,
  "feature_vector": [0.98, 0.02, 0.0, 0.0, 0.85, 0.0, 0.0, 0.0, 0.0, 0.0]
}
```

### 15. 缓存管理

```bash
# 查看缓存状态
curl http://localhost:8000/api/embedding/cache/status

# 响应示例
{
  "total_entries": 5000,
  "max_entries": 10000,
  "memory_usage_mb": 250.5,
  "hit_rate_7d": 0.45,
  "models": {
    "bge-m3": 3000,
    "qwen3-embedding-8b": 2000
  }
}

# 清除特定模型的缓存
curl -X DELETE http://localhost:8000/api/embedding/cache?model=bge-m3

# 清除所有缓存
curl -X DELETE http://localhost:8000/api/embedding/cache
```

---

## 前端使用

### 向量化进度界面

访问 `http://localhost:5173/documents/embed`，选择文档后：
1. 展开"高级配置"面板设置参数
2. 点击"开始向量化"触发任务
3. 进度条实时显示处理进度
4. 完成后显示统计图表

### 增量模式使用

1. 在高级配置中勾选"增量模式"
2. 对已向量化的文档再次执行
3. 系统自动跳过未变化的分块
4. 查看"缓存命中率"了解节省的计算量

### 模型对比功能

1. 对同一文档使用不同模型向量化
2. 点击"模型对比"按钮
3. 查看并排对比表格（处理时间、成功率等）
4. 选择最佳模型结果设为"活跃"

### 多模态文档处理

1. 上传包含图片/表格的文档
2. 完成分块后选择该文档
3. 系统自动显示分块类型分布
4. 向量化结果中可筛选查看不同类型

---

## 配置说明

### 向量化参数

| 参数 | 说明 | 范围 | 默认值 |
|------|------|------|--------|
| batch_size | 每批处理的分块数 | 10-200 | 50 |
| concurrency | 并发请求数 | 1-20 | 5 |
| enable_cache | 启用向量缓存 | true/false | true |
| incremental | 增量模式 | true/false | true |
| force_recompute | 强制重新计算 | true/false | false |

### 支持的模型

| 模型 | 维度 | 多模态 | 特点 |
|------|------|--------|------|
| bge-m3 | 1024 | ❌ | 多语言，速度快（推荐默认） |
| qwen3-embedding-8b | 4096 | ❌ | 高精度，长上下文 |
| hunyuan-embedding | 1024 | ❌ | 腾讯混元 |
| jina-embeddings-v4 | 2048 | ❌ | 多语言 |
| qwen3-vl-embedding-8b | 1024 | ✅ | 图文多模态 |

### 环境变量

```bash
# Embedding API 配置
EMBEDDING_API_KEY=your-api-key
EMBEDDING_API_BASE_URL=your-api-base-url

# 多模态模型配置
MULTIMODAL_EMBEDDING_MODEL=qwen3-vl-embedding-8b

# 批量处理配置
DEFAULT_BATCH_SIZE=50
DEFAULT_CONCURRENCY=5
MAX_BATCH_SIZE=200
MAX_CONCURRENCY=20

# 缓存配置
VECTOR_CACHE_BACKEND=memory  # memory | redis
VECTOR_CACHE_MAX_SIZE=10000
VECTOR_CACHE_TTL_DAYS=7

# Redis 配置（如果使用 Redis 缓存）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# 重试配置
RETRY_MAX_ATTEMPTS=3
RETRY_INITIAL_DELAY=1.0
RETRY_MAX_DELAY=32.0
```

---

## 常见问题

### Q: 增量向量化如何判断分块是否变化？
A: 使用 SHA-256 计算分块内容的哈希值，与历史记录对比判断是否变化。

### Q: 图片向量化失败时如何处理？
A: 系统自动降级为使用图片描述文本（caption）进行向量化，并在结果中标记"fallback"。

### Q: 缓存命中但维度不匹配怎么办？
A: 系统会检测维度不匹配的情况，自动重新计算向量而非使用缓存。

### Q: 向量化任务被取消后已处理的结果会保存吗？
A: 是的，取消任务会保存已完成的部分结果，可以在结果页面查看。

### Q: 如何选择合适的并发数？
A: 建议根据 API 限流情况调整。如果频繁遇到限流错误，系统会自动降低并发数。一般情况下默认值 5 即可满足需求。

### Q: 缓存占用太多内存怎么办？
A: 可以调整 `VECTOR_CACHE_MAX_SIZE` 降低缓存容量，或切换到 Redis 后端进行外部存储。

### Q: 多模态模型和普通模型可以混用吗？
A: 可以。系统会根据分块类型自动选择：图片使用多模态模型，其他内容使用普通模型。
