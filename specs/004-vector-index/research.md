# Research Document: 向量索引模块

**Feature**: 004-vector-index  
**Date**: 2025-12-22  
**Status**: Complete

## Executive Summary

本文档记录了向量索引模块的技术调研结果。基于现有系统架构（FastAPI + Vue3 + TDesign）和宪章要求，我们选择FAISS作为核心向量索引引擎，配合多提供商支持架构，实现高性能、可扩展的向量检索功能。

## 技术决策

### 1. 向量索引引擎选择

**Decision**: 使用 **Milvus** 作为主要向量数据库，FAISS 作为轻量级备选方案

**Rationale**:
- **Milvus优势**（优先选择）:
  - **生产级向量数据库**: 专为大规模向量检索设计
  - **分布式架构**: 原生支持水平扩展，可处理亿级向量
  - **完善的数据管理**: 内置元数据管理、Collection管理、分区支持
  - **高并发性能**: 原生支持并发读写，无需额外锁机制
  - **持久化可靠**: 自动数据持久化，支持快照和备份
  - **丰富的索引类型**: IVF_FLAT, IVF_PQ, HNSW, ANNOY等
  - **企业级特性**: 监控、日志、安全认证、资源隔离
  - **与宪章对齐**: 符合"多提供商支持"和"可扩展性"原则
  - 已在requirements.txt中包含pymilvus 2.3.4
  
- **FAISS作为备选**:
  - **轻量级场景**: 开发环境、小规模测试、资源受限部署
  - **快速原型**: 无需独立服务，降低部署复杂度
  - **离线处理**: 适合批量索引构建和离线查询
  - Meta开源，性能优秀（10K向量查询 < 10ms）

**Alternatives Considered**:
- **FAISS (Facebook AI)**:
  - 优点：轻量级，易于集成，性能优秀
  - 缺点：缺少分布式能力，元数据管理需自建，并发控制需手动实现
  - **采用场景**：作为备选方案，用于开发环境和小规模部署
  
- **Annoy (Spotify)**:
  - 优点：轻量级，易于集成
  - 缺点：索引构建后不可修改，不支持删除和更新操作
  - 拒绝原因：不满足FR-007增量更新需求
  
- **Hnswlib**:
  - 优点：高性能HNSW实现
  - 缺点：功能相对单一，缺少高级索引管理
  - 拒绝原因：不如Milvus功能完善
  
- **Pinecone**:
  - 优点：云端托管，易用
  - 缺点：商业服务，成本高，依赖外部服务
  - 拒绝原因：与本地部署需求不符，供应商锁定风险

### 2. 索引算法选择

**Decision**: 采用Milvus多索引策略 + FAISS分层索引作为备选

**Milvus索引策略**（主要方案）:
- **FLAT索引**（精确搜索）:
  - 适用场景：< 10K向量
  - 优点：100%精确，无需训练
  - Milvus参数：`index_type="FLAT"`
  
- **IVF_FLAT索引**（平衡方案）:
  - 适用场景：10K - 100万向量
  - 优点：召回率高（>95%），查询速度快
  - Milvus参数：`nlist=1024`（聚类中心数）
  
- **IVF_PQ索引**（压缩方案）:
  - 适用场景：> 100万向量
  - 优点：内存占用低，支持超大规模
  - Milvus参数：`nlist=1024, m=8`（PQ压缩参数）
  
- **HNSW索引**（高性能方案）:
  - 适用场景：对查询延迟要求极高（<10ms）
  - 优点：查询速度最快，召回率高
  - Milvus参数：`M=16, efConstruction=200`

**FAISS索引策略**（备选方案）:
- 小规模（< 10K）：IndexFlatIP（内积，用于余弦相似度）
- 中规模（10K-100K）：IndexIVFPQ（nlist=100, M=8）
- 大规模（> 100K）：IndexIVFPQ（nlist=1000, M=16）

### 3. 相似度计算方法

**Decision**: 主要使用余弦相似度（Cosine Similarity），同时支持欧氏距离和点积

**Rationale**:
- **余弦相似度**（默认）:
  - 最适合文本向量比较
  - 归一化后等价于内积
  - 符合Embedding模型的输出特性
  
- **实现方式**:
  - 内积索引：IndexFlatIP, IndexIVFPQ
  - 向量预归一化：L2 normalization
  - 欧氏距离：IndexFlatL2（可选）

**Technical Detail**:
```python
# 余弦相似度 = 归一化向量的内积
faiss.normalize_L2(vectors)  # 归一化
index = faiss.IndexFlatIP(dimension)  # 内积索引
# scores = dot_product(query_normalized, vectors_normalized)
```

### 4. 元数据存储方案

**Decision**: Milvus原生元数据管理 + PostgreSQL扩展存储

**Rationale**:
- **Milvus原生元数据**（主要方案）:
  - Milvus 2.3+支持Scalar字段存储元数据
  - 每个向量可关联多个标量字段（document_id, text, namespace等）
  - 支持元数据过滤查询（Filter Expression）
  - 数据与向量一体化存储，无需额外关联
  
- **PostgreSQL扩展存储**:
  - 存储复杂元数据（> 1KB的文本内容）
  - 管理索引级别配置和统计信息
  - 记录操作日志和审计信息
  - 提供关系查询能力

- **FAISS备选方案**:
  - FAISS仅存储向量，所有元数据存储在PostgreSQL
  - 通过vector_id关联Milvus数据库记录
  - 与现有系统架构（SQLAlchemy）集成

### 5. 索引持久化策略

**Decision**: Milvus自动持久化 + FAISS手动持久化

**Milvus持久化**（主要方案）:
- **自动持久化**: Milvus自动将数据写入MinIO/S3或本地磁盘
- **Flush操作**: 调用`collection.flush()`强制持久化
- **快照备份**: 支持collection级别的快照和恢复
- **分布式存储**: 数据自动分片存储，高可用

**FAISS持久化**（备选方案）:
- **手动保存**: `faiss.write_index()` 保存为 `.index` 文件
- **快速加载**: `faiss.read_index()`
- **文件大小**: 约为原始数据的100-120%
  
**自动持久化触发**（两种方案通用）:
- 每N次更新后自动保存（N=1000）
- 定时保存（每5分钟）
- 优雅关闭时保存

### 6. 并发控制方案

**Decision**: Milvus原生并发控制 + FAISS读写锁

**Milvus并发控制**（主要方案）:
- **原生并发**: Milvus内部实现MVCC多版本并发控制
- **无需额外锁**: 应用层无需管理锁机制
- **并发性能**: 支持数百并发查询
- **一致性保证**: ACID事务级别的数据一致性

**FAISS并发控制**（备选方案）:
- **读写锁**: Python `threading.RLock`
- **多读单写**: 读操作不阻塞其他读
- **写时复制**: 大批量更新时创建新索引，原子性替换指针

### 7. 多索引管理架构

**Decision**: 索引注册表（Registry Pattern）+ 命名空间隔离

**Rationale**:
- **Registry Pattern**:
  - 全局索引管理器
  - 支持索引的CRUD操作
  - 延迟加载（按需加载索引）
  
- **命名空间设计**:
  - 每个索引独立的命名空间
  - 支持跨索引查询（联合搜索）
  - 索引间完全隔离

**Architecture**:
```python
class VectorIndexRegistry:
    _instances: Dict[str, VectorIndex] = {}
    
    @classmethod
    def get_index(cls, name: str) -> VectorIndex:
        if name not in cls._instances:
            cls._instances[name] = VectorIndex.load(name)
        return cls._instances[name]
    
    @classmethod
    def create_index(cls, name: str, config: Dict) -> VectorIndex:
        index = VectorIndex(name, config)
        cls._instances[name] = index
        return index
```

## 性能优化策略

### 1. 批量处理优化

**Strategy**: 向量批量插入和批量查询

**Details**:
- 索引构建：批量添加（batch_size=1000）
- 批量查询：一次提交多个query向量
- 减少索引锁定次数
- 预期性能提升：3-5倍

### 2. 内存优化

**Strategy**: PQ量化 + mmap文件映射

**Details**:
- Product Quantization（PQ）：压缩向量表示
- 内存映射：大索引不完全加载到内存
- 预期内存占用：< 120%原始数据

### 3. 查询优化

**Strategy**: nprobe参数调优 + 预过滤

**Details**:
- IVF索引nprobe参数：控制精度/速度平衡
- 元数据预过滤：先筛选候选集
- 查询缓存：热点查询结果缓存

## 集成策略

### 1. 与现有系统集成

**Integration Points**:
- **Embedding Service**: 接收embedding_service生成的向量
- **Document Service**: 关联文档元数据
- **Storage Layer**: 复用现有database.py和file_storage.py

**Data Flow**:
```
Embedding Service → Vector Index Service → Search API
       ↓                      ↓
   JSON结果              持久化索引
```

**Docker 环境配置**（macOS 特别要求）:
- **macOS 用户**: 必须使用 Colima 启动 Docker 运行时
  ```bash
  brew install colima
  colima start --cpu 4 --memory 8 --disk 50
  ```
- **Linux 用户**: 直接使用系统 Docker
- **Windows 用户**: 使用 Docker Desktop 或 WSL2

### 2. API设计原则

**RESTful Endpoints**:
- POST `/api/v1/indexes` - 创建索引
- POST `/api/v1/indexes/{name}/vectors` - 添加向量
- POST `/api/v1/indexes/{name}/search` - 相似度搜索
- DELETE `/api/v1/indexes/{name}/vectors` - 删除向量
- GET `/api/v1/indexes/{name}/stats` - 索引统计

**Response Format**（符合宪章）:
```json
{
  "status": "success",
  "data": {
    "results": [...],
    "metadata": {...}
  },
  "timestamp": "2025-12-22T10:00:00Z"
}
```

## 风险评估与缓解

### Risk 1: FAISS版本兼容性

**Mitigation**: 
- 固定FAISS版本（faiss-cpu==1.7.4）
- 索引文件格式版本控制
- 提供迁移工具

### Risk 2: 大规模数据性能下降

**Mitigation**:
- 分片策略（未来Phase）
- 定期索引重建优化
- 监控性能指标

### Risk 3: 并发写入冲突

**Mitigation**:
- 写操作队列化
- 批量更新合并
- 事务性更新机制

## 技术栈总结

| 组件 | 技术选型 | 版本 | 说明 |
|------|---------|------|------|
| **向量数据库（主）** | **Milvus** | **2.3.4** | **优先选择** |
| 向量索引库（备选） | FAISS | 1.7.4 | 轻量级方案 |
| 元数据存储 | PostgreSQL | 14+ | 扩展存储 |
| 并发控制 | Milvus原生 / threading.RLock | - | 主备方案 |
| 序列化 | JSON + Protobuf | - | Milvus使用Protobuf |
| Web框架 | FastAPI | 0.104.1 | 后端API |
| ORM | SQLAlchemy | 2.0.23 | 数据库操作 |

## 前端设计研究 (2024-12-24 补充)

### 1. 布局方案

**Decision**: 采用左右分栏布局，参考 `DocumentEmbedding.vue`

**Rationale**:
- 与现有向量化模块保持一致的用户体验
- 左侧配置区固定宽度（380px），右侧内容区自适应
- 右侧采用双Tab设计（索引结果 + 历史记录）

**Layout Structure**:
```vue
<t-layout>
  <t-aside width="380px">
    <!-- 索引配置面板 -->
    <VectorTaskSelector />      <!-- 选择向量化任务 -->
    <DatabaseSelector />        <!-- 选择向量数据库 -->
    <AlgorithmSelector />       <!-- 选择索引算法 -->
    <t-button>开始索引</t-button>
  </t-aside>
  
  <t-content>
    <t-tabs>
      <t-tab-panel label="索引结果">
        <IndexResultCard />
      </t-tab-panel>
      <t-tab-panel label="历史记录">
        <IndexHistoryList />
      </t-tab-panel>
    </t-tabs>
  </t-content>
</t-layout>
```

### 2. 组件设计

#### VectorTaskSelector (向量化任务选择器)

**功能**:
- 下拉选择已完成的向量化任务
- 显示任务名称、文档名称、创建时间
- 选择后自动获取向量数据元信息（维度、数量）

**API 依赖**:
```
GET /api/v1/vector-index/embedding-tasks?status=SUCCESS
```

**数据结构**:
```typescript
interface VectorTask {
  result_id: string;
  document_id: string;
  document_name: string;
  model: string;
  vector_dimension: number;
  successful_count: number;
  created_at: string;
}
```

#### DatabaseSelector (数据库选择器)

**功能**:
- 单选 Milvus 或 FAISS
- 显示各数据库的特点说明
- 根据选择动态调整可用算法

**选项**:
| 数据库 | 描述 | 推荐场景 |
|--------|------|----------|
| Milvus | 生产级向量数据库，支持分布式 | 生产环境、大规模数据 |
| FAISS | 轻量级本地索引库 | 开发环境、小规模测试 |

#### AlgorithmSelector (算法选择器)

**功能**:
- 根据选择的数据库显示可用算法
- 显示算法特点和适用场景
- 提供参数配置（高级选项）

**算法矩阵**:
| 算法 | Milvus | FAISS | 特点 |
|------|--------|-------|------|
| FLAT | ✅ | ✅ | 精确搜索，适合小规模 |
| IVF_FLAT | ✅ | ✅ | 平衡方案，中等规模 |
| IVF_PQ | ✅ | ✅ | 压缩存储，大规模 |
| HNSW | ✅ | ❌ | 高性能，低延迟 |

#### IndexResultCard (索引结果卡片)

**功能**:
- 显示当前索引的详细信息
- 索引状态（构建中/就绪/错误）
- 统计信息（向量数量、索引大小、查询延迟）
- 操作按钮（持久化、导出、删除）

#### IndexHistoryList (历史记录列表)

**功能**:
- 分页展示索引操作历史
- 支持查看详情
- 支持删除记录
- 时间排序（最新在前）

**操作**:
- 查看详情：展开显示完整配置和统计
- 删除记录：确认后删除索引及数据

### 3. 状态管理 (Pinia Store)

**扩展 vectorIndexStore.js**:

```javascript
export const useVectorIndexStore = defineStore('vectorIndex', {
  state: () => ({
    // 向量化任务列表
    vectorTasks: [],
    selectedTaskId: null,
    
    // 配置选项
    selectedDatabase: 'milvus',  // milvus | faiss
    selectedAlgorithm: 'HNSW',
    algorithmParams: {},
    
    // 索引结果
    currentIndex: null,
    indexHistory: [],
    
    // 状态
    isCreating: false,
    error: null
  }),
  
  getters: {
    availableAlgorithms: (state) => {
      if (state.selectedDatabase === 'milvus') {
        return ['FLAT', 'IVF_FLAT', 'IVF_PQ', 'HNSW'];
      }
      return ['FLAT', 'IVF_FLAT', 'IVF_PQ'];
    },
    
    canStartIndexing: (state) => {
      return state.selectedTaskId && 
             state.selectedDatabase && 
             state.selectedAlgorithm &&
             !state.isCreating;
    }
  },
  
  actions: {
    async fetchVectorTasks() { /* ... */ },
    async createIndex() { /* ... */ },
    async fetchIndexHistory() { /* ... */ },
    async deleteIndex(indexId) { /* ... */ }
  }
});
```

### 4. API 扩展需求

**新增后端 API**:

1. **获取已完成的向量化任务**
   ```
   GET /api/v1/embedding/results?status=SUCCESS
   ```

2. **根据向量化任务创建索引**
   ```
   POST /api/v1/vector-index/indexes/from-embedding
   Body: {
     "embedding_result_id": "xxx",
     "provider": "milvus",
     "index_type": "HNSW",
     "index_params": { "M": 16, "efConstruction": 200 }
   }
   ```

3. **获取索引历史记录**
   ```
   GET /api/v1/vector-index/indexes/history
   Query: page, page_size, sort_by
   ```

4. **删除索引记录**
   ```
   DELETE /api/v1/vector-index/indexes/{index_id}
   ```

## 下一步行动

1. ✅ Phase 0 完成：技术选型确定
2. ✅ Phase 0 补充：前端设计研究完成
3. ⏭️ Phase 1: 更新数据模型和API契约
4. ⏭️ Phase 2: 任务分解和实现计划

## 参考资料

- [FAISS Documentation](https://github.com/facebookresearch/faiss/wiki)
- [FAISS Best Practices](https://github.com/facebookresearch/faiss/wiki/Faiss-building-blocks:-clustering,-PCA,-quantization)
- [Vector Index Comparison](https://benchmark.vectorview.ai/)
- 现有代码参考：`backend/src/services/embedding_service.py`
