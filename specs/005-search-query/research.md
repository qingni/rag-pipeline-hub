# Research: 搜索查询功能

**Feature**: 005-search-query  
**Date**: 2025-12-25

## 1. 查询向量化方案

### Decision
复用现有的 Embedding 服务 (003-vector-embedding) 将查询文本转换为向量

### Rationale
- 已有成熟的 `embedding_service.py` 支持多提供商
- 查询向量与文档向量必须使用相同的 Embedding 模型才能保证相似度计算的准确性
- 避免重复实现，降低维护成本

### Alternatives Considered
| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| 复用 Embedding 服务 | 一致性好，维护成本低 | 依赖外部服务 | ✅ 采用 |
| 独立实现查询向量化 | 解耦 | 重复代码，模型不一致风险 | ❌ 拒绝 |
| 缓存查询向量 | 重复查询快 | 增加复杂度，收益有限 | ⏳ 后期优化 |

---

## 2. 向量检索集成方案

### Decision
通过 `vector_index_service.py` 调用已注册的 Provider 执行相似度检索

### Rationale
- 004-vector-index 已实现完整的 Provider Pattern (Milvus/FAISS)
- 搜索查询是向量索引的消费者，不应重复实现检索逻辑
- 支持单索引和多索引联合搜索

### Implementation Approach
```python
# 调用链路
SearchService.search(query_text, index_ids, config)
  → EmbeddingService.embed(query_text)  # 获取查询向量
  → VectorIndexService.search(query_vector, index_ids, top_k, threshold)  # 检索
  → 合并结果，按相似度排序
```

---

## 3. 搜索历史存储方案

### Decision
使用 SQLite/PostgreSQL 存储搜索历史，与现有数据库保持一致

### Rationale
- 搜索历史需要持久化存储
- 复用现有数据库连接和 ORM 模式
- 支持按时间、查询文本等条件检索

### Data Model
```python
class SearchHistory(Base):
    id: str  # UUID
    query_text: str
    index_ids: List[str]  # JSON
    config: Dict  # JSON (top_k, threshold, metric_type)
    result_count: int
    execution_time_ms: int
    created_at: datetime
```

---

## 4. 前端组件设计方案

### Decision
采用与现有模块一致的布局模式，复用 TDesign 组件

### Rationale
- 遵循 Constitution IV. 用户体验优先
- 与文档处理、向量化、向量索引模块保持一致的交互体验
- 降低用户学习成本

### Layout Design
```text
┌─────────────────────────────────────────────────────────────┐
│  搜索查询                                                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │  🔍 [搜索输入框................................] [搜索] │    │
│  └─────────────────────────────────────────────────────┘    │
├──────────────────────┬──────────────────────────────────────┤
│  配置面板            │  搜索结果 | 历史记录                  │
│  ┌────────────────┐  │  ┌────────────────────────────────┐  │
│  │ 目标索引       │  │  │  结果卡片 1                    │  │
│  │ [下拉选择]     │  │  │  相似度: 95%  来源: doc1.pdf  │  │
│  ├────────────────┤  │  │  文本摘要...                   │  │
│  │ 返回数量 (TopK)│  │  └────────────────────────────────┘  │
│  │ [10]           │  │  ┌────────────────────────────────┐  │
│  ├────────────────┤  │  │  结果卡片 2                    │  │
│  │ 相似度阈值     │  │  │  相似度: 87%  来源: doc2.pdf  │  │
│  │ [0.5]          │  │  │  文本摘要...                   │  │
│  ├────────────────┤  │  └────────────────────────────────┘  │
│  │ 相似度方法     │  │                                      │
│  │ [余弦相似度]   │  │                                      │
│  └────────────────┘  │                                      │
└──────────────────────┴──────────────────────────────────────┘
```

---

## 5. 错误处理与降级策略

### Decision
分层错误处理，Embedding 服务不可用时显示明确提示

### Error Handling Strategy
| 错误类型 | 处理方式 | 用户提示 |
|----------|----------|----------|
| 查询文本为空 | 前端校验 | "请输入查询内容" |
| Embedding 服务超时 | 重试 1 次后失败 | "向量化服务暂时不可用，请稍后重试" |
| 向量索引不存在 | 返回错误 | "所选索引不存在或已被删除" |
| 无匹配结果 | 返回空列表 | "未找到相关内容，请尝试其他关键词" |
| 搜索超时 | 30秒超时 | "搜索请求超时，请缩小搜索范围" |

---

## 6. 性能优化策略

### Decision
首期采用同步调用，后期可优化为异步批处理

### Performance Targets
- 端到端响应时间 < 3秒 (P95)
- 支持 20 并发搜索请求
- 吞吐量 10 QPS

### Optimization Roadmap (Future)
1. 查询向量缓存（相同查询复用向量）
2. 结果缓存（热门查询结果缓存）
3. 异步搜索（大规模多索引场景）

---

## 7. API 设计方案

### Decision
RESTful API，遵循现有 API 规范

### Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/search` | 执行搜索查询 |
| GET | `/api/v1/search/indexes` | 获取可用索引列表 |
| GET | `/api/v1/search/history` | 获取搜索历史 |
| DELETE | `/api/v1/search/history/{id}` | 删除单条历史 |
| DELETE | `/api/v1/search/history` | 清空所有历史 |

---

## Summary

所有技术决策已明确，无 NEEDS CLARIFICATION 项：

| 领域 | 决策 |
|------|------|
| 查询向量化 | 复用 Embedding 服务 |
| 向量检索 | 调用 VectorIndexService |
| 历史存储 | SQLite/PostgreSQL |
| 前端布局 | 左右分栏 + Tab 切换 |
| 错误处理 | 分层处理 + 友好提示 |
| 性能目标 | <3s P95, 20 并发, 10 QPS |
