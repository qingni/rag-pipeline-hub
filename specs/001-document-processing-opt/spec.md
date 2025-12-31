# Feature Specification: 文档处理模块优化 - 合并加载与解析

**Feature Branch**: `001-document-processing-opt`  
**Created**: 2025-12-31  
**Status**: Draft  
**Input**: User description: "文档加载和文档解析模块合并，保留文档加载模块，去掉文档解析模块。修改所有相关的文档，去掉文档解析模块的相关说明"

## 背景

当前系统存在两个功能重叠的模块：
- **文档加载模块 (Loading)**: 负责读取文档内容、提取文本和元数据
- **文档解析模块 (Parsing)**: 基于加载结果进行二次处理（全文、分页、按标题等）

这两个模块功能高度重叠，文档解析模块实际上只是对加载结果的简单重组，增加了系统复杂度和用户操作步骤。本次优化将合并这两个模块，保留文档加载模块并增强其功能，移除冗余的文档解析模块。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 移除文档解析模块代码 (Priority: P1)

开发者需要从后端代码中移除文档解析模块的所有相关代码，包括 API 路由、服务层和相关引用，确保系统在移除后仍能正常运行。

**Why this priority**: 这是核心改动，必须先完成代码层面的移除，才能进行后续的文档更新。

**Independent Test**: 移除代码后，启动后端服务，验证所有其他功能正常，文档解析相关 API 返回 404。

**Acceptance Scenarios**:

1. **Given** 后端代码包含文档解析模块, **When** 移除 `backend/src/api/parsing.py` 和 `backend/src/services/parsing_service.py`, **Then** 后端服务正常启动无报错
2. **Given** 文档解析 API 已移除, **When** 调用 `/api/v1/parse` 端点, **Then** 系统返回 404 Not Found
3. **Given** 文档解析模块已移除, **When** 执行文档加载操作, **Then** 加载功能正常工作不受影响

---

### User Story 2 - 清理主程序和路由注册 (Priority: P1)

从 `main.py` 中移除文档解析模块的路由注册和相关导入，确保应用启动时不再加载解析模块。

**Why this priority**: 与 User Story 1 同等重要，是代码移除的必要步骤。

**Independent Test**: 检查 `main.py` 中不再包含 parsing 相关导入和路由注册。

**Acceptance Scenarios**:

1. **Given** `main.py` 包含 parsing 路由注册, **When** 移除相关代码, **Then** 应用正常启动且 API 文档中不显示 parsing 端点
2. **Given** 其他模块可能引用 parsing 服务, **When** 检查并移除所有引用, **Then** 无导入错误或运行时错误

---

### User Story 3 - 更新项目文档 (Priority: P2)

更新所有相关的项目文档，移除文档解析模块的说明，确保文档与代码保持一致。

**Why this priority**: 文档更新是代码改动后的必要步骤，确保开发者和用户获得准确信息。

**Independent Test**: 搜索所有文档，确认不再包含"文档解析"、"parsing"等相关描述。

**Acceptance Scenarios**:

1. **Given** README.md 包含文档解析功能说明, **When** 更新文档移除相关内容, **Then** README 只描述文档加载功能
2. **Given** `documents/` 目录可能包含解析相关文档, **When** 检查并更新或移除相关文件, **Then** 文档结构清晰一致
3. **Given** `specs/` 目录包含原始规格说明, **When** 更新 001-document-processing 规格, **Then** 规格说明反映当前系统架构

---

### User Story 4 - 更新前端界面（如有） (Priority: P3)

如果前端存在文档解析相关的界面或功能入口，需要移除或调整。

**Why this priority**: 前端改动依赖后端 API 变更，优先级较低。

**Independent Test**: 访问前端应用，确认不存在文档解析相关的菜单项或功能入口。

**Acceptance Scenarios**:

1. **Given** 前端可能有解析功能入口, **When** 检查并移除相关组件, **Then** 前端界面不显示解析相关选项
2. **Given** 前端 API 调用可能包含解析接口, **When** 移除相关调用代码, **Then** 前端功能正常无报错

---

### Edge Cases

- 当其他模块（如 chunking）依赖 parsing 结果时，如何处理数据兼容性？
- 当数据库中存在历史的 parsing 类型处理结果时，如何处理这些遗留数据？
- 当用户尝试访问已移除的解析 API 时，系统应返回清晰的错误信息

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统必须移除 `backend/src/api/parsing.py` 文件
- **FR-002**: 系统必须移除 `backend/src/services/parsing_service.py` 文件
- **FR-003**: 系统必须从 `backend/src/main.py` 中移除 parsing 相关的导入和路由注册
- **FR-004**: 系统必须检查并移除其他文件中对 parsing 模块的引用
- **FR-005**: 系统必须更新 `README.md`，移除文档解析功能的描述
- **FR-006**: 系统必须更新 `backend/README.md`，移除解析相关说明
- **FR-007**: 系统必须检查 `documents/` 目录，更新或移除解析相关文档
- **FR-008**: 系统必须更新 `specs/001-document-processing/` 规格说明
- **FR-009**: 系统必须检查前端代码，移除解析相关的组件和 API 调用
- **FR-010**: 移除后，文档加载功能必须保持完整可用

### Key Entities

- **待移除文件**:
  - `backend/src/api/parsing.py` - 解析 API 路由
  - `backend/src/services/parsing_service.py` - 解析服务实现

- **待修改文件**:
  - `backend/src/main.py` - 移除路由注册
  - `README.md` - 更新功能说明
  - `backend/README.md` - 更新后端说明
  - `documents/` 目录下相关文档
  - `specs/001-document-processing/` 规格文档

### Assumptions

- 文档加载模块已具备足够的功能，无需从解析模块迁移任何功能
- 数据库中的历史 parsing 处理结果可以保留，不影响系统运行
- 前端如有解析相关功能，可以直接移除而无需替代方案

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 后端服务启动无错误，所有非解析功能正常工作
- **SC-002**: 代码库中不存在 `parsing_service` 和 `parsing.py` 文件
- **SC-003**: 搜索代码库，"parsing" 相关引用仅存在于注释或历史记录中
- **SC-004**: 所有文档中不再描述"文档解析"作为独立功能模块
- **SC-005**: API 文档 (`/docs`) 中不显示 parsing 相关端点
- **SC-006**: 前端应用正常运行，无解析相关功能入口
