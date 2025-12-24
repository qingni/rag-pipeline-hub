# Implementation Plan: 向量索引模块

**Branch**: `004-vector-index` | **Date**: 2025-12-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-vector-index/spec.md`

**Note**: This plan has been regenerated based on the updated technical priority: Milvus as primary, FAISS as fallback.

## Summary

向量索引模块是RAG系统的核心检索引擎，负责构建、管理和查询向量索引。**技术选型已调整为：Milvus 2.3.4 作为主要向量数据库，FAISS 1.7.4 作为轻量级备选方案**。系统支持多种索引算法（FLAT, IVF_FLAT, IVF_PQ, HNSW），提供高性能的相似度检索能力（<50ms查询延迟，>100 QPS），并通过PostgreSQL管理索引元数据。

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: 
  - **Milvus 2.3.4** (pymilvus) - 主要向量数据库
  - FAISS 1.7.4 (faiss-cpu) - 备选向量索引库
  - FastAPI 0.104.1 - Web框架
  - SQLAlchemy 2.0.23 - ORM
  - PostgreSQL 14+ - 元数据存储
  
**Storage**: 
  - **Milvus分布式存储（主）**: MinIO/S3或本地磁盘，支持自动分片和持久化
  - FAISS本地文件存储（备）: `.index`二进制文件 + PostgreSQL元数据
  
**Testing**: pytest + pytest-asyncio（异步测试）  
**Target Platform**: Linux server (Docker容器化部署)
  - **macOS 开发环境**: 需要使用 Colima 启动 Docker 运行时
  - **Linux 生产环境**: 直接使用系统 Docker
  - **Windows**: 推荐 Docker Desktop 或 WSL2 + Docker  
**Project Type**: Web application (FastAPI backend + Vue3 frontend)  

**Performance Goals**:
  - **查询延迟**: <50ms (P95) with Milvus HNSW索引
  - **吞吐量**: >100 QPS (并发查询)
  - **索引构建速度**: >2000 vectors/s (1536维)
  - **检索精度**: >98% recall@K (与暴力搜索对比)
  
**Constraints**:
  - **并发控制**: Milvus原生MVCC（多读多写），FAISS使用RWLock（10读1写）
  - **内存占用**: 索引大小 <150% 原始向量数据
  - **持久化延迟**: Milvus自动flush，FAISS每1000次更新或5分钟触发
  - **高可用**: Milvus支持主从复制，FAISS依赖应用层备份
  
**Scale/Scope**:
  - **Milvus方案**: 支持亿级向量（1B+ vectors）
  - **FAISS方案**: 适合百万级向量（1M vectors）
  - **索引数量**: 支持多租户，每个用户/项目独立索引
  - **向量维度**: 128-1536 (可配置)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ I. 模块化架构
- [x] 向量索引作为独立功能模块设计
- [x] 通过明确的API接口与其他模块通信（Embedding Service、Document Service）
- [x] 独立的服务层实现：`vector_index_service.py`
- [x] 支持插件化扩展：多Provider架构（Milvus主、FAISS备）

### ✅ II. 多提供商支持
- [x] **向量数据库Provider**：Milvus（主）+ FAISS（备）
- [x] **索引算法**：FLAT, IVF_FLAT, IVF_PQ, HNSW（Milvus）/ IndexFlatIP, IndexIVFPQ（FAISS）
- [x] **相似度计算**：余弦相似度（默认）、欧氏距离、点积
- [x] Provider选择逻辑：基于配置文件或运行时参数

### ✅ III. 结果持久化 (NON-NEGOTIABLE)
- [x] **索引构建结果**：保存为JSON（`索引名_timestamp.json`）
- [x] **查询结果**：保存为JSON（`query_result_timestamp.json`）
- [x] **索引持久化**：Milvus自动持久化 / FAISS `.index`文件
- [x] **元数据持久化**：PostgreSQL存储索引配置和统计信息

### ✅ IV. 用户体验优先
- [x] 前端技术栈：Vue3 + Vite + TDesign Vue Next
- [x] 页面布局：左侧导航栏 + 右侧内容区域
- [x] 功能页面：左侧控制面板（索引管理、查询参数）+ 右侧内容显示（查询结果、可视化）
- [x] 用户功能：索引列表查看、创建索引、向量搜索、结果预览、性能统计

### ✅ V. API标准化
- [x] 基于FastAPI的RESTful API
- [x] 统一响应格式：`{status, data, timestamp}`
- [x] 统一错误处理：HTTP状态码 + 错误详情
- [x] API文档：自动生成OpenAPI/Swagger文档
- [x] 加载状态管理：异步任务状态跟踪

### 🔍 Gates Summary
**Status**: ✅ **PASS** - 所有宪章要求均满足
- 模块化架构完全对齐
- 多Provider支持符合扩展性原则
- 结果持久化机制完整
- 前端使用标准技术栈
- API设计遵循RESTful规范

## Project Structure

### Documentation (this feature)

```text
specs/004-vector-index/
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0 output (technical decisions)
├── data-model.md        # Phase 1 output (entities and database schema)
├── quickstart.md        # Phase 1 output (setup and usage guide)
├── contracts/           # Phase 1 output (API contracts)
│   └── vector-index-api.yaml  # OpenAPI specification
└── tasks.md             # Phase 2 output (NOT created yet)
```

### Source Code (repository root)

```text
# Web application structure (backend + frontend)

backend/
├── src/
│   ├── models/
│   │   └── vector_index.py          # VectorIndex, IndexMetadata models
│   ├── services/
│   │   ├── vector_index_service.py  # Main service orchestration
│   │   ├── providers/
│   │   │   ├── base_provider.py     # Abstract Provider interface
│   │   │   ├── milvus_provider.py   # Milvus implementation (PRIMARY)
│   │   │   └── faiss_provider.py    # FAISS implementation (FALLBACK)
│   │   └── index_registry.py        # Index management registry
│   ├── api/
│   │   └── routes/
│   │       └── vector_index.py      # REST endpoints
│   └── utils/
│       ├── vector_utils.py          # Vector normalization, validation
│       └── similarity.py            # Similarity metrics
└── tests/
    ├── unit/
    │   ├── test_milvus_provider.py
    │   ├── test_faiss_provider.py
    │   └── test_vector_index_service.py
    ├── integration/
    │   ├── test_index_api.py
    │   └── test_provider_switching.py
    └── contract/
        └── test_api_contracts.py

frontend/
├── src/
│   ├── components/
│   │   ├── VectorIndex/
│   │   │   ├── IndexList.vue        # 索引列表（t-table）
│   │   │   ├── IndexCreate.vue      # 创建索引（t-form）
│   │   │   ├── VectorSearch.vue     # 向量搜索（t-input, t-slider）
│   │   │   └── SearchResults.vue    # 搜索结果（t-card, t-list）
│   ├── pages/
│   │   └── VectorIndexPage.vue      # 主页面（左侧面板 + 右侧内容）
│   ├── services/
│   │   └── vectorIndexApi.js        # API调用封装
│   └── stores/
│       └── vectorIndexStore.js      # Pinia状态管理
└── tests/
    └── components/
        └── VectorIndex/
            └── IndexList.spec.js

# Database
migrations/
└── vector_index/
    ├── 001_create_vector_indexes_table.sql
    ├── 002_create_index_statistics_table.sql
    └── 003_create_vector_metadata_table.sql
```

**Structure Decision**: 
采用标准Web应用架构，后端使用Provider模式实现多向量数据库支持（Milvus主、FAISS备），前端基于TDesign组件库构建用户界面。索引管理通过Registry模式实现多索引支持。

## Complexity Tracking

> **本节留空 - 无宪章违规需要证明**

所有设计决策均符合系统宪章要求，无额外复杂性引入：
- 模块化架构与现有系统一致
- Provider模式符合多提供商支持原则
- 使用现有技术栈（FastAPI, Vue3, PostgreSQL）
- API设计遵循RESTful标准

**技术选型变更说明**：
- **变更内容**：从"FAISS为主，Milvus为备"调整为"Milvus为主，FAISS为备"
- **变更原因**：
  1. 生产级需求：Milvus提供企业级特性（分布式、高可用、监控）
  2. 性能提升：原生并发支持，>100 QPS，支持亿级向量
  3. 运维简化：自动持久化、元数据管理、集群部署
  4. 扩展性：满足未来大规模数据增长需求
- **影响评估**：
  - 部署复杂度略增（需Docker容器运行Milvus）
  - 开发环境可继续使用FAISS（轻量级）
  - API层保持Provider抽象，切换透明
  - 性能提升2-100倍（根据场景）

| 维度 | Milvus方案 | FAISS方案 | 优势 |
|------|-----------|----------|------|
| 查询延迟 | <50ms (HNSW) | <100ms (IVF) | 2倍提升 |
| 吞吐量 | >100 QPS | ~20 QPS | 5倍提升 |
| 并发模型 | MVCC（多读多写） | RWLock（10读1写） | 并发能力强 |
| 规模上限 | 亿级 | 百万级 | 100倍扩展 |
| 运维成本 | 中等（Docker部署） | 低（进程内） | FAISS更简单 |
