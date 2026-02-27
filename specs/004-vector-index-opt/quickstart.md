# Quickstart: 向量索引模块（优化版）

**Branch**: `004-vector-index-opt`
**Date**: 2026-02-06

## 概述

本指南帮助你快速上手向量索引模块，包括环境准备、基本操作和常见场景。

---

## 前置条件

### 1. Milvus 服务

确保 Milvus 2.4+ 服务已启动（需要 2.4+ 版本以支持 hybrid_search）：

```bash
# Docker 方式启动 Milvus Standalone
docker run -d --name milvus-standalone \
  -p 19530:19530 \
  -p 9091:9091 \
  -v /tmp/milvus:/var/lib/milvus \
  milvusdb/milvus:v2.4.0 \
  milvus run standalone

# 验证服务状态
curl http://localhost:9091/healthz
```

### 2. 后端服务

```bash
cd backend

# 安装依赖（包含 FlagEmbedding 用于 Reranker）
pip install -r requirements.txt

# 配置环境变量
cat > .env << EOF
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_POOL_SIZE=10

# Reranker 配置
RERANKER_MODEL=qwen3-reranker-4b
RERANKER_USE_FP16=true
RERANKER_TOP_N=20
EOF

# 启动服务（首次启动会自动下载 Reranker 模型）
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 前端服务

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

---

## 快速开始

### 场景 1: 通过 Web 界面创建索引

1. 打开浏览器访问 `http://localhost:5173`
2. 点击左侧导航栏「向量索引」
3. 在左侧配置区：
   - 选择已完成的向量化任务
   - **系统自动填充推荐的索引算法和度量类型**（旁边显示推荐理由标签）
   - 如需调整，可手动修改下拉框选择
4. 点击「开始索引」按钮
5. 观察右侧进度条，等待索引构建完成
6. 在「历史记录」Tab 查看索引详情

### 场景 1b: 通过 API 获取智能推荐

```bash
# 获取推荐的索引算法和度量类型
curl -X POST http://localhost:8000/api/v1/vector-index/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "embedding_task_id": "<your-embedding-task-id>"
  }'

# 响应示例
{
  "success": true,
  "data": {
    "recommended_index_type": "FLAT",
    "recommended_metric_type": "COSINE",
    "reason": "基于 BAAI/bge-m3 1024维 + 5000条向量推荐 — 数据量 5000 条 < 1万，FLAT 暴力搜索保证精确结果",
    "is_fallback": false,
    "vector_count": 5000,
    "dimension": 1024,
    "embedding_model": "BAAI/bge-m3"
  }
}

# 记录用户采纳行为（创建索引时调用）
curl -X POST http://localhost:8000/api/v1/vector-index/recommend/log \
  -H "Content-Type: application/json" \
  -d '{
    "embedding_task_id": "<your-embedding-task-id>",
    "recommended_index_type": "FLAT",
    "recommended_metric_type": "COSINE",
    "final_index_type": "FLAT",
    "final_metric_type": "COSINE",
    "reason": "数据量 < 1万，FLAT 暴力搜索保证精确结果"
  }'

# 查看推荐采纳率统计
curl -X GET "http://localhost:8000/api/v1/vector-index/recommend/stats?days=30"
```

### 场景 2: 通过 API 创建索引

```bash
# 1. 获取可用的向量化任务列表
curl -X GET http://localhost:8000/api/v1/vector-index/embedding-tasks

# 2. 创建索引
curl -X POST http://localhost:8000/api/v1/vector-index/indexes \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "my_first_index",
    "embedding_task_id": "<your-embedding-task-id>",
    "index_type": "HNSW",
    "metric_type": "L2",
    "index_params": {
      "M": 16,
      "efConstruction": 200
    }
  }'

# 3. 查询任务进度
curl -X GET http://localhost:8000/api/v1/vector-index/tasks/<task_id>

# 4. 等待状态变为 completed
```

### 场景 3: 执行向量检索（纯稠密）

```bash
# 单向量查询
curl -X POST http://localhost:8000/api/v1/vector-index/search \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "my_first_index",
    "query_vector": [0.1, 0.2, ..., 0.5],
    "top_k": 5,
    "threshold": 0.8
  }'

# 批量查询
curl -X POST http://localhost:8000/api/v1/vector-index/batch-search \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "my_first_index",
    "query_vectors": [
      [0.1, 0.2, ..., 0.5],
      [0.3, 0.4, ..., 0.6]
    ],
    "top_k": 5
  }'
```

### 场景 3b: 混合检索（稠密+稀疏 + RRF + Reranker） — 新增

```bash
# 混合检索（稠密+稀疏双路召回 → RRF 粗排 → Reranker 精排）
curl -X POST http://localhost:8000/api/v1/vector-index/hybrid-search \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "my_first_index",
    "query_text": "什么是向量检索？",
    "query_dense_vector": [0.1, 0.2, ..., 0.5],
    "query_sparse_vector": {"23": 0.45, "1089": 0.32, "5672": 0.18},
    "top_n": 20,
    "top_k": 5,
    "enable_reranker": true
  }'

# 响应示例
{
  "success": true,
  "search_mode": "hybrid",
  "data": [
    {
      "vector_id": 42,
      "doc_id": "doc_001",
      "chunk_index": 3,
      "rrf_score": 0.032,
      "reranker_score": 0.95,
      "final_score": 0.95,
      "text": "向量检索是一种基于向量空间模型的信息检索方法...",
      "search_mode": "hybrid"
    }
  ],
  "query_time_ms": 156.3,
  "rrf_time_ms": 45.2,
  "reranker_time_ms": 98.1,
  "total_candidates": 20
}
```

> **降级模式**：当 `query_sparse_vector` 为空或 Collection 不含稀疏字段时，系统自动降级到纯稠密检索模式，`search_mode` 返回 `"dense_only"`。

### 场景 4: 增量更新索引

```bash
# 添加新向量
curl -X POST http://localhost:8000/api/v1/vector-index/indexes/my_first_index/vectors \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": [
      {
        "doc_id": "doc_new_001",
        "chunk_index": 0,
        "embedding": [0.1, 0.2, ..., 0.5],
        "metadata": {"source": "新增文档"}
      }
    ]
  }'

# 删除向量（幂等性）
curl -X DELETE http://localhost:8000/api/v1/vector-index/indexes/my_first_index/vectors \
  -H "Content-Type: application/json" \
  -d '{
    "vector_ids": [123, 456, 789]
  }'
```

---

## Python SDK 示例

```python
import httpx

class VectorIndexClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.client = httpx.Client()
    
    def get_recommendation(
        self,
        embedding_task_id: str
    ) -> dict:
        """获取智能推荐的索引配置"""
        response = self.client.post(
            f"{self.base_url}/vector-index/recommend",
            json={"embedding_task_id": embedding_task_id}
        )
        return response.json()
    
    def create_index(
        self,
        collection_name: str,
        embedding_task_id: str,
        index_type: str = "HNSW",
        metric_type: str = "L2"
    ) -> dict:
        """创建向量索引"""
        response = self.client.post(
            f"{self.base_url}/vector-index/indexes",
            json={
                "collection_name": collection_name,
                "embedding_task_id": embedding_task_id,
                "index_type": index_type,
                "metric_type": metric_type
            }
        )
        return response.json()
    
    def search(
        self,
        collection_name: str,
        query_vector: list,
        top_k: int = 5,
        threshold: float = None
    ) -> dict:
        """向量相似度检索（纯稠密）"""
        payload = {
            "collection_name": collection_name,
            "query_vector": query_vector,
            "top_k": top_k
        }
        if threshold is not None:
            payload["threshold"] = threshold
        
        response = self.client.post(
            f"{self.base_url}/vector-index/search",
            json=payload
        )
        return response.json()
    
    def hybrid_search(
        self,
        collection_name: str,
        query_text: str,
        query_dense_vector: list,
        query_sparse_vector: dict = None,
        top_n: int = 20,
        top_k: int = 5,
        enable_reranker: bool = True
    ) -> dict:
        """混合检索（稠密+稀疏 + RRF + Reranker）"""
        payload = {
            "collection_name": collection_name,
            "query_text": query_text,
            "query_dense_vector": query_dense_vector,
            "top_n": top_n,
            "top_k": top_k,
            "enable_reranker": enable_reranker
        }
        if query_sparse_vector is not None:
            payload["query_sparse_vector"] = query_sparse_vector
        
        response = self.client.post(
            f"{self.base_url}/vector-index/hybrid-search",
            json=payload
        )
        return response.json()
    
    def get_task_progress(self, task_id: str) -> dict:
        """获取任务进度"""
        response = self.client.get(
            f"{self.base_url}/vector-index/tasks/{task_id}"
        )
        return response.json()


# 使用示例
client = VectorIndexClient()

# 创建索引
result = client.create_index(
    collection_name="demo_index",
    embedding_task_id="abc-123-def"
)
print(f"Task ID: {result['task_id']}")

# 等待完成后检索（纯稠密）
search_result = client.search(
    collection_name="demo_index",
    query_vector=[0.1] * 1536,
    top_k=5,
    threshold=0.8
)
for item in search_result['data']:
    print(f"Doc: {item['doc_id']}, Score: {item['score']:.4f}")

# 混合检索（稠密+稀疏 + Reranker）
hybrid_result = client.hybrid_search(
    collection_name="demo_index",
    query_text="什么是向量检索？",
    query_dense_vector=[0.1] * 1536,
    query_sparse_vector={"23": 0.45, "1089": 0.32},
    top_k=5
)
print(f"Search mode: {hybrid_result.get('search_mode')}")
for item in hybrid_result['data']:
    print(f"Doc: {item['doc_id']}, Reranker: {item.get('reranker_score', 'N/A')}")
```

---

## 索引算法选择指南

> 💡 **提示**：选择向量化任务后，系统会根据下表规则自动推荐最佳索引算法和度量类型。

| 场景 | 推荐算法 | 推荐度量 | 理由 |
|------|---------|---------|------|
| 小规模数据 (<10K) | FLAT | 按模型推断 | 100% 召回率，无需调参 |
| 中等规模 (10K-1M) + 低维度 (≤256) | IVF_FLAT | 按模型推断 | IVF 聚类效率高、内存开销低 |
| 中等规模 (10K-1M) + 高维度 (>256) | HNSW | 按模型推断 | 图索引召回率与速度兼优 |
| 大规模数据 (>1M) | IVF_PQ | 按模型推断 | PQ 压缩显著降低内存占用 |

**度量类型推断规则**：
| Embedding 模型 | 推荐度量 | 理由 |
|----------------|---------|------|
| BGE 系列 (bge-m3 等) | COSINE | 归一化输出，余弦相似度最佳 |
| OpenAI (text-embedding 等) | COSINE | 归一化输出 |
| 未识别/自定义模型 | L2 | 通用安全默认值 |

---

## 常见问题

### Q1: Milvus 连接失败怎么办？

检查 Milvus 服务状态：
```bash
docker ps | grep milvus
curl http://localhost:9091/healthz
```

系统会自动进行指数退避重试（1s→2s→4s），最多3次。

### Q2: 索引构建很慢怎么办？

1. 减少单批次向量数量
2. 使用更简单的索引算法（如 FLAT 或 IVF_FLAT）
3. 增加 Milvus 资源配置

### Q3: 检索结果不准确怎么办？

1. 检查向量维度是否匹配
2. 调整搜索参数（如增加 `nprobe` 或 `ef`）
3. 考虑使用更精确的索引算法（如 FLAT）
4. **推荐**：启用混合检索（hybrid-search），稠密+稀疏双路召回 + Reranker 精排能显著提升检索准确率

### Q4: 混合检索比纯稠密检索慢怎么办？

1. 减小 `top_n`（粗排候选集大小），默认 20 已足够
2. 确保 Reranker 模型使用 FP16 推理（`RERANKER_USE_FP16=true`）
3. 如果不需要精排，设置 `enable_reranker: false` 仅使用 RRF 粗排
4. 混合检索预期总耗时 < 200ms（粗排 ~50ms + 精排 ~100ms）

### Q5: 稀疏向量为空时会发生什么？

系统会自动降级到纯稠密检索模式（`search_mode: "dense_only"`），不影响可用性。响应中的 `search_mode` 字段可告知实际使用的检索模式。

---

## 下一步

- 查看 [API 契约文档](./contracts/index-api.yaml) 了解完整接口
- 阅读 [数据模型文档](./data-model.md) 了解实体设计
- 参考 [技术研究文档](./research.md) 了解设计决策
