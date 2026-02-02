# Tasks: 文档处理模块优化 - 合并加载与解析

**Input**: Design documents from `/specs/001-document-processing-opt/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: 未明确要求测试，本任务列表不包含测试任务。

**Organization**: 任务按用户故事分组，支持独立实现和测试。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 所属用户故事（US1, US2, US3...）

## Path Conventions

- **后端**: `backend/src/`
- **前端**: `frontend/src/`
- **文档**: `documents/`, `README.md`, `backend/README.md`

---

## Phase 1: Setup (环境准备)

**Purpose**: 安装依赖，准备开发环境

- [x] T001 安装 Docling 核心依赖 `pip install docling`
- [x] T002 [P] 安装第一批格式依赖 `pip install PyMuPDF python-docx openpyxl python-pptx`
- [x] T003 [P] 安装第二批格式依赖 `pip install beautifulsoup4 lxml markdown pandas`
- [x] T004 [P] 安装第三批格式依赖 `pip install ebooklib extract-msg webvtt-py jproperties xlrd`
- [x] T005 验证 Docling 安装成功 `python -c "from docling.document_converter import DocumentConverter"`

---

## Phase 2: Foundational (基础架构)

**Purpose**: 创建统一数据结构和核心配置，所有用户故事依赖此阶段

**⚠️ CRITICAL**: 用户故事实现必须等待此阶段完成

- [x] T006 创建统一数据结构模型 `backend/src/models/loading_result.py`
- [x] T007 [P] 创建加载器配置模型 `backend/src/models/loader_config.py`
- [x] T008 [P] 创建格式策略配置 `backend/src/loader_config/format_strategies.py`
- [x] T009 创建加载器基类 `backend/src/providers/loaders/base_loader.py`
- [x] T010 更新加载器注册表 `backend/src/providers/loaders/__init__.py`

**Checkpoint**: 基础架构就绪 - 用户故事可以开始实现

---

## Phase 3: User Story 1 - 移除文档解析模块代码 (Priority: P1) 🎯 MVP

**Goal**: 从后端代码中移除文档解析模块的所有相关代码

**Independent Test**: 移除代码后，启动后端服务，验证所有其他功能正常，文档解析相关 API 返回 404

### Implementation for User Story 1

- [x] T011 [US1] 删除解析 API 文件 `backend/src/api/parsing.py` (已确认不存在)
- [x] T012 [P] [US1] 删除解析服务文件 `backend/src/services/parsing_service.py` (已确认不存在)
- [x] T013 [US1] 从主程序移除 parsing 路由注册 `backend/src/main.py` (已确认无 parsing 引用)
- [x] T014 [US1] 检查并移除其他文件中对 parsing 模块的引用 (已确认无引用)
- [x] T015 [US1] 验证后端服务正常启动，无 parsing 相关导入错误

**Checkpoint**: 解析模块已完全移除，后端服务正常运行

---

## Phase 4: User Story 2 - 集成 Docling 解析器 (Priority: P1)

**Goal**: 集成 Docling 作为主要文档解析器，实现多层级降级策略

**Independent Test**: 上传 PDF/DOCX 文档，验证系统优先使用 Docling 解析，失败时自动降级到备用解析器

### Implementation for User Story 2

- [x] T016 [US2] 创建 Docling 加载器 `backend/src/providers/loaders/docling_loader.py`
- [x] T017 [US2] 实现降级策略管理器 `backend/src/services/fallback_manager.py`
- [x] T018 [US2] 更新加载服务，集成降级策略 `backend/src/services/loading_service.py`
- [x] T019 [US2] 实现智能解析器选择逻辑（基于文件大小和格式）`backend/src/services/loading_service.py`
- [x] T020 [US2] 更新加载 API，支持 loader_type 和 enable_fallback 参数 `backend/src/api/loading.py`
- [x] T021 [US2] 实现解析结果到 StandardDocumentResult 的转换器 `backend/src/utils/result_converter.py`

**Checkpoint**: Docling 集成完成，降级策略正常工作

---

## Phase 5: User Story 3 - 验证主程序清理 (Priority: P1)

**Goal**: 验证应用启动时不再加载解析模块，API 文档中不显示 parsing 端点

**Independent Test**: 检查 `main.py` 中不再包含 parsing 相关导入和路由注册

**Note**: T013 (US1) 已执行实际移除操作，本阶段任务为验证性任务，确保清理完整

### Implementation for User Story 3

- [x] T022 [US3] **验证** main.py 中 parsing 相关导入已被移除 `grep -r "parsing" backend/src/main.py` 返回空
- [x] T023 [US3] **验证** main.py 中 parsing 路由注册已被移除 `backend/src/main.py`
- [x] T024 [US3] 检查并更新 API 文档配置 `backend/src/main.py`
- [x] T025 [US3] 验证 `/docs` 端点不显示 parsing 相关 API

**Checkpoint**: 主程序清理验证完成，API 文档正确

---

## Phase 6: User Story 4 - 扩展格式支持 (Priority: P2)

**Goal**: 按分批策略扩展文档格式支持到 20+ 种

**Independent Test**: 上传各批次支持的文档格式，验证系统能正确识别并选择合适的解析器

### 第一批格式 (PDF/DOCX/XLSX/PPTX) - 已有部分支持，需增强

- [x] T026 [P] [US4] 增强 XLSX 加载器，支持 Docling 降级 `backend/src/providers/loaders/xlsx_loader.py`
- [x] T027 [P] [US4] 增强 PPTX 加载器，支持 Docling 降级 `backend/src/providers/loaders/pptx_loader.py`

### 第二批格式 (HTML/CSV/TXT/MD)

- [x] T028 [P] [US4] 创建 HTML 加载器 `backend/src/providers/loaders/html_loader.py`
- [x] T029 [P] [US4] 创建 CSV 加载器 `backend/src/providers/loaders/csv_loader.py`
- [x] T030 [P] [US4] 创建 JSON 加载器 `backend/src/providers/loaders/json_loader.py`

### 第三批格式 (其他)

- [x] T031 [P] [US4] 创建 XML 加载器 `backend/src/providers/loaders/xml_loader.py`
- [ ] ~~T032 [P] [US4] 创建 EPUB 加载器~~ (不再实现)
- [ ] ~~T033 [P] [US4] 创建 Email (EML) 加载器~~ (不再实现)
- [ ] ~~T034 [P] [US4] 创建 MSG 加载器~~ (不再实现)
- [ ] ~~T035 [P] [US4] 创建 VTT 加载器~~ (不再实现)
- [x] T036 [P] [US4] 创建 Properties 加载器 `backend/src/providers/loaders/properties_loader.py`

### 注册和配置

- [x] T037 [US4] 更新加载器注册表，注册所有新加载器 `backend/src/providers/loaders/__init__.py`
- [x] T038 [US4] 更新格式策略配置，添加新格式映射 `backend/src/loader_config/format_strategies.py`
- [x] T039 [US4] 添加获取加载器列表 API `backend/src/api/loading.py`
- [x] T040 [US4] 添加获取支持格式 API `backend/src/api/loading.py`

**Checkpoint**: 系统支持 20+ 种文档格式 ✅ (已支持 22 种格式)

---

## Phase 7: User Story 5 - 更新项目文档 (Priority: P3)

**Goal**: 更新所有相关的项目文档，移除文档解析模块的说明，添加 Docling 集成描述

**Independent Test**: 搜索所有文档，确认不再包含"文档解析"、"parsing"等相关描述，并包含 Docling 相关说明

### Implementation for User Story 5

- [x] T041 [P] [US5] 更新根目录 README.md，移除解析模块说明，添加 Docling 集成描述
- [x] T042 [P] [US5] 更新 backend/README.md，移除解析相关说明，添加新解析器架构描述
- [x] T043 [US5] 检查并更新 documents/ 目录下相关文档
- [x] T044 [US5] 更新 specs/001-document-processing/ 规格说明（如存在）
- [x] T045 [US5] 更新格式支持列表文档，反映当前支持的所有格式

**Checkpoint**: 所有文档已更新，与代码保持一致 ✅

---

## Phase 8: User Story 6 - 更新前端界面 (Priority: P3)

**Goal**: 移除前端中文档解析相关的界面或功能入口

**Independent Test**: 访问前端应用，确认不存在文档解析相关的菜单项或功能入口

### Implementation for User Story 6

- [x] T046 [US6] 检查并移除前端解析相关组件 `frontend/src/views/` (已确认无 parsing 组件)
- [x] T047 [US6] 更新前端文档服务，移除解析 API 调用 `frontend/src/services/documentService.js` (已确认无 parsing 调用)
- [x] T048 [US6] 更新前端路由配置，移除解析相关路由 `frontend/src/router/` (已确认无 parsing 路由)
- [x] T049 [US6] 添加降级通知组件（显示备用解析器使用提示）`frontend/src/components/document/FallbackNotice.vue`
- [x] T050 [US6] 更新文档加载页面，集成降级通知 `frontend/src/views/DocumentLoad.vue`

**Checkpoint**: 前端界面已更新，无解析相关入口 ✅

---

## Phase 9: Edge Case 处理 (Priority: P2)

**Purpose**: 处理边界情况，确保系统健壮性

- [x] T056 [P] [EC] 处理 chunking 依赖 parsing 结果的数据兼容性 - chunking 模块能正确处理 loading 输出格式
- [x] T057 [P] [EC] 处理历史 parsing 类型处理结果的遗留数据 - 旧格式数据能被正确读取或迁移
- [x] T058 [P] [EC] 处理并发上传相同文件的竞态条件 - 并发上传同一文件不会导致数据损坏 (已有文件系统锁机制)
- [x] T059 [P] [EC] 处理解析过程中文件被删除的情况 - 文件删除时返回友好错误，不崩溃
- [x] T060 [P] [EC] 处理超大文件（>100MB）的内存管理 - 100MB+ 文件解析时记录警告日志

**Checkpoint**: 边界情况处理完成，系统健壮性提升 ✅

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: 最终验证和优化

- [x] T061 运行后端服务，验证所有 API 正常工作
- [x] T062 [P] 运行前端应用，验证界面正常显示 (组件已更新)
- [x] T063 执行 quickstart.md 中的验证步骤
- [x] T064 检查日志输出，确保降级信息正确记录
- [x] T065 验证 API 文档 `/docs` 显示正确的端点信息

**Checkpoint**: 最终验证完成 ✅

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 - 可立即开始
- **Foundational (Phase 2)**: 依赖 Setup 完成 - 阻塞所有用户故事
- **User Story 1 (Phase 3)**: 依赖 Foundational 完成
- **User Story 2 (Phase 4)**: 依赖 Foundational 完成，可与 US1 并行
- **User Story 3 (Phase 5)**: 依赖 US1 完成（确保 parsing 代码已删除）
- **User Story 4 (Phase 6)**: 依赖 US2 完成（需要降级策略框架）
- **User Story 5 (Phase 7)**: 依赖 US1-US4 完成（文档需反映最终状态）
- **User Story 6 (Phase 8)**: 依赖 US1-US2 完成（需要后端 API 稳定）
- **Edge Case (Phase 9)**: 依赖 US2 完成（需要加载框架稳定）
- **Polish (Phase 10)**: 依赖所有用户故事和 Edge Case 完成

### User Story Dependencies

```
                    ┌─────────────────┐
                    │  Setup (P1)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Foundational(P2)│
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    ┌──────▼──────┐   ┌──────▼──────┐         │
    │ US1 移除代码 │   │ US2 Docling │         │
    │   (P1)      │   │   (P1)      │         │
    └──────┬──────┘   └──────┬──────┘         │
           │                 │                 │
    ┌──────▼──────┐   ┌──────▼──────┐         │
    │ US3 清理主程│   │ US4 格式扩展│         │
    │   (P1)      │   │   (P2)      │         │
    └──────┬──────┘   └──────┬──────┘         │
           │                 │                 │
           └────────┬────────┘                 │
                    │                          │
           ┌────────▼────────┐        ┌───────▼───────┐
           │ US5 更新文档    │        │ US6 更新前端  │
           │   (P3)          │        │   (P3)        │
           └────────┬────────┘        └───────┬───────┘
                    │                          │
                    └──────────┬───────────────┘
                               │
                      ┌────────▼────────┐
                      │ Edge Case (P9)  │
                      └────────┬────────┘
                               │
                      ┌────────▼────────┐
                      │  Polish (P10)   │
                      └─────────────────┘
```

### Parallel Opportunities

- **Phase 1**: T002, T003, T004 可并行
- **Phase 2**: T007, T008 可并行
- **Phase 3**: T011, T012 可并行
- **Phase 6**: T026-T036 所有新加载器可并行创建
- **Phase 7**: T041, T042 可并行
- **Phase 9**: T051, T052 可并行

---

## Parallel Example: User Story 4 (格式扩展)

```bash
# 并行创建所有新加载器:
Task: "创建 HTML 加载器 backend/src/providers/loaders/html_loader.py"
Task: "创建 CSV 加载器 backend/src/providers/loaders/csv_loader.py"
Task: "创建 JSON 加载器 backend/src/providers/loaders/json_loader.py"
Task: "创建 XML 加载器 backend/src/providers/loaders/xml_loader.py"
Task: "创建 Properties 加载器 backend/src/providers/loaders/properties_loader.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. 完成 Phase 1: Setup
2. 完成 Phase 2: Foundational (CRITICAL - 阻塞所有故事)
3. 完成 Phase 3: User Story 1 (移除解析模块)
4. 完成 Phase 4: User Story 2 (集成 Docling)
5. **STOP and VALIDATE**: 测试核心功能
6. 部署/演示 MVP

### Incremental Delivery

1. Setup + Foundational → 基础就绪
2. US1 + US2 → 核心功能完成 → **MVP!**
3. US3 → 清理完成 → 部署
4. US4 → 格式扩展 → 部署
5. US5 + US6 → 文档和前端更新 → 最终部署

---

## Summary

| 指标 | 数值 |
|------|------|
| **总任务数** | 65 |
| **US1 任务数** | 5 |
| **US2 任务数** | 6 |
| **US3 任务数** | 4 (验证性任务) |
| **US4 任务数** | 15 |
| **US5 任务数** | 5 |
| **US6 任务数** | 5 |
| **Setup 任务数** | 5 |
| **Foundational 任务数** | 5 |
| **Edge Case 任务数** | 5 |
| **Polish 任务数** | 5 |
| **可并行任务数** | 27 |
| **MVP 范围** | US1 + US2 (11 任务) |

---

## Notes

- [P] 任务 = 不同文件，无依赖
- [Story] 标签映射到特定用户故事，便于追踪
- 每个用户故事应可独立完成和测试
- 每个任务或逻辑组完成后提交
- 在任何检查点停止以独立验证故事
- 避免：模糊任务、同文件冲突、破坏独立性的跨故事依赖
