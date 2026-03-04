# Quickstart: 文档分块功能优化

**Branch**: `002-doc-chunking-opt` | **Date**: 2026-01-20

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

### 2. 使用智能策略推荐

```bash
# 1. 获取策略推荐
curl -X POST http://localhost:8000/api/chunking/recommend \
  -H "Content-Type: application/json" \
  -d '{"document_id": "doc-123"}'

# 响应示例
{
  "recommendations": [
    {
      "strategy": "heading",
      "strategy_name": "按标题分块",
      "reason": "检测到清晰的标题层级结构（H1: 3个, H2: 12个）",
      "confidence": 0.92,
      "estimated_chunks": 40,
      "is_top": true,
      "suggested_params": {"min_heading_level": 1, "max_heading_level": 3}
    }
  ]
}
```

### 3. 父子文档分块

```bash
# 创建父子分块任务
curl -X POST http://localhost:8000/api/chunking/chunk \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc-123",
    "strategy_type": "parent_child",
    "strategy_params": {
      "parent_size": 2000,
      "child_size": 400,
      "child_overlap": 50
    }
  }'

# 获取结果（包含父块）
curl "http://localhost:8000/api/chunking/result/result-456?include_parent=true"
```

### 4. 多模态分块

```bash
# 包含表格和图片的独立分块
curl -X POST http://localhost:8000/api/chunking/chunk \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc-123",
    "strategy_type": "multimodal",
    "strategy_params": {
      "include_tables": true,
      "include_images": true,
      "text_strategy": "semantic"
    }
  }'

# 按类型筛选分块
curl "http://localhost:8000/api/chunking/result/result-456/chunks?chunk_type=table"
```

### 5. 混合分块策略

```bash
curl -X POST http://localhost:8000/api/chunking/chunk \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc-123",
    "strategy_type": "hybrid",
    "hybrid_config": {
      "text": {"strategy": "semantic", "params": {"similarity_threshold": 0.3}},
      "code": {"strategy": "line", "params": {"lines_per_chunk": 50}},
      "table": {"strategy": "independent"},
      "image": {"strategy": "independent"}
    }
  }'
```

### 6. 策略对比预览

```bash
curl -X POST http://localhost:8000/api/chunking/compare \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc-123",
    "strategies": [
      {"strategy_type": "semantic", "strategy_params": {"similarity_threshold": 0.3}},
      {"strategy_type": "heading"},
      {"strategy_type": "parent_child", "strategy_params": {"parent_size": 2000}}
    ]
  }'
```

### 7. 版本管理

```bash
# 查看版本历史
curl http://localhost:8000/api/chunking/versions/doc-123

# 回滚到指定版本
curl -X POST http://localhost:8000/api/chunking/versions/result-old/rollback

# 版本对比
curl -X POST http://localhost:8000/api/chunking/versions/compare \
  -H "Content-Type: application/json" \
  -d '{"result_ids": ["result-v1", "result-v2"]}'
```

### 8. 大文档流式处理

```bash
# 使用 SSE 流式分块
curl -N http://localhost:8000/api/chunking/stream \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "large-doc-123",
    "strategy_type": "semantic",
    "segment_size": 100000
  }'

# 响应为 Server-Sent Events
# data: {"chunk_index": 0, "content": "...", "type": "text"}
# data: {"chunk_index": 1, "content": "...", "type": "text"}
# ...
```

---

## 前端使用

### 策略推荐卡片

访问 `http://localhost:5173/chunk`，选择文档后：
1. 系统自动分析文档结构
2. 显示推荐策略卡片（包含理由和预估效果）
3. 点击"应用此策略"一键配置

### 父子分块结果查看

1. 选择"父子文档分块"策略
2. 配置父块/子块大小
3. 执行分块后，切换到"树形视图"
4. 展开父块查看其子块

### 多模态分块类型筛选

1. 选择"多模态分块"策略
2. 启用表格/图片独立分块
3. 执行分块后，使用类型筛选下拉框
4. 不同类型显示不同图标（📝文本/📊表格/🖼️图片/💻代码）

---

## 配置说明

### 策略参数范围

| 策略 | 参数 | 范围 | 默认值 |
|------|------|------|--------|
| character | chunk_size | 100-5000 | 500 |
| character | overlap | 0-500 | 50 |
| semantic | similarity_threshold | 0.1-0.9 | 0.3 |
| semantic | min_chunk_size | 100-2000 | 300 |
| semantic | max_chunk_size | 500-5000 | 1200 |
| semantic | use_embedding | true/false | true |
| semantic | embedding_model | bge-m3/qwen3-embedding-8b | bge-m3 |
| parent_child | parent_size | 500-10000 | 2000 |
| parent_child | child_size | 100-2000 | 500 |
| parent_child | child_overlap | 0-200 | 50 |
| hybrid | embedding_model | bge-m3/qwen3-embedding-8b | bge-m3 |

### Embedding 模型选择指南

| 模型 | 维度 | 上下文长度 | 特点 | 适用场景 |
|------|------|------------|------|----------|
| bge-m3 | 1024 | 8K | 多语言，速度快 | 通用场景（推荐默认） |
| qwen3-embedding-8b | 4096 | 32K | 高精度，超长文本 | 精度敏感、长文档 |

### 环境变量

```bash
# Embedding API 配置（必须配置）
EMBEDDING_API_KEY=your-api-key
EMBEDDING_API_BASE_URL=your-api-base-url

# 语义分块默认 Embedding 模型
# 可选: bge-m3 (推荐) / qwen3-embedding-8b (高精度)
SEMANTIC_CHUNKER_MODEL=bge-m3
SEMANTIC_CHUNKER_USE_EMBEDDING=true
SEMANTIC_CHUNKER_SIMILARITY_THRESHOLD=0.7

# 多模态 Embedding 模型（未来扩展）
MULTIMODAL_EMBEDDING_MODEL=qwen3-vl-embedding-8b
MULTIMODAL_CHUNKER_USE_EMBEDDING=false

# 大文档阈值（字符数）
LARGE_DOCUMENT_THRESHOLD=50000000

# 流式处理段大小
STREAM_SEGMENT_SIZE=100000
```

---

## 常见问题

### Q: 父子分块和普通分块如何选择？
A: 如果您的应用需要精确检索 + 完整上下文，推荐父子分块。普通分块适合简单场景。

### Q: 多模态分块的图片如何向量化？
A: 优先使用图片 base64 直接向量化（qwen3-embedding-8b），失败时降级为文本描述向量化。

### Q: 语义分块算法升级后有什么变化？
A: 升级为基于统一 EmbeddingService 的 Embedding 相似度，支持 bge-m3（推荐）、qwen3-embedding-8b（高精度）两种模型。如果 Embedding 服务不可用，自动降级为 TF-IDF，最终降级为句子累加。

### Q: 如何选择 Embedding 模型？
A: 
- **bge-m3（推荐默认）**：1024维，8K上下文，多语言支持，速度快，适合大多数场景
- **qwen3-embedding-8b**：4096维，32K上下文，高精度，适合精度敏感或超长文本场景

### Q: 版本回滚会删除当前版本吗？
A: 不会。回滚只是将指定版本标记为 active，所有版本都保留。
