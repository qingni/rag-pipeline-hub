# Quickstart Guide: 向量索引模块

**Feature**: 004-vector-index  
**Last Updated**: 2025-12-24  
**Estimated Setup Time**: 15-30 minutes

## Overview

本指南将帮助你快速搭建和使用向量索引模块。系统支持两种向量数据库：
- **Milvus**（推荐）：生产环境，高性能，分布式
- **FAISS**：开发环境，轻量级，易于调试

**2024-12-24 更新**：新增从向量化任务创建索引的工作流程。

## 快速开始（推荐流程）

### 前置条件

1. 已完成文档向量化（至少有一个状态为 SUCCESS 的向量化任务）
2. 后端服务运行中（`http://localhost:8000`）
3. 前端服务运行中（`http://localhost:5173`）

### 步骤 1：访问向量索引页面

```
http://localhost:5173/vector-index
```

### 步骤 2：选择向量化任务

在左侧配置面板的「向量化任务」下拉框中：
- 选择一个已完成的向量化任务
- 系统自动显示任务详情（文档名称、模型、向量维度、向量数量）

### 步骤 3：选择向量数据库

| 选项 | 适用场景 |
|------|----------|
| **Milvus** | 生产环境、大规模数据（>10K向量） |
| **FAISS** | 开发测试、小规模数据（<10K向量） |

### 步骤 4：选择索引算法

| 算法 | 特点 | 推荐场景 |
|------|------|----------|
| **FLAT** | 精确搜索，无损失 | <10K 向量 |
| **IVF_FLAT** | 平衡精度和速度 | 10K-100K 向量 |
| **IVF_PQ** | 压缩存储，节省内存 | >100K 向量 |
| **HNSW** | 最快查询速度 | 对延迟敏感的场景 |

### 步骤 5：开始索引

点击「开始索引」按钮，系统将：
1. 读取向量化结果中的向量数据
2. 创建向量索引配置
3. 批量导入向量到选定的数据库
4. 构建索引结构
5. 更新统计信息

### 步骤 6：查看结果

- **索引结果 Tab**：显示当前索引的详细信息和统计
- **历史记录 Tab**：查看所有索引操作历史，支持查看详情和删除

## Prerequisites

### System Requirements

- **OS**: Linux/macOS (推荐) 或 Windows WSL2
- **Python**: 3.11+
- **Docker**: 20.10+ (Milvus部署)
  - **macOS**: 需要安装 Colima 来运行 Docker 容器
  - **Linux**: 直接使用系统 Docker
  - **Windows**: 推荐使用 Docker Desktop 或 WSL2 + Docker
- **PostgreSQL**: 14+ (元数据存储)
- **Memory**: 最小 4GB RAM，推荐 8GB+
- **Disk**: 10GB+ 可用空间

### Software Dependencies

```bash
# Python packages (already in requirements.txt)
pymilvus==2.3.4          # Milvus client
faiss-cpu==1.7.4         # FAISS library
fastapi==0.104.1         # Web framework
sqlalchemy==2.0.23       # ORM
psycopg2-binary==2.9.9   # PostgreSQL driver
```

## Installation

### Option 1: Milvus Production Setup (推荐)

#### Step 1: 启动 Docker 环境（macOS 需使用 Colima）

**macOS 用户必读**：macOS 需要使用 Colima 启动 Docker 运行时

**方式一：使用提供的脚本（推荐）**

```bash
# 从项目根目录运行
bash scripts/start_colima.sh
```

**方式二：手动启动**

```bash
# 1. 安装 Colima（如果尚未安装）
brew install colima

# 2. 启动 Colima（启动 Docker 运行时）
colima start --cpu 4 --memory 8 --disk 50

# 参数说明：
# --cpu 4: 分配 4 核 CPU
# --memory 8: 分配 8GB 内存
# --disk 50: 分配 50GB 磁盘空间

# 3. 验证 Docker 环境
docker ps
# 如果成功，应显示空的容器列表或已有容器

# 4. 查看 Colima 状态
colima status
# 应显示: colima is running
```

**Linux 用户**：可以直接使用系统的 Docker，跳过此步骤

**Windows 用户**：使用 Docker Desktop 或 WSL2 + Docker

#### Step 2: 启动 Milvus 服务

```bash
# 下载 Milvus Docker Compose 配置
cd /path/to/project
mkdir -p docker/milvus
cd docker/milvus

# 下载官方配置文件
wget https://github.com/milvus-io/milvus/releases/download/v2.3.4/milvus-standalone-docker-compose.yml -O docker-compose.yml

# 启动 Milvus
docker-compose up -d

# 验证服务状态
docker-compose ps
# Expected output:
# NAME                  SERVICE             STATUS
# milvus-standalone     standalone          running
# milvus-minio          minio              running
# milvus-etcd           etcd               running
```

#### Step 3: 配置 Milvus 连接

```bash
# backend/.env
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_USER=root
MILVUS_PASSWORD=Milvus
MILVUS_DB_NAME=default
```

#### Step 4: 初始化数据库

```bash
cd backend

# 创建 PostgreSQL 数据库
psql -U postgres -c "CREATE DATABASE rag_framework;"

# 运行迁移脚本
alembic upgrade head

# 或者直接执行 SQL
psql -U postgres -d rag_framework -f migrations/vector_index/001_create_vector_indexes_table.sql
```

#### Step 5: 验证 Milvus 连接

```python
# backend/scripts/test_milvus_connection.py
from pymilvus import connections, utility

# 连接 Milvus
connections.connect(
    alias="default",
    host="localhost",
    port="19530"
)

# 列出所有 Collection
collections = utility.list_collections()
print(f"Collections: {collections}")

# 检查服务器版本
print(f"Milvus version: {utility.get_server_version()}")
```

运行测试：
```bash
python backend/scripts/test_milvus_connection.py
# Expected output:
# Collections: []
# Milvus version: v2.3.4
```

---

### Option 2: FAISS Development Setup (快速开始)

#### Step 1: 安装 FAISS

```bash
# 已在 requirements.txt 中包含
pip install faiss-cpu==1.7.4

# 验证安装
python -c "import faiss; print(faiss.__version__)"
# Expected output: 1.7.4
```

#### Step 2: 配置本地存储

```bash
# backend/.env
VECTOR_INDEX_PROVIDER=faiss
FAISS_INDEX_DIR=/path/to/project/data/faiss_indexes
```

```bash
# 创建索引存储目录
mkdir -p data/faiss_indexes
```

#### Step 4: 初始化数据库

同 Milvus Setup Step 3

---

## Basic Usage

### 1. 启动后端服务

```bash
cd backend
python -m uvicorn main:app --reload --port 8000

# 服务启动在 http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### 2. 从向量化任务创建索引（推荐方式）

#### Step 1: 获取可用的向量化任务

```bash
curl -X GET "http://localhost:8000/api/v1/vector-index/embedding-tasks?status=SUCCESS"
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "tasks": [
      {
        "result_id": "emb_001",
        "document_id": "doc_12345",
        "document_name": "contract_v2.pdf",
        "model": "bge-m3",
        "vector_dimension": 1024,
        "successful_count": 150,
        "status": "SUCCESS",
        "created_at": "2025-12-24T08:00:00Z"
      }
    ],
    "total": 1
  }
}
```

#### Step 2: 创建索引

```bash
curl -X POST "http://localhost:8000/api/v1/vector-index/indexes/from-embedding" \
  -H "Content-Type: application/json" \
  -d '{
    "embedding_result_id": "emb_001",
    "provider": "MILVUS",
    "index_type": "HNSW",
    "metric_type": "COSINE",
    "index_params": {
      "M": 16,
      "efConstruction": 200
    }
  }'
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "id": "idx_001",
    "name": "contract_v2_index",
    "provider": "milvus",
    "dimension": 1024,
    "index_type": "HNSW",
    "vector_count": 150,
    "status": "building",
    "source_document_name": "contract_v2.pdf",
    "source_model": "bge-m3",
    "created_at": "2025-12-24T10:00:00Z"
  }
}
```

#### Step 3: 查看索引历史

```bash
curl -X GET "http://localhost:8000/api/v1/vector-index/indexes/history?page=1&page_size=20"
```

### 3. 手动创建索引（高级用法）

#### 使用 Milvus

```bash
curl -X POST "http://localhost:8000/api/v1/indexes" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_first_index",
    "provider": "milvus",
    "dimension": 1536,
    "index_type": "HNSW",
    "metric_type": "cosine",
    "index_params": {
      "M": 16,
      "efConstruction": 200
    },
    "namespace": "default"
  }'
```

#### 使用 FAISS

```bash
curl -X POST "http://localhost:8000/api/v1/indexes" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_first_index",
    "provider": "faiss",
    "dimension": 1536,
    "index_type": "IndexFlatIP",
    "metric_type": "cosine",
    "namespace": "default"
  }'
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "my_first_index",
    "provider": "milvus",
    "status": "building",
    "created_at": "2025-12-23T10:00:00Z"
  },
  "timestamp": "2025-12-23T10:00:00Z"
}
```

### 3. 添加向量

```bash
curl -X POST "http://localhost:8000/api/v1/indexes/my_first_index/vectors" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": [
      {
        "vector_id": "vec_001",
        "embedding": [0.123, -0.456, 0.789, ...],
        "document_id": "doc_12345",
        "text_content": "Sample text content",
        "metadata": {
          "source": "sample.pdf",
          "page": 1
        }
      }
    ]
  }'
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "inserted_count": 1,
    "index_status": "ready"
  },
  "timestamp": "2025-12-23T10:05:00Z"
}
```

### 4. 向量检索

```bash
curl -X POST "http://localhost:8000/api/v1/indexes/my_first_index/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query_vector": [0.123, -0.456, 0.789, ...],
    "top_k": 5,
    "threshold": 0.8
  }'
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "results": [
      {
        "vector_id": "vec_001",
        "score": 0.9523,
        "document_id": "doc_12345",
        "text_content": "Sample text content",
        "metadata": {
          "source": "sample.pdf",
          "page": 1
        },
        "rank": 1
      }
    ],
    "query_latency_ms": 42.3
  },
  "timestamp": "2025-12-23T10:10:00Z"
}
```

### 5. 查看索引统计

```bash
curl -X GET "http://localhost:8000/api/v1/indexes/my_first_index/stats"
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "vector_count": 1250,
    "index_size_mb": 11.5,
    "avg_query_latency_ms": 38.7,
    "query_count_24h": 342,
    "error_count_24h": 0
  },
  "timestamp": "2025-12-23T10:15:00Z"
}
```

---

## Frontend Setup

### 1. 安装前端依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
# 服务启动在 http://localhost:5173
```

### 3. 访问向量索引页面

打开浏览器访问：`http://localhost:5173/vector-index`

**页面功能**：
- 左侧面板：索引列表、创建索引、搜索控制
- 右侧内容：搜索结果展示、索引统计图表

---

## Common Workflows

### Workflow 1: 从 Embedding 到检索

```python
# Step 1: 获取文档的 Embedding 结果
with open('results/document_embedding_20251223.json', 'r') as f:
    embedding_result = json.load(f)

# Step 2: 创建向量索引
import requests
response = requests.post('http://localhost:8000/api/v1/indexes', json={
    'name': 'my_docs_index',
    'provider': 'milvus',
    'dimension': 1536,
    'index_type': 'HNSW',
    'metric_type': 'cosine'
})
index_id = response.json()['data']['id']

# Step 3: 批量插入向量
vectors = []
for chunk in embedding_result['chunks']:
    vectors.append({
        'vector_id': chunk['id'],
        'embedding': chunk['embedding'],
        'document_id': embedding_result['document_id'],
        'text_content': chunk['text'],
        'metadata': chunk['metadata']
    })

requests.post(f'http://localhost:8000/api/v1/indexes/my_docs_index/vectors', 
              json={'vectors': vectors})

# Step 4: 执行相似度检索
query_text = "What is the contract termination clause?"
query_embedding = get_embedding(query_text)  # 调用 Embedding API

response = requests.post(f'http://localhost:8000/api/v1/indexes/my_docs_index/search',
                         json={
                             'query_vector': query_embedding,
                             'top_k': 5,
                             'threshold': 0.7
                         })
results = response.json()['data']['results']
```

### Workflow 2: 索引更新

```python
# 添加新向量
requests.post(f'http://localhost:8000/api/v1/indexes/{index_name}/vectors',
              json={'vectors': new_vectors})

# 删除向量
requests.delete(f'http://localhost:8000/api/v1/indexes/{index_name}/vectors',
                json={'vector_ids': ['vec_001', 'vec_002']})

# 更新向量（删除后重新插入）
requests.delete(f'http://localhost:8000/api/v1/indexes/{index_name}/vectors',
                json={'vector_ids': ['vec_001']})
requests.post(f'http://localhost:8000/api/v1/indexes/{index_name}/vectors',
              json={'vectors': [updated_vector]})
```

### Workflow 3: 跨索引检索

```python
# 同时查询多个索引
indexes = ['legal_docs', 'technical_docs', 'customer_support']
all_results = []

for index_name in indexes:
    response = requests.post(f'http://localhost:8000/api/v1/indexes/{index_name}/search',
                             json={'query_vector': query_embedding, 'top_k': 5})
    results = response.json()['data']['results']
    
    # 添加来源标记
    for r in results:
        r['source_index'] = index_name
    all_results.extend(results)

# 合并并排序结果
all_results.sort(key=lambda x: x['score'], reverse=True)
top_results = all_results[:10]
```

---

## Configuration Guide

### Backend Configuration (backend/.env)

```bash
# Milvus Configuration
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_USER=root
MILVUS_PASSWORD=Milvus
MILVUS_DB_NAME=default

# FAISS Configuration
FAISS_INDEX_DIR=/path/to/faiss_indexes
FAISS_AUTO_SAVE_INTERVAL=300  # 5 minutes

# General Settings
VECTOR_INDEX_DEFAULT_PROVIDER=milvus  # or 'faiss'
VECTOR_INDEX_BATCH_SIZE=1000
VECTOR_INDEX_MAX_QUERY_TIMEOUT=10  # seconds
```

### Index Configuration Examples

#### High Performance (HNSW)

```json
{
  "index_type": "HNSW",
  "index_params": {
    "M": 32,
    "efConstruction": 500
  },
  "search_params": {
    "ef": 200
  }
}
```

#### Balanced (IVF_FLAT)

```json
{
  "index_type": "IVF_FLAT",
  "index_params": {
    "nlist": 1024
  },
  "search_params": {
    "nprobe": 16
  }
}
```

#### Memory Efficient (IVF_PQ)

```json
{
  "index_type": "IVF_PQ",
  "index_params": {
    "nlist": 1024,
    "m": 8,
    "nbits": 8
  },
  "search_params": {
    "nprobe": 16
  }
}
```

---

## Performance Tuning

### Milvus Performance Tips

1. **选择合适的索引类型**：
   - < 10K vectors: FLAT
   - 10K - 1M vectors: IVF_FLAT or HNSW
   - > 1M vectors: IVF_PQ or HNSW

2. **调整 HNSW 参数**：
   - `M`: 增加提升精度，但占用更多内存（推荐 8-64）
   - `efConstruction`: 构建时搜索范围（推荐 100-500）
   - `ef`: 查询时搜索范围（推荐 100-500）

3. **批量操作**：
   - 使用批量插入（batch_size=1000）
   - 使用批量查询减少网络开销

4. **定期 Flush**：
   ```python
   collection.flush()  # 强制持久化
   ```

### FAISS Performance Tips

1. **预归一化向量**（余弦相似度）：
   ```python
   faiss.normalize_L2(vectors)
   ```

2. **使用 GPU**（如有）：
   ```bash
   pip install faiss-gpu
   ```

3. **调整 IVF 参数**：
   - `nlist`: 聚类中心数（推荐 sqrt(N)）
   - `nprobe`: 查询时访问的聚类数（1-nlist）

---

## Troubleshooting

### Issue 1: Milvus 连接失败

**Symptoms**: `Error: failed to connect to Milvus: connection refused`

**Solutions**:
```bash
# 检查 Milvus 服务状态
docker-compose ps

# 重启 Milvus
docker-compose restart

# 检查端口占用
lsof -i:19530

# 查看 Milvus 日志
docker-compose logs milvus-standalone
```

**macOS 专属问题**：Colima 未启动或失败

```bash
# 检查 Colima 状态
colima status

# 如果未启动，启动 Colima
colima start --cpu 4 --memory 8 --disk 50

# 如果 Colima 启动失败，重置并重启
colima stop
colima delete
colima start --cpu 4 --memory 8 --disk 50

# 验证 Docker 可用性
docker ps

# 如果 Docker 命令不可用，检查 Docker context
docker context ls
docker context use colima  # 切换到 Colima context
```

### Issue 2: FAISS 索引加载失败

**Symptoms**: `RuntimeError: Invalid index file`

**Solutions**:
```bash
# 检查文件权限
ls -l data/faiss_indexes/

# 验证索引文件完整性
python -c "import faiss; index = faiss.read_index('path/to/index.faiss'); print(index.ntotal)"

# 重建索引
# 删除损坏的文件并重新构建
```

### Issue 3: 查询延迟过高

**Symptoms**: 查询耗时 > 100ms

**Solutions**:
1. 检查索引类型和参数配置
2. 减少 `nprobe` 或 `ef` 参数
3. 使用更高效的索引类型（如 HNSW）
4. 考虑使用 GPU 加速
5. 检查数据库和网络延迟

### Issue 4: 内存不足

**Symptoms**: `MemoryError: cannot allocate memory`

**Solutions**:
1. 使用 IVF_PQ 压缩索引
2. 增加系统内存
3. 分批加载和查询
4. 使用 mmap 文件映射（FAISS）

---

## Next Steps

1. **阅读 API 文档**: http://localhost:8000/docs
2. **查看数据模型**: [data-model.md](./data-model.md)
3. **了解实现计划**: [plan.md](./plan.md)
4. **执行任务清单**: [tasks.md](./tasks.md)（Phase 2 后生成）

---

## Additional Resources

- **Milvus Documentation**: https://milvus.io/docs
- **FAISS Wiki**: https://github.com/facebookresearch/faiss/wiki
- **API Contract**: [contracts/vector-index-api.yaml](./contracts/vector-index-api.yaml)
- **Project Constitution**: [.specify/memory/constitution.md](../../.specify/memory/constitution.md)

---

## Support

如遇问题，请：
1. 查看 Troubleshooting 章节
2. 检查后端日志：`backend/logs/vector_index.log`
3. 提交 Issue 或联系开发团队
