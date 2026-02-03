# Implementation Plan: 文档向量化功能优化

**Branch**: `003-vector-embedding-opt` | **Date**: 2026-02-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-vector-embedding-opt/spec.md`

## Summary

本次优化基于现有向量化功能（003-vector-embedding），通过引入多模态向量化、批量处理优化、增量向量化、向量缓存、**智能模型推荐**等高级技术，全面提升向量化模块的效率、可靠性和用户体验。

**核心优化项**:
1. **多模态向量化** - 支持图片 base64 直接向量化，失败时降级为文本描述
2. **批量处理优化** - 可配置并发控制、指数退避重试、部分成功返回
3. **增量向量化** - 基于内容哈希检测变更，避免重复计算
4. **向量缓存机制** - LRU 缓存策略，支持跨文档复用
5. **智能模型推荐** - 基于文档特征（语言、领域、多模态比例）自动推荐最佳嵌入模型
6. **前端体验优化** - 进度可视化、推荐卡片、结果对比

## Technical Context

**Language/Version**: Python 3.11 (后端) + JavaScript ES2020+ (前端)  
**Primary Dependencies**: FastAPI 0.104.1, openai (API 兼容), asyncio, Vue 3, Vite, TDesign Vue Next, Pinia, ECharts (雷达图)  
**Storage**: SQLite/PostgreSQL (元数据) + JSON (向量结果) + 内存/Redis (缓存)  
**Testing**: pytest (后端), Vitest (前端)  
**Target Platform**: Linux/macOS 服务器, 现代浏览器  
**Project Type**: Web 应用（前后端分离）  
**Performance Goals**: 500 分块 <30s (5 并发), 进度推送 <500ms, 缓存查询 <10ms, 特征分析 <2s (单文档)  
**Constraints**: 内存缓存 <500MB, API 并发 ≤20, 批量大小 ≤200  
**Scale/Scope**: 单次最大 10000 分块, 并发任务 ≤5, 批量推荐 ≤100 文档

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 | 状态 | 说明 |
|------|------|------|
| I. 模块化架构 | ✅ PASS | 新增多模态处理器、缓存管理器、进度跟踪器、特征分析器、推荐引擎作为独立模块 |
| II. 多提供商支持 | ✅ PASS | 支持多模态模型切换，智能推荐最佳模型，保留纯文本模型作为 fallback |
| III. 结果持久化 | ✅ PASS | 向量化结果保存为 JSON，支持历史记录和对比；模型能力配置持久化 |
| IV. 用户体验优先 | ✅ PASS | 前端采用 Vue3 + TDesign，推荐卡片、雷达图、进度展示、结果可视化 |
| V. API标准化 | ✅ PASS | 新增 API 遵循 RESTful 规范，支持 WebSocket/SSE |

**Gate Result**: ✅ ALL PASS - 可进入 Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/003-vector-embedding-opt/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── embedding-api.yaml
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (by /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   ├── embedding.py                   # 扩展：批量向量化、进度查询端点
│   │   ├── embedding_progress.py          # 新增：WebSocket/SSE 进度推送
│   │   ├── embedding_cache.py             # 新增：缓存管理 API
│   │   └── embedding_recommend.py         # 新增：智能模型推荐 API
│   ├── models/
│   │   ├── embedding_task.py              # 扩展：进度跟踪字段
│   │   ├── embedding_result.py            # 扩展：缓存信息、多模态统计
│   │   ├── vector_cache.py                # 新增：缓存实体模型
│   │   ├── document_features.py           # 新增：文档特征实体
│   │   ├── model_capability.py            # 新增：模型能力配置实体
│   │   └── model_recommendation.py        # 新增：推荐结果实体
│   ├── providers/
│   │   └── embedders/
│   │       ├── base_embedder.py           # 扩展：批量处理接口
│   │       ├── multimodal_embedder.py     # 新增：多模态向量化器
│   │       ├── batch_embedder.py          # 新增：批量处理器（并发控制）
│   │       └── cached_embedder.py         # 新增：缓存装饰器
│   ├── services/
│   │   ├── embedding_service.py           # 扩展：增量向量化、任务管理
│   │   ├── embedding_cache_service.py     # 新增：缓存服务
│   │   ├── embedding_progress_service.py  # 新增：进度跟踪服务
│   │   ├── content_hash_service.py        # 新增：内容哈希服务
│   │   ├── document_feature_service.py    # 新增：文档特征分析服务
│   │   ├── model_capability_service.py    # 新增：模型能力管理服务
│   │   └── model_recommend_service.py     # 新增：智能推荐引擎服务
│   ├── config/
│   │   └── model_capabilities.yaml        # 新增：预置模型能力配置
│   └── utils/
│       ├── retry_handler.py               # 扩展：指数退避重试
│       ├── rate_limiter.py                # 新增：速率限制器
│       ├── language_detector.py           # 新增：语言检测工具
│       └── domain_classifier.py           # 新增：领域分类工具
└── tests/
    ├── unit/
    │   ├── embedders/
    │   ├── services/
    │   │   ├── test_document_feature_service.py
    │   │   ├── test_model_capability_service.py
    │   │   └── test_model_recommend_service.py
    │   └── utils/
    │       ├── test_language_detector.py
    │       └── test_domain_classifier.py
    └── integration/
        └── test_recommendation_flow.py

frontend/
├── src/
│   ├── components/
│   │   └── embedding/
│   │       ├── EmbeddingProgress.vue          # 新增：进度条组件
│   │       ├── EmbeddingConfig.vue            # 扩展：高级配置面板
│   │       ├── EmbeddingStatistics.vue        # 新增：统计图表组件
│   │       ├── ModelComparison.vue            # 新增：模型对比组件
│   │       ├── CacheStatus.vue                # 新增：缓存状态组件
│   │       ├── ModelRecommendCard.vue         # 新增：推荐卡片组件
│   │       ├── FeatureRadarChart.vue          # 新增：特征匹配度雷达图
│   │       ├── OutlierDocumentList.vue        # 新增：异常文档列表组件
│   │       └── ModelCapabilityManager.vue     # 新增：模型能力管理组件
│   ├── views/
│   │   ├── DocumentEmbed.vue                  # 扩展：集成推荐组件
│   │   └── ModelCapabilityAdmin.vue           # 新增：管理员配置页面
│   ├── stores/
│   │   ├── embeddingStore.js                  # 扩展：进度、缓存状态
│   │   └── modelRecommendStore.js             # 新增：推荐状态管理
│   └── services/
│       ├── embeddingService.js                # 扩展：新 API 调用
│       ├── embeddingProgressService.js        # 新增：WebSocket 进度服务
│       └── modelRecommendService.js           # 新增：推荐 API 服务
└── tests/
    └── components/
        ├── ModelRecommendCard.test.js
        ├── FeatureRadarChart.test.js
        └── OutlierDocumentList.test.js
```

**Structure Decision**: 沿用现有 Web 应用架构，在 backend/frontend 目录下扩展功能模块。智能推荐作为独立服务模块实现，便于后续维护和扩展。

## Implementation Phases

### Phase 0: Research & Prototyping
- 调研主流嵌入模型的能力特征和最佳实践
- 验证语言检测和领域分类的可行方案
- 原型验证加权评分算法的有效性

### Phase 1: Design
- 完善数据模型定义（DocumentFeatures、ModelCapability、ModelRecommendation）
- 设计 API 契约（推荐、特征分析、能力管理）
- 设计前端组件交互流程

### Phase 2: Tasks Breakdown
- 按优先级分解实现任务
- P1: 多模态向量化、批量处理、进度反馈、智能推荐
- P2: 增量向量化、缓存机制、模型能力管理
- P3: 结果可视化、导出功能

## Key Design Decisions

### 1. 智能推荐算法
采用**加权评分算法**，各维度分别计算匹配度得分后加权求和：
- 语言匹配度 (40%): 文档主要语言与模型语言支持度匹配
- 领域匹配度 (35%): 文档领域与模型领域专长匹配
- 多模态支持度 (25%): 文档多模态比例与模型多模态能力匹配

### 2. 模型能力数据来源
采用**静态配置 + 管理界面**方案：
- 预置 YAML 配置文件，包含主流模型的能力评分
- 提供管理界面允许用户调整和添加新模型

### 3. 批量推荐策略
采用**统一推荐 + 异常标注**方案：
- 分析所有文档的综合特征，提供统一推荐
- 检测并标注特征偏离较大的文档（偏离度 > 阈值）

### 4. 推荐结果展示
采用**推荐卡片 + 雷达图**方案：
- 卡片展示 Top 3 推荐模型、推荐理由
- 雷达图可视化各维度匹配度

## Complexity Tracking

> 无宪章违规项，本节留空。

## Dependencies

| 依赖项 | 用途 | 版本要求 |
|--------|------|----------|
| langdetect | 语言检测 | >=1.0.9 |
| scikit-learn | 领域分类（TF-IDF + 朴素贝叶斯） | >=1.3.0 |
| echarts | 雷达图可视化 | >=5.4.0 |
| pyyaml | 配置文件解析 | >=6.0 |

## Risk Assessment

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 语言检测准确率不足 | 推荐结果偏差 | 使用多种检测器投票，低置信度时提示用户确认 |
| 领域分类模型冷启动 | 领域判断不准 | 预置通用领域分类模型，支持用户反馈优化 |
| 模型能力评分主观性 | 推荐效果参差 | 提供管理界面，支持用户根据实际效果调整 |
| 批量文档特征差异大 | 统一推荐困难 | 设置偏离阈值，自动标注异常文档 |

## Next Steps

1. 执行 `/speckit.tasks` 生成任务清单
2. 按优先级实现 P1 功能（多模态向量化、智能推荐）
3. 集成测试验证推荐准确率
