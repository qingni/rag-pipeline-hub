# Implementation Plan: 文档处理模块优化 - 合并加载与解析

**Branch**: `001-document-processing-opt` | **Date**: 2025-01-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-document-processing-opt/spec.md`

## Summary

本次优化将合并文档加载和解析模块，移除冗余的解析模块，同时集成 Docling 作为主要文档解析器，实现多层级降级策略和智能解析器选择机制。系统将从支持 6 种格式扩展到 20+ 种格式，并设计统一的标准化数据结构。

## Technical Context

**Language/Version**: Python 3.11 (后端) + JavaScript ES2020+ (前端)  
**Primary Dependencies**: FastAPI 0.104.1, Docling, PyMuPDF, python-docx, openpyxl, python-pptx, pandas, BeautifulSoup4, ebooklib, Vue 3, Vite, TDesign Vue Next  
**Storage**: SQLite/PostgreSQL (元数据) + JSON (结果持久化)  
**Testing**: pytest  
**Target Platform**: Linux/macOS 服务器  
**Project Type**: Web 应用 (前后端分离)  
**Performance Goals**: 文档解析成功率 95%+，单文档处理时间 < 30s (50MB 以内)  
**Constraints**: 文档上传限制 50MB，解析失败时自动降级  
**Scale/Scope**: 支持 20+ 种文档格式，多层级解析器降级策略

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 | 状态 | 说明 |
|------|------|------|
| **I. 模块化架构** | ✅ 通过 | 新增 DoclingLoader 等解析器遵循现有模块化设计，每个加载器独立实现 |
| **II. 多提供商支持** | ✅ 通过 | 扩展加载器支持 Docling、PyMuPDF、Unstructured 等多种提供商 |
| **III. 结果持久化** | ✅ 通过 | 所有解析结果保存为 JSON 格式，命名规范：文档名_时间戳.json |
| **IV. 用户体验优先** | ✅ 通过 | 解析失败时通知用户并自动降级，提供清晰的状态反馈 |
| **V. API 标准化** | ✅ 通过 | 移除 parsing API，增强 loading API，统一响应格式 |

**Gate 结果**: ✅ 通过，无违规项

## Project Structure

### Documentation (this feature)

```text
specs/001-document-processing-opt/
├── plan.md              # This file
├── research.md          # Phase 0 output - Docling 集成研究
├── data-model.md        # Phase 1 output - 统一数据结构定义
├── quickstart.md        # Phase 1 output - 快速开始指南
├── contracts/           # Phase 1 output - API 契约
│   └── loading-api.yaml # 增强的加载 API 定义
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   └── loading.py           # 增强的加载 API (修改)
│   ├── models/
│   │   └── loading_result.py    # 统一数据结构 (新增)
│   ├── services/
│   │   └── loading_service.py   # 增强的加载服务 (修改)
│   └── providers/
│       └── loaders/
│           ├── __init__.py      # 加载器注册 (修改)
│           ├── docling_loader.py    # Docling 加载器 (新增)
│           ├── csv_loader.py        # CSV 加载器 (新增)
│           ├── json_loader.py       # JSON 加载器 (新增)
│           ├── html_loader.py       # HTML 加载器 (新增)
│           ├── xml_loader.py        # XML 加载器 (新增)
│           ├── properties_loader.py # Properties 加载器 (新增)
│           ├── xlsx_loader.py       # XLSX 加载器 (新增)
│           ├── pptx_loader.py       # PPTX 加载器 (新增)
│           └── [existing loaders]   # 现有加载器保留
└── tests/
    └── unit/
        └── loaders/             # 加载器单元测试 (新增)

frontend/
├── src/
│   ├── views/
│   │   └── DocumentLoad.vue     # 文档加载页面 (修改)
│   └── services/
│       └── documentService.js   # 文档服务 (修改)
└── tests/
```

**Structure Decision**: 采用现有的 Web 应用结构，在 `backend/src/providers/loaders/` 目录下新增加载器实现，遵循现有的模块化设计模式。

## Complexity Tracking

> **无违规项，无需记录**

---

## Phase 0: Outline & Research

### 研究任务

1. **Docling 集成研究**
   - Docling 安装和配置要求
   - Docling API 使用方式和输出格式
   - Docling 与现有加载器的兼容性
   - Docling 性能基准测试

2. **格式支持研究**
   - 各格式最佳解析库选择
   - 解析库依赖和安装要求
   - 格式识别和自动选择策略

3. **降级策略研究**
   - 解析失败检测机制
   - 降级顺序和条件
   - 用户通知方式

### 输出

详见 [research.md](./research.md)

---

## Phase 1: Design & Contracts

### 数据模型

详见 [data-model.md](./data-model.md)

### API 契约

详见 [contracts/loading-api.yaml](./contracts/loading-api.yaml)

### 快速开始

详见 [quickstart.md](./quickstart.md)
