# Implementation Plan: 向量索引模块

**Branch**: `004-vector-index` | **Date**: 2025-12-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-vector-index/spec.md`

**Note**: 本计划基于 2024-12-24 澄清的需求重新规划，重点关注前端界面和向量化任务集成。

## Summary

向量索引模块实现 RAG 系统的核心检索能力。基于澄清的需求：
- **前端布局**：左右分栏（左侧配置区 + 右侧双Tab结果区），样式参考文档向量化模块
- **数据源**：下拉选择已完成的向量化任务，自动获取向量数据
- **向量数据库**：支持 Milvus（生产）+ FAISS（开发）
- **索引算法**：FLAT / IVF_FLAT / IVF_PQ / HNSW
- **历史记录**：支持查看详情 + 删除操作

技术方案采用 Milvus 作为主要向量数据库，FAISS 作为轻量级备选，通过 Provider Pattern 实现多后端支持。

## Technical Context

**Language/Version**: Python 3.11 (后端) + Vue 3 + Vite (前端)  
**Primary Dependencies**: FastAPI 0.104.1, pymilvus 2.3.4, faiss-cpu 1.7.4, TDesign Vue Next, Pinia  
**Storage**: PostgreSQL 14+ (元数据) + Milvus/FAISS (向量数据) + JSON (结果持久化)  
**Testing**: pytest (后端), Vitest (前端)  
**Target Platform**: Linux/macOS 服务器 + 现代浏览器  
**Project Type**: Web Application (frontend + backend)  
**Performance Goals**: 单次查询 <100ms (P95)，索引构建 >1000 vec/s  
**Constraints**: <200ms P95 查询延迟，支持 10 并发读  
**Scale/Scope**: 10K-100万向量规模，单租户

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. 模块化架构** | ✅ PASS | 独立 `vector_index_service.py`，Provider Pattern 支持多后端 |
| **II. 多提供商支持** | ✅ PASS | 支持 Milvus + FAISS 两种向量数据库 |
| **III. 结果持久化** | ✅ PASS | JSON 格式保存索引配置和操作日志 |
| **IV. 用户体验优先** | ✅ PASS | Vue3 + TDesign，左右分栏布局，与向量化模块一致 |
| **V. API标准化** | ✅ PASS | RESTful API，统一响应格式，OpenAPI 文档 |

**Constitution Gate**: ✅ PASSED

## Project Structure

### Documentation (this feature)

```text
specs/004-vector-index/
├── plan.md              # 本文件 - 实现计划
├── research.md          # Phase 0 - 技术调研
├── data-model.md        # Phase 1 - 数据模型设计
├── quickstart.md        # Phase 1 - 快速开始指南
├── contracts/           # Phase 1 - API 契约
│   ├── api-contract.yaml
│   └── vector-index-api.yaml
├── tasks.md             # Phase 2 - 任务分解
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   └── vector_index.py          # API 路由 (已存在)
│   ├── models/
│   │   ├── vector_index.py          # SQLAlchemy 模型 (已存在)
│   │   ├── index_statistics.py      # 统计模型 (已存在)
│   │   └── query_history.py         # 查询历史模型 (已存在)
│   ├── services/
│   │   ├── vector_index_service.py  # 核心服务 (已存在)
│   │   ├── index_registry.py        # 索引注册表 (已存在)
│   │   └── providers/
│   │       ├── base_provider.py     # Provider 基类 (需创建)
│   │       ├── faiss_provider.py    # FAISS 实现 (已存在)
│   │       └── milvus_provider.py   # Milvus 实现 (需创建)
│   └── exceptions/
│       └── vector_index_errors.py   # 错误定义 (已存在)
└── tests/
    └── test_vector_index/           # 测试用例 (需创建)

frontend/
├── src/
│   ├── views/
│   │   └── VectorIndex.vue          # 主页面 (已存在，需重构)
│   ├── components/
│   │   └── VectorIndex/
│   │       ├── IndexConfigPanel.vue     # 左侧配置面板 (需创建)
│   │       ├── VectorTaskSelector.vue   # 向量化任务选择器 (需创建)
│   │       ├── DatabaseSelector.vue     # 数据库选择器 (需创建)
│   │       ├── AlgorithmSelector.vue    # 算法选择器 (需创建)
│   │       ├── IndexResultCard.vue      # 索引结果卡片 (需创建)
│   │       └── IndexHistoryList.vue     # 历史记录列表 (需创建)
│   ├── services/
│   │   └── vectorIndexApi.js        # API 服务 (已存在，需扩展)
│   └── stores/
│       └── vectorIndexStore.js      # Pinia Store (已存在，需扩展)
└── tests/
    └── components/                   # 组件测试 (需创建)
```

**Structure Decision**: Web Application 结构，前后端分离。前端参考 `DocumentEmbedding.vue` 的布局模式，后端复用现有 Provider Pattern。

## Key Design Decisions

### 1. 数据源集成 - 向量化任务选择

**Decision**: 通过 API 获取已完成的向量化任务列表，用户选择后自动加载向量数据

**Implementation**:
```python
# API: GET /api/v1/vector-index/embedding-tasks
# 返回所有状态为 SUCCESS 的 EmbeddingResult 列表
```

### 2. 前端组件复用

**Decision**: 复用 `DocumentEmbedding.vue` 的布局模式和组件结构

**Components to Create**:
- `VectorTaskSelector.vue` - 类似 `DocumentSelector.vue`
- `DatabaseSelector.vue` - 类似 `ModelSelector.vue`
- `IndexHistoryList.vue` - 类似 `EmbeddingHistoryList.vue`

### 3. Provider Pattern 扩展

**Decision**: 定义 `BaseProvider` 抽象类，FAISS 和 Milvus 均实现该接口

**Interface**:
```python
class BaseProvider(ABC):
    @abstractmethod
    def create_index(self, config: IndexConfig) -> str: ...
    @abstractmethod
    def insert_vectors(self, index_id: str, vectors: List[Vector]) -> int: ...
    @abstractmethod
    def search_vectors(self, index_id: str, query: SearchQuery) -> List[SearchResult]: ...
    @abstractmethod
    def delete_vectors(self, index_id: str, vector_ids: List[str]) -> int: ...
```

## Complexity Tracking

> 无宪章违规，无需记录
