# Implementation Plan: 向量索引模块（优化版）

**Branch**: `004-vector-index-opt` | **Date**: 2026-02-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-vector-index-opt/spec.md`

## Summary

向量索引模块优化版，基于 004-vector-index 进行简化，**移除 FAISS 支持，统一使用 Milvus 作为唯一向量数据库后端**。主要功能包括：
- 向量数据索引构建（支持 FLAT/IVF_FLAT/IVF_PQ/HNSW 四种算法）
- 向量相似度检索（支持 TopK 查询和相似度阈值过滤）
- 索引增量更新与删除（幂等性设计）
- 前端索引管理界面（左右分栏布局 + 实时进度展示）

## Technical Context

**Language/Version**: Python 3.11 (Backend), TypeScript/JavaScript (Frontend with Vue 3)
**Primary Dependencies**: 
- Backend: FastAPI, pymilvus==2.3.4, SQLAlchemy, Pydantic
- Frontend: Vue 3, Vite, TDesign Vue Next, Pinia
**Storage**: Milvus 2.x (向量数据库), SQLite/PostgreSQL (元数据)
**Testing**: pytest, pytest-asyncio, pytest-cov
**Target Platform**: Linux server, macOS (development)
**Project Type**: web (frontend + backend)
**Performance Goals**: 
- 单次 TopK 查询（K=5）响应 < 100ms (P95)
- 索引构建 >= 1000 条向量/秒 (1536维)
- 并发支持 >= 10 请求，吞吐量 >= 50 QPS
**Constraints**: 
- Milvus 连接失败时指数退避重试（1s→2s→4s，最多3次）
- 删除不存在的向量ID静默忽略（幂等性）
**Scale/Scope**: 支持 1,000 到 1,000,000 级别向量规模

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. 模块化架构 | ✅ PASS | 向量索引模块独立设计，通过明确接口与其他模块通信 |
| II. 多提供商支持 | ✅ PASS | 本版本专注 Milvus，符合宪章"支持多种技术提供商"原则 |
| III. 结果持久化 | ✅ PASS | 索引元数据保存为 JSON 格式，Milvus 原生持久化向量数据 |
| IV. 用户体验优先 | ✅ PASS | 采用 Vue3 + TDesign，左右分栏布局，实时进度展示 |
| V. API标准化 | ✅ PASS | 基于 FastAPI 实现 RESTful API，统一错误处理 |

## Project Structure

### Documentation (this feature)

```text
specs/004-vector-index-opt/
├── plan.md              # This file
├── research.md          # Phase 0 output - 技术研究
├── data-model.md        # Phase 1 output - 数据模型
├── quickstart.md        # Phase 1 output - 快速入门
├── contracts/           # Phase 1 output - API契约
│   ├── index-api.yaml   # 索引管理 API
│   └── search-api.yaml  # 检索 API
└── tasks.md             # Phase 2 output - 任务分解
```

### Source Code (repository root)

```text
# Web application structure (frontend + backend)
backend/
├── src/
│   ├── api/
│   │   └── vector_index.py          # 向量索引 API 路由
│   ├── models/
│   │   └── vector_index.py          # 向量索引数据模型
│   ├── schemas/
│   │   └── vector_index.py          # Pydantic 请求/响应模式
│   ├── services/
│   │   ├── vector_index_service.py  # 向量索引业务逻辑
│   │   └── providers/
│   │       ├── __init__.py          # Provider 注册
│   │       ├── base_provider.py     # 抽象基类
│   │       └── milvus_provider.py   # Milvus 实现
│   └── config/
│       └── vector_config.py         # 向量数据库配置
├── tests/
│   ├── unit/
│   │   └── test_vector_index.py     # 单元测试
│   └── integration/
│       └── test_vector_milvus.py    # Milvus 集成测试
└── results/
    └── vector_index/                # 索引结果 JSON 存储

frontend/
├── src/
│   ├── components/
│   │   └── VectorIndex/
│   │       ├── IndexCreate.vue      # 索引创建组件
│   │       ├── IndexList.vue        # 索引列表组件
│   │       └── VectorSearch.vue     # 向量搜索组件
│   ├── views/
│   │   └── VectorIndex.vue          # 向量索引页面
│   ├── services/
│   │   └── vectorIndexApi.js        # API 调用封装
│   └── stores/
│       └── vectorIndexStore.js      # Pinia 状态管理
└── tests/
    └── components/
        └── VectorIndex.spec.js      # 组件测试
```

**Structure Decision**: 采用现有项目的 Web 应用结构（frontend + backend），复用已有的向量索引模块代码，移除 FAISS 相关实现。

## Complexity Tracking

> 本版本无宪章违规，通过移除 FAISS 简化了架构复杂度。

| Simplification | Benefit | Trade-off |
|----------------|---------|-----------|
| 移除 FAISS | 减少代码维护、统一存储后端 | 失去本地轻量级存储选项 |
| 统一 Milvus | 降低复杂度、减少测试场景 | 需要 Milvus 服务运行 |

## Key Design Decisions

### 1. 索引算法支持
- **FLAT**: 暴力搜索，精确匹配，适用于小规模数据
- **IVF_FLAT**: 倒排文件索引，平衡精度与速度
- **IVF_PQ**: 倒排文件 + 乘积量化，适用于大规模数据
- **HNSW**: 层次化可导航小世界图，高召回率

### 2. 错误处理策略
- **Milvus 连接失败**: 指数退避重试（1s→2s→4s，最多3次）
- **删除不存在向量**: 静默忽略，返回成功（幂等性设计）
- **维度不匹配**: 拒绝该向量，返回明确错误信息

### 3. 元数据字段设计
- **必需字段**: `doc_id`, `chunk_index`, `created_at`
- **可选字段**: 文本内容、来源文件名等自定义字段

### 4. 前端交互设计
- **进度展示**: 实时进度条（百分比 + 已处理/总数）+ 状态文字
- **错误展示**: 错误弹窗（Modal）显示错误类型、详情和建议操作
