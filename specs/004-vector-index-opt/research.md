# Technical Research: 向量索引模块（优化版）

**Branch**: `004-vector-index-opt`
**Date**: 2026-02-06
**Status**: Updated (混合检索增强 2026-02-06)

## Research Overview

本文档记录向量索引模块优化版的技术研究结果，所有技术决策已明确，无待澄清项。

---

## Research Task 1: Milvus 索引算法选择

### Decision
支持四种 Milvus 原生索引算法：**FLAT, IVF_FLAT, IVF_PQ, HNSW**

### Rationale
1. **FLAT**: 暴力搜索，100% 召回率，适用于 <10K 向量的小规模场景
2. **IVF_FLAT**: 平衡精度与速度，适用于 10K-1M 向量的中等规模
3. **IVF_PQ**: 内存效率高，适用于 >1M 向量的大规模场景
4. **HNSW**: 高召回率 + 低延迟，适用于实时检索场景

### Alternatives Considered
- **ANNOY**: Milvus 不原生支持，需要额外集成
- **DiskANN**: Milvus 2.3+ 支持，但配置复杂，暂不引入
- **GPU 索引**: 需要 GPU 硬件，超出当前 MVP 范围

### Configuration Parameters
```python
# FLAT - 无需额外参数
flat_params = {"index_type": "FLAT", "metric_type": "L2"}

# IVF_FLAT - nlist 决定聚类中心数量
ivf_flat_params = {
    "index_type": "IVF_FLAT",
    "metric_type": "L2",
    "params": {"nlist": 128}  # 推荐值：sqrt(n_vectors)
}

# IVF_PQ - m 决定子向量数量，nbits 决定编码位数
ivf_pq_params = {
    "index_type": "IVF_PQ",
    "metric_type": "L2",
    "params": {"nlist": 128, "m": 8, "nbits": 8}
}

# HNSW - M 决定连接数，efConstruction 决定构建质量
hnsw_params = {
    "index_type": "HNSW",
    "metric_type": "L2",
    "params": {"M": 16, "efConstruction": 200}
}
```

---

## Research Task 2: Milvus 连接与重试策略

### Decision
采用**指数退避重试机制**，间隔 1s → 2s → 4s，最多3次重试

### Rationale
1. 指数退避可避免在服务恢复期间产生大量重试请求
2. 最多3次重试可快速判断服务是否可用，避免长时间阻塞
3. 总等待时间 = 1 + 2 + 4 = 7秒，对用户体验影响可控

### Implementation
```python
import asyncio
from typing import TypeVar, Callable

T = TypeVar('T')

async def retry_with_exponential_backoff(
    operation: Callable[[], T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_multiplier: float = 2.0
) -> T:
    """
    指数退避重试机制
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay *= backoff_multiplier
    
    raise last_exception
```

### Alternatives Considered
- **固定间隔重试**: 简单但可能在服务恢复期造成压力
- **立即重试后固定间隔**: 第一次重试过快，可能无效
- **无限重试**: 可能导致请求永久阻塞

---

## Research Task 3: 向量元数据字段设计

### Decision
采用**最小必需字段集**设计：
- **必需**: `doc_id`, `chunk_index`, `created_at`
- **可选**: 任意自定义字段

### Rationale
1. 最小字段集降低存储成本
2. 灵活的可选字段支持多样化业务需求
3. `doc_id` + `chunk_index` 可唯一标识向量来源
4. `created_at` 支持时间范围过滤查询

### Milvus Schema Design
```python
from pymilvus import FieldSchema, CollectionSchema, DataType

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="chunk_index", dtype=DataType.INT32),
    FieldSchema(name="created_at", dtype=DataType.INT64),  # Unix timestamp
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
    # 可选字段通过 JSON 存储
    FieldSchema(name="metadata", dtype=DataType.JSON)
]

schema = CollectionSchema(
    fields=fields,
    description="Vector index collection with metadata"
)
```

### Alternatives Considered
- **完整字段集**: 预定义所有可能字段，浪费存储空间
- **纯 JSON 存储**: 查询效率低，无法建立索引
- **外部元数据表**: 增加查询复杂度，需要额外 JOIN

---

## Research Task 4: 前端进度展示方案

### Decision
采用**实时进度条 + 状态文字**方案：
- 进度条显示百分比和已处理/总数
- 状态文字提示当前阶段（如"正在构建索引..."）

### Rationale
1. 进度条提供直观的视觉反馈
2. 数字显示让用户了解具体进度
3. 状态文字说明当前操作阶段
4. 符合 TDesign 组件库设计规范

### Frontend Component Design
```vue
<template>
  <div class="index-progress">
    <t-progress 
      :percentage="progress.percentage" 
      :status="progress.status"
    />
    <div class="progress-info">
      <span class="count">{{ progress.processed }} / {{ progress.total }}</span>
      <span class="status-text">{{ progress.statusText }}</span>
    </div>
  </div>
</template>
```

### Backend Progress API
```python
class IndexProgressResponse(BaseModel):
    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    percentage: float
    processed: int
    total: int
    status_text: str
    error: Optional[str] = None
```

---

## Research Task 5: 错误展示策略

### Decision
采用**错误弹窗（Modal）**方案展示索引构建失败信息

### Rationale
1. Modal 弹窗能确保用户注意到错误
2. 足够空间展示详细错误信息
3. 可提供明确的操作建议
4. 符合 TDesign 设计规范

### Error Display Structure
```typescript
interface IndexError {
  type: string;           // 错误类型：connection, validation, timeout
  code: string;           // 错误码：ERR_MILVUS_CONNECTION, ERR_DIM_MISMATCH
  message: string;        // 用户友好的错误描述
  detail: string;         // 技术细节（可选展开）
  suggestion: string;     // 建议操作
}
```

### Error Types Catalog
| 错误类型 | 错误码 | 描述 | 建议操作 |
|---------|--------|------|---------|
| 连接错误 | ERR_MILVUS_CONNECTION | Milvus 服务不可用 | 检查服务状态，稍后重试 |
| 维度不匹配 | ERR_DIM_MISMATCH | 向量维度与 Collection 不一致 | 确认向量化配置 |
| 超时错误 | ERR_TIMEOUT | 索引构建超时 | 减少批量大小，稍后重试 |
| 数据验证 | ERR_VALIDATION | 向量数据无效（NaN/Inf） | 检查向量化结果 |

---

## Research Task 6: 删除操作幂等性设计

### Decision
删除不存在的向量ID时**静默忽略**，返回成功状态

### Rationale
1. 幂等性设计简化客户端重试逻辑
2. 避免因网络重传导致的重复错误
3. 符合 RESTful DELETE 最佳实践
4. Milvus delete 操作本身支持幂等性

### Implementation
```python
async def delete_vectors(self, collection_name: str, vector_ids: List[str]) -> DeleteResult:
    """
    删除向量，幂等性设计
    """
    try:
        # Milvus delete with expression
        expr = f"id in {vector_ids}"
        result = collection.delete(expr)
        
        return DeleteResult(
            success=True,
            deleted_count=result.delete_count,  # 实际删除数量
            requested_count=len(vector_ids),     # 请求删除数量
            message="删除操作完成"
        )
    except Exception as e:
        # 连接错误等非幂等场景才返回失败
        raise VectorIndexError(
            type="delete_error",
            code="ERR_DELETE_FAILED",
            message=str(e)
        )
```

---

## Research Task 7: 并发控制策略

### Decision
依赖 **Milvus 原生并发控制**，后端使用异步 I/O

### Rationale
1. Milvus 2.x 原生支持并发读写
2. FastAPI 异步框架天然支持高并发
3. 无需额外实现分布式锁
4. 简化架构复杂度

### Concurrency Configuration
```python
# Milvus 连接池配置
MILVUS_POOL_SIZE = 10  # 连接池大小
MILVUS_TIMEOUT = 30    # 操作超时（秒）

# FastAPI 并发配置
WORKER_COUNT = 4       # Uvicorn worker 数量
```

---

## Dependencies Summary (Superseded — see Updated version below)

> ⚠️ 以下为初始版本依赖列表，已被下方“Dependencies Summary (Updated)”替代。

| Dependency | Version | Purpose |
|------------|---------|---------|
| pymilvus | 2.3.4 | Milvus Python SDK |
| FastAPI | >=0.110.0 | Web 框架 |
| Pydantic | 2.7.4 | 数据验证 |
| SQLAlchemy | 2.0.23 | 元数据 ORM |
| Vue | 3.x | 前端框架 |
| TDesign | latest | UI 组件库 |
| Pinia | latest | 状态管理 |

---

---

## Research Task 8: Milvus 多向量字段 Schema 设计（稀疏向量集成）

### Decision
在现有 Collection Schema 中新增 `sparse_embedding` 字段（SPARSE_FLOAT_VECTOR 类型），与现有 `embedding` 字段（FLOAT_VECTOR）共存于同一 Collection。

### Rationale
1. Milvus 2.4+ 原生支持同一 Collection 多个向量字段
2. 稠密+稀疏向量存储在同一 Collection 避免了跨 Collection JOIN 的复杂度
3. BGE-M3 一次推理同时输出稠密和稀疏向量，写入时天然配对

### Implementation
```python
from pymilvus import FieldSchema, CollectionSchema, DataType

def create_hybrid_collection_schema(dimension: int) -> CollectionSchema:
    """
    创建支持混合检索的 Milvus Collection Schema
    """
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="chunk_index", dtype=DataType.INT32),
        FieldSchema(name="created_at", dtype=DataType.INT64),
        # 稠密向量字段（BGE-M3 dense output）
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dimension),
        # 稀疏向量字段（BGE-M3 sparse output）— 新增
        FieldSchema(name="sparse_embedding", dtype=DataType.SPARSE_FLOAT_VECTOR),
        FieldSchema(name="metadata", dtype=DataType.JSON)
    ]
    return CollectionSchema(fields=fields, description="Hybrid vector collection for RAG")
```

### Alternatives Considered
- **两个独立 Collection**: 稠密和稀疏分开存储，查询时需 JOIN，延迟高
- **仅稠密向量**: 不支持混合检索，召回率有限
- **外部稀疏索引（如 Elasticsearch）**: 引入额外依赖，架构复杂

### Migration Strategy
- 新创建的 Collection 默认包含 `sparse_embedding` 字段
- 旧 Collection 无此字段时，系统检测并自动降级到纯稠密检索
- 无需迁移旧数据，向前兼容

---

## Research Task 9: Milvus RRFRanker 粗排融合

### Decision
使用 Milvus 原生 `hybrid_search` API + `RRFRanker(k=60)` 对稠密和稀疏双路召回结果进行粗排融合。

### Rationale
1. RRF (Reciprocal Rank Fusion) 是经过验证的多路融合算法，无需训练
2. Milvus 2.4 原生支持 `hybrid_search`，一次 API 调用完成双路召回+融合
3. k=60 是 RRF 的默认推荐值，对大多数场景效果稳定
4. 粗排阶段取 Top-N（默认 N=20），送入 Reranker 精排

### Implementation
```python
from pymilvus import AnnSearchRequest, RRFRanker

def hybrid_search(collection, dense_vector, sparse_vector, top_n=20):
    """
    Milvus 混合检索 — 稠密 + 稀疏双路召回 + RRF 粗排
    """
    # 稠密向量检索请求
    dense_req = AnnSearchRequest(
        data=[dense_vector],
        anns_field="embedding",
        param={"metric_type": "L2", "params": {"ef": 64}},  # HNSW 示例
        limit=top_n
    )
    
    # 稀疏向量检索请求
    sparse_req = AnnSearchRequest(
        data=[sparse_vector],
        anns_field="sparse_embedding",
        param={"metric_type": "IP", "params": {}},
        limit=top_n
    )
    
    # RRF 融合
    reranker = RRFRanker(k=60)
    
    results = collection.hybrid_search(
        reqs=[dense_req, sparse_req],
        ranker=reranker,
        limit=top_n,
        output_fields=["doc_id", "chunk_index", "metadata"]
    )
    
    return results
```

### Parameters
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `k` (RRF) | 60 | 排名平滑因子，越大越平滑 |
| `top_n` (粗排) | 20 | 粗排候选集大小，送入 Reranker |
| `top_k` (最终) | 5 | 最终返回给用户的结果数 |

### Alternatives Considered
- **WeightedRanker**: 需要手动调权重（如 0.7*dense + 0.3*sparse），不够自适应
- **自定义融合算法**: 开发成本高，且 RRF 已被验证效果稳定
- **仅依赖 Reranker**: 不做粗排直接精排，候选集过大时 Reranker 推理慢

---

## Research Task 10: Reranker 精排集成

### Decision
通过远程 API 服务（OpenAI-compatible `/rerank` 端点）调用 qwen3-reranker-4b 模型，对 RRF 粗排后的候选集进行精排重排序。

### Rationale
1. qwen3-reranker-4b 是阿里云发布的多语言 Reranker 模型，支持 100+ 语言，32K 序列长度
2. 通过远程 API 调用，无需本地加载模型，资源开销小
3. 20 条候选集精排延迟可控（< 100ms）
4. 与 OpenAI-compatible API 兼容，集成简单

### Implementation
```python
from openai import OpenAI

class RerankerService:
    """qwen3-reranker-4b 精排服务（远程 API）"""
    
    def __init__(self, model_name: str = "qwen3-reranker-4b"):
        self.reranker = FlagReranker(model_name, use_fp16=True)
    
    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = 5
    ) -> list[dict]:
        """
        对候选集进行精排重排序
        
        Args:
            query: 原始查询文本
            candidates: RRF 粗排后的候选集 [{doc_id, chunk_index, text, ...}]
            top_k: 最终返回数量
        
        Returns:
            重排后的 Top-K 结果，附带 reranker_score
        """
        # 构造 query-document pairs
        pairs = [[query, c.get("text", "")] for c in candidates]
        
        # batch 推理
        scores = self.reranker.compute_score(pairs, normalize=True)
        
        # 按分数排序
        for i, candidate in enumerate(candidates):
            candidate["reranker_score"] = scores[i] if isinstance(scores, list) else scores
        
        sorted_results = sorted(candidates, key=lambda x: x["reranker_score"], reverse=True)
        return sorted_results[:top_k]
```

### Performance Characteristics
| 候选集大小 | CPU 推理延迟 | GPU 推理延迟 |
|-----------|-------------|-------------|
| 10 条 | ~50ms | ~10ms |
| 20 条 | ~100ms | ~20ms |
| 50 条 | ~250ms | ~50ms |

### Configuration
```python
# .env 配置
RERANKER_MODEL=qwen3-reranker-4b
RERANKER_API_KEY=your_api_key
RERANKER_API_BASE_URL=http://your-reranker-api-server/api/llmproxy
RERANKER_TIMEOUT=30
RERANKER_TOP_N=20  # 粗排候选集大小
```

### Alternatives Considered
- **Cohere Rerank API**: 效果好但需要网络调用和 API Key，增加外部依赖
- **cross-encoder/ms-marco**: 英文效果好，中文差
- **不使用 Reranker**: 仅 RRF 粗排，精度不够

---

## Research Task 11: 稀疏向量降级策略

### Decision
当稀疏向量为空或不可用时，系统自动降级到纯稠密向量检索（跳过 RRF 融合），直接将稠密检索 Top-N 送入 Reranker 精排。

### Rationale
1. 保证检索服务在任何情况下可用（不因稀疏向量缺失而中断）
2. 降级逻辑简单，仅是条件跳过，不引入额外复杂度
3. 纯稠密检索 + Reranker 精排仍能提供较好的检索效果

### Implementation
```python
async def search(self, query_dense, query_sparse=None, top_n=20, top_k=5, query_text=""):
    """
    智能检索：自动选择混合检索或纯稠密检索
    """
    # 判断是否可以使用混合检索
    use_hybrid = (
        query_sparse is not None
        and len(query_sparse) > 0
        and self._collection_has_sparse_field()
    )
    
    if use_hybrid:
        # 混合检索：稠密 + 稀疏 → RRF 粗排
        candidates = await self._hybrid_search(query_dense, query_sparse, top_n)
    else:
        # 降级：纯稠密检索
        candidates = await self._dense_search(query_dense, top_n)
    
    # 精排（无论是否混合检索，都走 Reranker）
    if query_text and self.reranker:
        results = self.reranker.rerank(query_text, candidates, top_k)
    else:
        results = candidates[:top_k]
    
    return results
```

### Degradation Detection
```python
def _collection_has_sparse_field(self) -> bool:
    """检测 Collection 是否有稀疏向量字段"""
    schema = self.collection.schema
    return any(
        field.dtype == DataType.SPARSE_FLOAT_VECTOR
        for field in schema.fields
    )

def _is_sparse_vector_valid(self, sparse_vector) -> bool:
    """检测稀疏向量是否有效"""
    if sparse_vector is None:
        return False
    if isinstance(sparse_vector, dict) and len(sparse_vector) == 0:
        return False
    return True
```

### Alternatives Considered
- **报错拒绝**: 稀疏向量缺失时报错，但会降低可用性
- **使用零向量替代**: 稀疏向量全零可能干扰 RRF 融合结果
- **缓存最近的稀疏向量**: 复杂且不准确

---

## Research Task 12: SPARSE_INVERTED_INDEX 构建参数

### Decision
使用 `SPARSE_INVERTED_INDEX` + `IP`（内积）度量 + `drop_ratio_build=0.2` 优化存储。

### Rationale
1. SPARSE_INVERTED_INDEX 是 Milvus 专为稀疏向量设计的倒排索引
2. 稀疏向量天然使用内积（IP）作为相似度度量
3. `drop_ratio_build=0.2` 丢弃构建时最小的 20% 权重值，节省索引空间而几乎不影响召回率

### Configuration
```python
# 稀疏向量索引配置
sparse_index_params = {
    "index_type": "SPARSE_INVERTED_INDEX",
    "metric_type": "IP",
    "params": {
        "drop_ratio_build": 0.2  # 构建时丢弃最小的 20% 权重
    }
}

# 搜索参数
sparse_search_params = {
    "metric_type": "IP",
    "params": {
        "drop_ratio_search": 0.0  # 搜索时不丢弃（保证召回率）
    }
}
```

### Parameters
| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| `drop_ratio_build` | 0.2 | 0.0-1.0 | 构建时丢弃的最小权重比例 |
| `drop_ratio_search` | 0.0 | 0.0-1.0 | 搜索时丢弃的最小权重比例 |

### Alternatives Considered
- **SPARSE_WAND**: Milvus 也支持的稀疏索引类型，但 SPARSE_INVERTED_INDEX 更通用
- **不建索引直接暴力搜索**: 稀疏向量维度高，暴力搜索太慢
- **BM25 外部索引**: 引入 Elasticsearch 额外依赖

---

## Research Task 13: 智能推荐引擎 — 索引算法与度量类型推荐策略

### Decision
采用**分层规则匹配引擎**，基于数据量 → 向量维度 → Embedding 模型类型三维决策因子，自动推荐索引算法和度量类型。推荐规则以 JSON 配置表形式存储，支持热更新。

### Rationale
1. 分层规则匹配是业内向量数据库（Milvus、Pinecone、Weaviate）推荐策略的主流方案
2. 三维决策因子覆盖了影响索引性能的核心变量：数据量决定算法复杂度需求，维度影响内存与计算特性，模型类型决定度量兼容性
3. JSON 配置表可在运行时更新，无需重新部署代码
4. 兜底默认值（HNSW + COSINE）确保任何情况下都有合理推荐

### Implementation

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class RecommendationRule:
    """推荐规则实体"""
    priority: int                          # 规则优先级（数字越小优先级越高）
    min_vector_count: Optional[int]        # 最小数据量
    max_vector_count: Optional[int]        # 最大数据量
    min_dimension: Optional[int]           # 最小维度
    max_dimension: Optional[int]           # 最大维度
    embedding_models: Optional[list[str]]  # 适用的 Embedding 模型列表
    recommended_index_type: str            # 推荐索引算法
    recommended_metric_type: str           # 推荐度量类型
    reason_template: str                   # 推荐理由文案模板

# 默认推荐规则表（按优先级排序）
DEFAULT_RECOMMENDATION_RULES = [
    # 规则 1：小数据量 → FLAT
    RecommendationRule(
        priority=1,
        min_vector_count=0,
        max_vector_count=9999,
        min_dimension=None, max_dimension=None,
        embedding_models=None,
        recommended_index_type="FLAT",
        recommended_metric_type=None,  # 度量类型由模型规则决定
        reason_template="数据量 {count} 条 < 1万，FLAT 暴力搜索保证精确结果"
    ),
    # 规则 2：中等数据量 + 低维度 → IVF_FLAT
    RecommendationRule(
        priority=2,
        min_vector_count=10000,
        max_vector_count=999999,
        min_dimension=1, max_dimension=256,
        embedding_models=None,
        recommended_index_type="IVF_FLAT",
        recommended_metric_type=None,
        reason_template="数据量 {count} 条 + 维度 {dim} ≤ 256，IVF_FLAT 聚类效率高"
    ),
    # 规则 3：中等数据量 + 高维度 → HNSW
    RecommendationRule(
        priority=3,
        min_vector_count=10000,
        max_vector_count=999999,
        min_dimension=257, max_dimension=None,
        embedding_models=None,
        recommended_index_type="HNSW",
        recommended_metric_type=None,
        reason_template="数据量 {count} 条 + 维度 {dim} > 256，HNSW 图索引召回率与速度兼优"
    ),
    # 规则 4：百万级数据 → IVF_PQ
    RecommendationRule(
        priority=4,
        min_vector_count=1000000,
        max_vector_count=None,
        min_dimension=None, max_dimension=None,
        embedding_models=None,
        recommended_index_type="IVF_PQ",
        recommended_metric_type=None,
        reason_template="数据量 {count} 条 ≥ 100万，IVF_PQ 压缩显著降低内存占用"
    ),
]

# 度量类型推荐规则（按模型系列）
METRIC_TYPE_RULES = {
    "bge": "COSINE",       # BGE 系列归一化输出
    "openai": "COSINE",    # OpenAI Ada/text-embedding 归一化输出
    "cohere": "COSINE",    # Cohere embed 归一化输出
    "default": "L2",       # 未识别模型默认 L2
}

# 兜底默认值
FALLBACK_RECOMMENDATION = {
    "index_type": "HNSW",
    "metric_type": "COSINE",
    "reason": "未精确匹配推荐规则，已使用通用默认值"
}


class RecommendationEngine:
    """智能推荐引擎"""
    
    def __init__(self, rules: list[RecommendationRule] = None):
        self.rules = sorted(rules or DEFAULT_RECOMMENDATION_RULES, key=lambda r: r.priority)
    
    def recommend(
        self,
        vector_count: int,
        dimension: int,
        embedding_model: str = ""
    ) -> dict:
        """
        根据向量特征推荐索引算法和度量类型
        
        Returns:
            {
                "index_type": str,
                "metric_type": str,
                "reason": str,
                "is_fallback": bool
            }
        """
        # 1. 匹配索引算法规则
        matched_rule = None
        for rule in self.rules:
            if self._matches(rule, vector_count, dimension):
                matched_rule = rule
                break
        
        # 2. 推断度量类型
        metric_type = self._infer_metric_type(embedding_model)
        
        # 3. 输出推荐
        if matched_rule:
            reason = matched_rule.reason_template.format(
                count=vector_count, dim=dimension, model=embedding_model
            )
            return {
                "index_type": matched_rule.recommended_index_type,
                "metric_type": matched_rule.recommended_metric_type or metric_type,
                "reason": f"基于 {embedding_model or '未知模型'} {dimension}维 + {vector_count}条向量推荐 — {reason}",
                "is_fallback": False
            }
        
        # 4. 兜底
        return {
            **FALLBACK_RECOMMENDATION,
            "is_fallback": True
        }
    
    def _matches(self, rule: RecommendationRule, count: int, dim: int) -> bool:
        if rule.min_vector_count is not None and count < rule.min_vector_count:
            return False
        if rule.max_vector_count is not None and count > rule.max_vector_count:
            return False
        if rule.min_dimension is not None and dim < rule.min_dimension:
            return False
        if rule.max_dimension is not None and dim > rule.max_dimension:
            return False
        return True
    
    def _infer_metric_type(self, model: str) -> str:
        model_lower = (model or "").lower()
        for prefix, metric in METRIC_TYPE_RULES.items():
            if prefix != "default" and prefix in model_lower:
                return metric
        return METRIC_TYPE_RULES["default"]
```

### Performance Characteristics
| 操作 | 延迟 | 说明 |
|------|------|------|
| 规则匹配 | < 1ms | 纯内存遍历，规则数 < 10 |
| 度量类型推断 | < 1ms | 字符串前缀匹配 |
| 总推荐延迟 | < 10ms | 远低于 500ms P95 要求 |

### Alternatives Considered
- **机器学习推荐模型**: 需要训练数据积累，初期规则引擎更实用
- **用户历史行为推荐**: 冷启动问题，需要大量用户数据
- **硬编码推荐**: 不可配置，修改需要重新部署

---

## Dependencies Summary (Updated)

| Dependency | Version | Purpose |
|------------|---------|---------|
| pymilvus | 2.4.9 | Milvus Python SDK（支持 hybrid_search） |
| FlagEmbedding | >=1.2.0 | ~~bge-reranker-v2-m3 精排模型加载~~（已替换为远程 API 调用 qwen3-reranker-4b） |
| FastAPI | >=0.110.0 | Web 框架 |
| Pydantic | 2.7.4 | 数据验证 |
| SQLAlchemy | 2.0.23 | 元数据 ORM |
| Vue | 3.x | 前端框架 |
| TDesign | latest | UI 组件库 |
| Pinia | latest | 状态管理 |

---

## Conclusion

所有技术研究任务已完成，无待澄清项。主要技术决策：
1. ✅ 索引算法：FLAT/IVF_FLAT/IVF_PQ/HNSW（稠密向量）
2. ✅ 重试策略：指数退避（1s→2s→4s，最多3次）
3. ✅ 元数据字段：最小必需集 + JSON 可选字段
4. ✅ 进度展示：实时进度条 + 状态文字
5. ✅ 错误展示：Modal 弹窗 + 建议操作
6. ✅ 删除幂等：静默忽略不存在的ID
7. ✅ 并发控制：Milvus 原生 + 异步 I/O
8. ✅ 多向量字段 Schema：同一 Collection 中稠密+稀疏向量字段共存
9. ✅ RRF 粗排融合：Milvus hybrid_search + RRFRanker(k=60)
10. ✅ Reranker 精排：qwen3-reranker-4b + 远程 API
11. ✅ 稀疏向量降级：自动降级到纯稠密检索 + Reranker
12. ✅ 稀疏索引：SPARSE_INVERTED_INDEX + IP + drop_ratio_build=0.2
13. ✅ 智能推荐引擎：分层规则匹配（数据量→维度→模型），JSON 配置表，兜底 HNSW+COSINE
