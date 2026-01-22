# Feature Specification: 文档处理模块优化 - 合并加载与解析

**Feature Branch**: `001-document-processing-opt`  
**Created**: 2025-12-31  
**Status**: Draft  
**Input**: User description: "文档加载和文档解析模块合并，保留文档加载模块，去掉文档解析模块。修改所有相关的文档，去掉文档解析模块的相关说明"

## Clarifications

### Session 2025-01-13

- Q: 在基于 Docling 的渐进式优化中，你希望如何处理现有的多加载器架构？ → A: 保留现有加载器作为降级策略，Docling 作为主要解析器
- Q: 对于你列出的 20+ 种文档格式，在实施阶段应该按什么优先级顺序来支持？ → A: 分3批：第1批(PDF/DOCX/XLSX/PPTX)，第2批(HTML/CSV/TXT/MD)，第3批(其他格式)
- Q: 在 Docling 集成中，当遇到大文件（>50MB）或复杂文档时，系统应该如何平衡解析质量和性能？ → A: 基于文件大小和复杂度智能选择解析器（注：文档上传限制为50MB）
- Q: 当 Docling 解析失败时，系统应该如何处理用户体验？ → A: 自动降级到备用解析器并通知用户使用了备用方案
- Q: 在集成 Docling 后，解析结果的数据结构应该如何设计以支持不同解析器的输出？ → A: 设计统一的标准化数据结构，所有解析器输出都转换为此格式

## 背景

当前系统存在两个功能重叠的模块：
- **文档加载模块 (Loading)**: 负责读取文档内容、提取文本和元数据
- **文档解析模块 (Parsing)**: 基于加载结果进行二次处理（全文、分页、按标题等）

这两个模块功能高度重叠，文档解析模块实际上只是对加载结果的简单重组，增加了系统复杂度和用户操作步骤。本次优化将合并这两个模块，保留文档加载模块并增强其功能，移除冗余的文档解析模块，同时集成基于 Docling 的渐进式优化方案。

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

### User Story 2 - 集成 Docling 解析器 (Priority: P1)

系统需要集成 Docling 作为主要文档解析器，同时保留现有加载器作为降级策略，实现智能解析器选择机制。

**Why this priority**: 这是功能增强的核心，需要与解析模块移除同步进行。

**Independent Test**: 上传 PDF/DOCX 文档，验证系统优先使用 Docling 解析，失败时自动降级到备用解析器。

**Acceptance Scenarios**:

1. **Given** 系统集成了 Docling 解析器, **When** 上传 PDF 文档, **Then** 系统优先使用 Docling 进行解析
2. **Given** Docling 解析失败, **When** 系统检测到解析错误, **Then** 自动降级到 PyMuPDF 解析器并通知用户
3. **Given** 文档解析成功, **When** 查看解析结果, **Then** 所有解析器输出都转换为统一的标准化数据结构

---

### User Story 3 - 清理主程序和路由注册 (Priority: P1)

从 `main.py` 中移除文档解析模块的路由注册和相关导入，确保应用启动时不再加载解析模块。

**Why this priority**: 与 User Story 1 同等重要，是代码移除的必要步骤。

**Independent Test**: 检查 `main.py` 中不再包含 parsing 相关导入和路由注册。

**Acceptance Scenarios**:

1. **Given** `main.py` 包含 parsing 路由注册, **When** 移除相关代码, **Then** 应用正常启动且 API 文档中不显示 parsing 端点
2. **Given** 其他模块可能引用 parsing 服务, **When** 检查并移除所有引用, **Then** 无导入错误或运行时错误

---

### User Story 4 - 扩展格式支持 (Priority: P2)

按照分批策略扩展文档格式支持，第1批支持 PDF/DOCX/XLSX/PPTX，第2批支持 HTML/CSV/TXT/MD，第3批支持其他格式。

**Why this priority**: 格式扩展是渐进式优化的重要组成部分，需要在核心功能稳定后进行。

**Independent Test**: 上传各批次支持的文档格式，验证系统能正确识别并选择合适的解析器。

**Acceptance Scenarios**:

1. **Given** 第1批格式已实现, **When** 上传 XLSX 文档, **Then** 系统使用 Docling 解析并提取表格结构
2. **Given** 第2批格式已实现, **When** 上传 HTML 文档, **Then** 系统使用 HTML 解析器提取文本内容
3. **Given** 所有格式已支持, **When** 查看支持格式列表, **Then** 系统显示 20+ 种支持的文档格式

---

### User Story 5 - 更新项目文档 (Priority: P3)

更新所有相关的项目文档，移除文档解析模块的说明，添加 Docling 集成和新格式支持的描述。

**Why this priority**: 文档更新是代码改动后的必要步骤，确保开发者和用户获得准确信息。

**Independent Test**: 搜索所有文档，确认不再包含"文档解析"、"parsing"等相关描述，并包含 Docling 相关说明。

**Acceptance Scenarios**:

1. **Given** README.md 包含文档解析功能说明, **When** 更新文档移除相关内容, **Then** README 只描述增强的文档加载功能
2. **Given** 文档需要更新 Docling 集成说明, **When** 添加相关描述, **Then** 文档清晰说明多层级解析器策略
3. **Given** 格式支持列表需要更新, **When** 更新支持格式说明, **Then** 文档反映当前支持的所有格式

---

### User Story 6 - 更新前端界面（如有） (Priority: P3)

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
- 当 Docling 和所有备用解析器都失败时，系统如何处理？
- 当文档格式识别错误导致选择错误解析器时，如何自动纠正？

## Requirements *(mandatory)*

### Functional Requirements

#### 解析模块移除
- **FR-001**: 系统必须移除 `backend/src/api/parsing.py` 文件
- **FR-002**: 系统必须移除 `backend/src/services/parsing_service.py` 文件
- **FR-003**: 系统必须从 `backend/src/main.py` 中移除 parsing 相关的导入和路由注册
- **FR-004**: 系统必须检查并移除其他文件中对 parsing 模块的引用

#### Docling 集成
- **FR-005**: 系统必须集成 Docling 作为主要文档解析器
- **FR-006**: 系统必须实现多层级解析器降级策略：`["docling", "pymupdf", "unstructured"]`
- **FR-007**: 系统必须基于文件大小和复杂度智能选择解析器
- **FR-008**: 系统必须在解析失败时自动降级并通知用户使用了备用方案
- **FR-009**: 系统必须设计统一的标准化数据结构，所有解析器输出都转换为此格式

#### 格式扩展
- **FR-010**: 系统必须按分批策略扩展格式支持（第1批：PDF/DOCX/XLSX/PPTX）
- **FR-011**: 系统必须支持新增格式的专用解析器（CSV、JSON、HTML、XML、EPUB等）
- **FR-012**: 系统必须更新格式映射配置，支持多解析器降级策略

#### 文档更新
- **FR-013**: 系统必须更新 `README.md`，移除文档解析功能描述，添加 Docling 集成说明
- **FR-014**: 系统必须更新 `backend/README.md`，移除解析相关说明，添加新解析器架构描述
- **FR-015**: 系统必须检查 `documents/` 目录，更新或移除解析相关文档
- **FR-016**: 系统必须更新 `specs/001-document-processing/` 规格说明
- **FR-017**: 系统必须检查前端代码，移除解析相关的组件和 API 调用
- **FR-018**: 移除后，文档加载功能必须保持完整可用

### Key Entities

#### 待移除文件
- `backend/src/api/parsing.py` - 解析 API 路由
- `backend/src/services/parsing_service.py` - 解析服务实现

#### 待修改文件
- `backend/src/main.py` - 移除路由注册
- `README.md` - 更新功能说明
- `backend/README.md` - 更新后端说明
- `documents/` 目录下相关文档
- `specs/001-document-processing/` 规格文档

#### 新增解析器
- **DoclingLoader** - IBM Docling 解析器，支持高精度文档理解
- **CSVLoader** - CSV 文件解析器
- **JSONLoader** - JSON 文件解析器
- **HTMLLoader** - HTML 文档解析器
- **XMLLoader** - XML 文档解析器
- **EPUBLoader** - EPUB 电子书解析器
- **EmailLoader** - EML 邮件解析器
- **MSGLoader** - MSG 邮件解析器
- **PropertiesLoader** - Properties 配置文件解析器
- **VTTLoader** - VTT 字幕文件解析器

#### 增强的解析器选择策略

```python
extended_format_map = {
    # 现有格式优化（多层级降级）
    "pdf": ["docling", "pymupdf", "unstructured"],
    "docx": ["docling", "docx"],
    "pptx": ["docling", "unstructured"],
    "xlsx": ["docling", "pandas"],
    
    # 新增格式
    "csv": ["csv"],
    "json": ["json"],
    "html": ["html", "unstructured"],
    "htm": ["html", "unstructured"],
    "xml": ["xml", "unstructured"],
    "epub": ["epub"],
    "eml": ["email"],
    "msg": ["msg"],
    "properties": ["properties"],
    "vtt": ["vtt"],
    "xls": ["pandas", "unstructured"],
    "ppt": ["unstructured"],
    "doc": ["doc", "unstructured"],
    "markdown": ["text"],
    "mdx": ["text"],
}
```

#### 统一数据结构

```python
StandardDocumentResult = {
    "success": bool,
    "loader": str,
    "metadata": {
        "title": str,
        "author": str,
        "page_count": int,
        "file_size": int,
        "format": str,
        "created_time": datetime,
        "extraction_quality": float  # 0.0-1.0
    },
    "content": {
        "full_text": str,
        "pages": List[PageContent],
        "tables": List[TableContent],  # Docling 特有
        "images": List[ImageContent],  # 图片数据（含 base64）
        "formulas": List[FormulaContent]  # Docling 特有
    },
    "statistics": {
        "total_pages": int,
        "total_chars": int,
        "processing_time": float,
        "fallback_used": bool,
        "fallback_reason": str
    }
}
```

#### 图片数据结构（占位符 + 结构化元数据方案）

为支持多模态嵌入，图片采用占位符 + 结构化元数据方案：

**占位符格式（full_text 中）**：
```
[IMAGE_N: 图片描述]
```

**图片元数据结构（images 数组）**：
```python
ImageContent = {
    "image_index": int,           # 图片索引（对应占位符中的 N）
    "file_path": str,             # 图片文件路径（用于展示）
    "base64_data": str,           # Base64 编码数据（用于多模态嵌入）
    "mime_type": str,             # MIME 类型（image/png, image/jpeg 等）
    "alt_text": str,              # 替代文本/描述
    "caption": str,               # 图片标题
    "width": int,                 # 图片宽度
    "height": int,                # 图片高度
    "page_number": int,           # 所在页码
    "context_before": str,        # 图片前的上下文文本
    "context_after": str          # 图片后的上下文文本
}
```

**设计说明**：
- `embed_images_base64` 默认启用，确保图片数据包含 base64 编码
- 文本中保留占位符 `[IMAGE_N: 描述]`，保持文档结构清晰
- 分块器根据占位符匹配 images 数组，关联完整图片数据
- `file_path` 用于前端展示，`base64_data` 用于多模态嵌入

### Assumptions

- 文档上传限制为 50MB，无需处理超大文件场景
- 文档加载模块已具备足够的功能，无需从解析模块迁移任何功能
- Docling 库能够稳定运行并提供预期的解析质量
- 现有的文档加载模块架构足够灵活，可以集成新的解析器
- 数据库中的历史 parsing 处理结果可以保留，不影响系统运行
- 前端如有解析相关功能，可以直接移除而无需替代方案

## Success Criteria *(mandatory)*

### Measurable Outcomes

#### 代码移除成功指标
- **SC-001**: 后端服务启动无错误，所有非解析功能正常工作
- **SC-002**: 代码库中不存在 `parsing_service` 和 `parsing.py` 文件
- **SC-003**: 搜索代码库，"parsing" 相关引用仅存在于注释或历史记录中

#### Docling 集成成功指标
- **SC-004**: Docling 解析器成功集成，PDF/DOCX 文档解析质量提升至 95%+ 准确率
- **SC-005**: 多层级降级策略正常工作，解析失败时自动切换到备用解析器
- **SC-006**: 智能解析器选择机制根据文件特征选择最优解析器

#### 格式扩展成功指标
- **SC-007**: 第1批格式（PDF/DOCX/XLSX/PPTX）解析成功率达到 95%+
- **SC-008**: 系统支持的文档格式从 6 种扩展到 20+ 种
- **SC-009**: 所有新增格式都有对应的专用解析器和降级策略

#### 用户体验成功指标
- **SC-010**: 解析失败时用户能收到清晰的通知和备用方案说明
- **SC-011**: 所有解析结果都使用统一的数据结构，便于后续处理
- **SC-012**: API 文档 (`/docs`) 中不显示 parsing 相关端点，但显示增强的加载功能

#### 文档更新成功指标
- **SC-013**: 所有项目文档中不再描述"文档解析"作为独立功能模块
- **SC-014**: 文档清晰描述 Docling 集成和多层级解析器策略
- **SC-015**: 格式支持列表准确反映当前系统能力
