# Research: 文档向量化功能优化

**Branch**: `003-vector-embedding-opt` | **Date**: 2026-02-02

## 1. 多模态向量化策略 (Multimodal Embedding)

### Decision
采用分层策略：图片优先使用 base64 直接向量化（多模态模型），失败时降级为文本描述；表格使用 Markdown 格式文本向量化。

### Rationale
- 多模态模型（如 qwen3-vl-embedding-8b）能直接理解图片内容，生成更精确的向量
- 图片描述文本作为 fallback 确保所有内容都能被向量化
- 表格的 Markdown 格式保留了结构信息，比纯文本更有效

### Alternatives Considered
| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| 仅文本描述向量化 | 实现简单，兼容性好 | 丢失视觉信息 | ❌ 拒绝 |
| 仅多模态向量化 | 效果最佳 | 模型不可用时完全失败 | ❌ 拒绝 |
| 分层策略（多模态优先） | 效果好+高可用 | 实现稍复杂 | ✅ 采用 |
| OCR + 文本向量化 | 通用性好 | 需要额外 OCR 步骤，信息损失 | ❌ 备选 |

### Implementation Approach
```python
class MultimodalEmbedder:
    def embed_chunk(self, chunk: Chunk) -> Vector:
        if chunk.chunk_type == "image":
            try:
                # 优先使用图片 base64 直接向量化
                return self._embed_image(chunk.metadata.image_base64)
            except Exception as e:
                # 降级为文本描述
                logger.warning(f"Image embedding failed, fallback to text: {e}")
                return self._embed_text(chunk.metadata.caption or chunk.content)
        elif chunk.chunk_type == "table":
            # 表格使用 Markdown 格式
            return self._embed_text(chunk.metadata.table_markdown or chunk.content)
        else:
            return self._embed_text(chunk.content)
```

---

## 2. 批量处理与并发控制 (Batch Processing)

### Decision
实现基于 asyncio 的并发批量处理器，支持可配置的并发数、批量大小和自适应限流。

### Rationale
- asyncio 提供高效的异步并发能力
- 可配置参数适应不同的 API 限制和网络条件
- 自适应限流防止 API 过载导致的请求失败

### Implementation Approach
```python
class BatchEmbedder:
    def __init__(self, max_concurrency: int = 5, batch_size: int = 50):
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.batch_size = batch_size
        self.current_concurrency = max_concurrency
    
    async def embed_chunks(self, chunks: List[Chunk]) -> List[EmbeddingResult]:
        batches = self._create_batches(chunks, self.batch_size)
        results = []
        
        for batch in batches:
            async with self.semaphore:
                try:
                    batch_result = await self._process_batch(batch)
                    results.extend(batch_result)
                except RateLimitError:
                    # 自动降低并发数
                    self._reduce_concurrency()
                    await asyncio.sleep(self._get_backoff_delay())
                    batch_result = await self._process_batch(batch)
                    results.extend(batch_result)
        
        return results
```

---

## 3. 指数退避重试机制 (Exponential Backoff Retry)

### Decision
实现带抖动的指数退避重试，支持可配置的最大重试次数、初始延迟和最大延迟。

### Rationale
- 指数退避避免在服务恢复时瞬间大量请求
- 抖动（jitter）防止多个客户端同时重试
- 可配置参数适应不同场景

### Implementation Approach
```python
class RetryHandler:
    def __init__(
        self, 
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 32.0,
        jitter: float = 0.25
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.jitter = jitter
    
    async def with_retry(self, func, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except RetryableError as e:
                if attempt == self.max_retries - 1:
                    raise
                delay = self._calculate_delay(attempt)
                await asyncio.sleep(delay)
    
    def _calculate_delay(self, attempt: int) -> float:
        delay = min(self.initial_delay * (2 ** attempt), self.max_delay)
        jitter_range = delay * self.jitter
        return delay + random.uniform(-jitter_range, jitter_range)
```

---

## 4. 增量向量化机制 (Incremental Embedding)

### Decision
基于内容哈希（SHA-256）检测分块变更，仅对新增/修改的分块进行向量化。

### Rationale
- SHA-256 提供高强度的内容指纹，冲突概率极低
- 避免重复计算节省时间和 API 成本
- 支持强制全量模式满足特殊需求

### Implementation Approach
```python
class IncrementalEmbeddingService:
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
    
    async def embed_with_incremental(
        self, 
        chunks: List[Chunk], 
        model: str,
        force_recompute: bool = False
    ) -> IncrementalResult:
        result = IncrementalResult()
        chunks_to_process = []
        
        for chunk in chunks:
            content_hash = hashlib.sha256(chunk.content.encode()).hexdigest()
            
            if force_recompute:
                chunks_to_process.append(chunk)
            else:
                cached_vector = await self.cache_service.get(content_hash, model)
                if cached_vector and cached_vector.dimension == self._get_dimension(model):
                    result.add_cached(chunk.id, cached_vector)
                else:
                    chunks_to_process.append(chunk)
        
        # 仅处理需要计算的分块
        new_vectors = await self._embed_chunks(chunks_to_process, model)
        result.add_computed(new_vectors)
        
        return result
```

---

## 5. 向量缓存机制 (Vector Caching)

### Decision
实现基于内容哈希的 LRU 缓存，支持本地内存和 Redis 两种存储后端。

### Rationale
- LRU 策略在固定容量下保留最常用的缓存
- 双后端支持满足不同部署场景（单机/分布式）
- 缓存键包含模型名确保不同模型的向量不混淆

### Cache Key Design
```
cache_key = SHA256(content)[:16] + ":" + model_name
```

### Implementation Approach
```python
class VectorCacheService:
    def __init__(
        self, 
        backend: str = "memory",  # memory | redis
        max_size: int = 10000,
        ttl_days: int = 7
    ):
        if backend == "memory":
            self.cache = LRUCache(maxsize=max_size)
        else:
            self.cache = RedisCache(ttl=ttl_days * 86400)
    
    async def get(self, content_hash: str, model: str) -> Optional[CachedVector]:
        key = self._make_key(content_hash, model)
        cached = await self.cache.get(key)
        if cached:
            await self.cache.touch(key)  # 更新 LRU 访问时间
        return cached
    
    async def set(
        self, 
        content_hash: str, 
        model: str, 
        vector: List[float]
    ) -> None:
        key = self._make_key(content_hash, model)
        await self.cache.set(key, CachedVector(
            vector=vector,
            dimension=len(vector),
            created_at=datetime.utcnow()
        ))
    
    def _make_key(self, content_hash: str, model: str) -> str:
        return f"{content_hash[:16]}:{model}"
```

---

## 6. 进度推送机制 (Progress Streaming)

### Decision
采用 Server-Sent Events (SSE) 进行进度推送，前端使用 EventSource API 接收。

### Rationale
- SSE 比 WebSocket 更轻量，单向推送场景更合适
- 原生 HTTP 协议，防火墙和代理兼容性好
- 自动重连支持，断线恢复更简单

### Alternatives Considered
| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| WebSocket | 双向通信 | 实现复杂，需要心跳 | ❌ 过度设计 |
| SSE | 轻量，自动重连 | 仅支持单向 | ✅ 采用 |
| 轮询 | 最简单 | 延迟高，资源浪费 | ❌ 拒绝 |

### Implementation Approach
```python
# Backend
@router.get("/embedding/progress/{task_id}")
async def stream_progress(task_id: str):
    async def event_generator():
        while True:
            progress = await progress_service.get_progress(task_id)
            yield {
                "event": "progress",
                "data": progress.json()
            }
            if progress.status in ["completed", "failed", "cancelled"]:
                break
            await asyncio.sleep(0.5)
    
    return EventSourceResponse(event_generator())

# Frontend
const eventSource = new EventSource(`/api/embedding/progress/${taskId}`);
eventSource.onmessage = (event) => {
    const progress = JSON.parse(event.data);
    updateProgressBar(progress);
};
```

---

## 7. 模型对比功能 (Model Comparison)

### Decision
存储多次向量化结果，提供对比 API 和前端对比视图。

### Rationale
- 用户需要了解不同模型的性能差异
- 保留历史结果支持回溯和分析
- 设置"活跃"结果便于后续检索使用

### Comparison Metrics
| 指标 | 说明 |
|------|------|
| 处理时间 | 总耗时、平均每块耗时 |
| 向量维度 | 各模型输出维度 |
| 成功率 | 成功/失败/跳过分块占比 |
| 缓存命中率 | 复用缓存的比例 |
| 多模态处理 | 图片向量化成功率、降级率 |

### Implementation Approach
```python
class EmbeddingComparisonService:
    async def compare_results(
        self, 
        result_ids: List[str]
    ) -> ComparisonResult:
        results = await self._fetch_results(result_ids)
        
        return ComparisonResult(
            results=[
                ResultSummary(
                    result_id=r.result_id,
                    model=r.model,
                    dimension=r.dimension,
                    processing_time_ms=r.statistics.processing_time_ms,
                    success_rate=r.statistics.successful_count / r.statistics.total_chunks,
                    cache_hit_rate=r.statistics.cache_hit_rate,
                    image_success_rate=self._calc_image_success_rate(r)
                )
                for r in results
            ]
        )
```

---

## 8. 前端进度可视化 UI

### Decision
使用 TDesign Progress 组件实现进度条，配合统计卡片展示详细信息。

### UI Layout
```
┌─────────────────────────────────────────────────────────────┐
│ 向量化进度                                                    │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ████████████████████████░░░░░░░░░░  60%                 │ │
│ │ 已完成 300/500 · 失败 2 · 缓存命中 150                    │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐      │
│ │ 处理速度       │ │ 预估剩余时间   │ │ 缓存命中率     │      │
│ │ 25 块/秒      │ │ 约 8 秒       │ │ 30%          │      │
│ └───────────────┘ └───────────────┘ └───────────────┘      │
│                                                              │
│                                    [取消] [在后台运行]        │
└─────────────────────────────────────────────────────────────┘
```

### Component Structure
```vue
<template>
  <t-card title="向量化进度" :bordered="true">
    <t-progress 
      :percentage="progress.percentage" 
      :status="progressStatus"
    />
    <div class="progress-details">
      <span>已完成 {{ progress.completed }}/{{ progress.total }}</span>
      <span v-if="progress.failed > 0" class="text-error">
        · 失败 {{ progress.failed }}
      </span>
      <span v-if="progress.cached > 0" class="text-success">
        · 缓存命中 {{ progress.cached }}
      </span>
    </div>
    
    <t-row :gutter="16" class="stats-row">
      <t-col :span="4">
        <StatCard label="处理速度" :value="`${progress.speed} 块/秒`" />
      </t-col>
      <t-col :span="4">
        <StatCard label="预估剩余时间" :value="formatETA(progress.eta_seconds)" />
      </t-col>
      <t-col :span="4">
        <StatCard label="缓存命中率" :value="`${progress.cacheHitRate}%`" />
      </t-col>
    </t-row>
    
    <div class="action-buttons">
      <t-button theme="default" @click="cancel">取消</t-button>
      <t-button theme="primary" @click="runInBackground">在后台运行</t-button>
    </div>
  </t-card>
</template>
```

---

## 9. 自适应限流机制 (Adaptive Rate Limiting)

### Decision
实现自适应限流器，根据 API 响应自动调整请求速率。

### Rationale
- 不同 API 提供商限流策略不同
- 动态调整比固定配置更灵活
- 快速恢复机制提升整体吞吐量

### Implementation Approach
```python
class AdaptiveRateLimiter:
    def __init__(self, initial_rate: int = 5):
        self.current_rate = initial_rate
        self.min_rate = 1
        self.max_rate = 20
        self.success_streak = 0
        self.failure_streak = 0
    
    def on_success(self):
        self.success_streak += 1
        self.failure_streak = 0
        # 连续成功 10 次后尝试提升速率
        if self.success_streak >= 10 and self.current_rate < self.max_rate:
            self.current_rate = min(self.current_rate + 1, self.max_rate)
            self.success_streak = 0
    
    def on_rate_limit(self):
        self.failure_streak += 1
        self.success_streak = 0
        # 遇到限流立即降低速率
        self.current_rate = max(self.current_rate // 2, self.min_rate)
```
