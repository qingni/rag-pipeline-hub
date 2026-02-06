# Technical Research: 向量索引模块（优化版）

**Branch**: `004-vector-index-opt`
**Date**: 2026-02-06
**Status**: Complete

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

## Dependencies Summary

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

## Conclusion

所有技术研究任务已完成，无待澄清项。主要技术决策：
1. ✅ 索引算法：FLAT/IVF_FLAT/IVF_PQ/HNSW
2. ✅ 重试策略：指数退避（1s→2s→4s，最多3次）
3. ✅ 元数据字段：最小必需集 + JSON 可选字段
4. ✅ 进度展示：实时进度条 + 状态文字
5. ✅ 错误展示：Modal 弹窗 + 建议操作
6. ✅ 删除幂等：静默忽略不存在的ID
7. ✅ 并发控制：Milvus 原生 + 异步 I/O
