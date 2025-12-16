# 向量嵌入功能优化说明

## 优化概述

向量嵌入功能已优化,现在直接使用文档分块后的JSON文件作为数据源,实现了完整的文档处理流程:

```
文档上传 → 文档加载 → 文档分块 → 向量嵌入 → 语义搜索
```

## 主要变更

### 1. 新增接口

#### POST `/api/embedding/from-chunking-result`
基于分块结果ID进行向量化,将分块结果中的所有分块转换为向量。

**请求参数:**
```json
{
  "result_id": "chunking-result-uuid",
  "model": "qwen3-embedding-8b",
  "max_retries": 3,
  "timeout": 60
}
```

**响应:**
```json
{
  "request_id": "embedding-request-uuid",
  "status": "SUCCESS",
  "vectors": [
    {
      "index": 0,
      "vector": [0.123, -0.456, ...],
      "dimension": 1536,
      "text_hash": "sha256:...",
      "text_length": 250,
      "processing_time_ms": 120.5
    }
  ],
  "failures": [],
  "metadata": {
    "model": "qwen3-embedding-8b",
    "batch_size": 50,
    "successful_count": 50,
    "failed_count": 0,
    "processing_time_ms": 6250.3,
    "vectors_per_second": 8.0
  },
  "timestamp": "2025-12-15T10:30:00Z"
}
```

#### POST `/api/embedding/from-document`
基于文档ID进行向量化,自动使用该文档最新的活跃分块结果。

**请求参数:**
```json
{
  "document_id": "document-uuid",
  "model": "qwen3-embedding-8b",
  "strategy_type": "paragraph",  // 可选,用于过滤分块策略
  "max_retries": 3,
  "timeout": 60
}
```

### 2. 工作流程

#### 方式1: 通过分块结果ID
```python
# 1. 获取分块结果ID (通过分块API)
POST /api/chunking/chunk
{
  "document_id": "doc-123",
  "strategy_type": "paragraph",
  "parameters": {"chunk_size": 500}
}
# 返回: result_id

# 2. 使用分块结果ID进行向量化
POST /api/embedding/from-chunking-result
{
  "result_id": "result-uuid",
  "model": "qwen3-embedding-8b"
}
```

#### 方式2: 通过文档ID (推荐)
```python
# 直接使用文档ID,系统自动选择最新的分块结果
POST /api/embedding/from-document
{
  "document_id": "doc-123",
  "model": "qwen3-embedding-8b",
  "strategy_type": "paragraph"  // 可选
}
```

### 3. 结果持久化

向量嵌入结果会保存为JSON文件,包含源信息追踪:

**文件路径:** `results/embedding/{YYYY-MM-DD}/embedding_{request_id}_{timestamp}.json`

**文件内容:**
```json
{
  "request_id": "...",
  "status": "SUCCESS",
  "timestamp": "2025-12-15T10:30:00Z",
  "source": {
    "chunking_result_id": "result-uuid",  // 或 document_id
    "document_id": "doc-123"
  },
  "metadata": { ... },
  "vectors": [ ... ],
  "failures": []
}
```

## API端点总览

| 端点 | 方法 | 说明 | 优先级 |
|------|------|------|--------|
| `/api/embedding/from-chunking-result` | POST | 基于分块结果ID向量化 | P1 |
| `/api/embedding/from-document` | POST | 基于文档ID向量化(自动选择最新分块) | P1 |
| `/api/embedding/single` | POST | 单文本向量化(用于查询) | P2 |
| `/api/embedding/batch` | POST | 批量文本向量化 | P3 |
| `/api/embedding/models` | GET | 列出所有支持的模型 | - |
| `/api/embedding/models/{model_name}` | GET | 获取模型详情 | - |
| `/api/embedding/health` | GET | 健康检查 | - |

## 支持的模型

| 模型名称 | 维度 | 说明 |
|----------|------|------|
| qwen3-embedding-8b | 1536 | 通义千问 Embedding 模型 (推荐) |
| bge-m3 | 1024 | BGE-M3 多语言模型 |
| hunyuan-embedding | 1024 | 腾讯混元 Embedding 模型 |
| jina-embeddings-v4 | 768 | Jina AI Embeddings v4 |

## 测试脚本

使用提供的测试脚本验证功能:

```bash
cd backend
python test_embedding_from_chunks.py
```

测试脚本包含:
1. 基于分块结果ID的向量化测试
2. 基于文档ID的向量化测试  
3. 单文本向量化测试
4. 模型列表查询

## 环境变量

确保设置以下环境变量:

```bash
# 必需
export EMBEDDING_API_KEY="your-api-key"

# 可选 (有默认值)
export EMBEDDING_API_BASE_URL="http://dev.fit-ai.woa.com/api/llmproxy"
export EMBEDDING_RESULTS_DIR="results/embedding"
```

## 错误处理

### 常见错误

| 错误码 | HTTP状态 | 说明 |
|--------|----------|------|
| CHUNKING_RESULT_NOT_FOUND | 404 | 分块结果不存在或未完成 |
| DOCUMENT_OR_CHUNKING_RESULT_NOT_FOUND | 404 | 文档或分块结果不存在 |
| INVALID_TEXT_ERROR | 400 | 文本内容无效(空或空白) |
| AUTHENTICATION_ERROR | 401 | API密钥无效 |
| RATE_LIMIT_ERROR | 429 | 超出API调用限制 |
| BATCH_SIZE_LIMIT_EXCEEDED | 413 | 批量大小超限(>1000) |

### 自动重试

系统会自动对以下错误进行重试(指数退避):
- 速率限制错误 (RATE_LIMIT_ERROR)
- 超时错误 (API_TIMEOUT_ERROR)
- 网络错误 (NETWORK_ERROR)

重试配置:
- 最大重试次数: 3
- 初始延迟: 1秒
- 最大延迟: 32秒
- 抖动: ±25%

## 性能指标

- **单分块向量化**: <2秒 (正常条件下)
- **批量向量化 (100分块)**: <30秒
- **首次成功率**: >95% (24小时滚动窗口)
- **重试恢复率**: >80% (临时网络故障)

## 与现有功能的兼容性

现有的单文本和批量文本向量化接口保持不变,新功能是附加的:

- ✅ `/api/embedding/single` - 继续支持,用于查询向量化
- ✅ `/api/embedding/batch` - 继续支持,用于任意文本批量向量化
- ✨ `/api/embedding/from-chunking-result` - **新增**
- ✨ `/api/embedding/from-document` - **新增**

## 下一步

1. 测试新的向量嵌入接口
2. 将向量存储到向量数据库(如Milvus/Qdrant)
3. 实现语义搜索功能
4. 完善前端UI集成

## 相关文档

- [Feature Spec](../../specs/003-vector-embedding/spec.md)
- [Implementation Plan](../../specs/003-vector-embedding/plan.md)
- [API Documentation](../../specs/003-vector-embedding/contracts/openapi.yaml)
