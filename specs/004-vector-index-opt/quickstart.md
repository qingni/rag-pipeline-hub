# Quickstart: 向量索引模块（优化版）

**Branch**: `004-vector-index-opt`
**Date**: 2026-02-06

## 概述

本指南帮助你快速上手向量索引模块，包括环境准备、基本操作和常见场景。

---

## 前置条件

### 1. Milvus 服务

确保 Milvus 2.x 服务已启动：

```bash
# Docker 方式启动 Milvus Standalone
docker run -d --name milvus-standalone \
  -p 19530:19530 \
  -p 9091:9091 \
  -v /tmp/milvus:/var/lib/milvus \
  milvusdb/milvus:v2.3.4 \
  milvus run standalone

# 验证服务状态
curl http://localhost:9091/healthz
```

### 2. 后端服务

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cat > .env << EOF
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_POOL_SIZE=10
EOF

# 启动服务
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
   - 选择索引算法（推荐 HNSW）
4. 点击「开始索引」按钮
5. 观察右侧进度条，等待索引构建完成
6. 在「历史记录」Tab 查看索引详情

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

### 场景 3: 执行向量检索

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
        """向量相似度检索"""
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

# 等待完成后检索
search_result = client.search(
    collection_name="demo_index",
    query_vector=[0.1] * 1536,
    top_k=5,
    threshold=0.8
)
for item in search_result['data']:
    print(f"Doc: {item['doc_id']}, Score: {item['score']:.4f}")
```

---

## 索引算法选择指南

| 场景 | 推荐算法 | 理由 |
|------|---------|------|
| 小规模数据 (<10K) | FLAT | 100% 召回率，无需调参 |
| 中等规模 (10K-1M) | HNSW | 高召回率 + 低延迟 |
| 大规模数据 (>1M) | IVF_PQ | 内存效率高，适合海量数据 |
| 对召回率要求极高 | IVF_FLAT | 平衡精度与速度 |

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

---

## 下一步

- 查看 [API 契约文档](./contracts/index-api.yaml) 了解完整接口
- 阅读 [数据模型文档](./data-model.md) 了解实体设计
- 参考 [技术研究文档](./research.md) 了解设计决策
