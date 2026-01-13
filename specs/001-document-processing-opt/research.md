# Research: 文档处理模块优化

**Feature**: 001-document-processing-opt  
**Date**: 2025-01-13

## 1. Docling 集成研究

### 1.1 Docling 概述

**Decision**: 使用 IBM Docling 作为主要文档解析器

**Rationale**:
- Docling 是 IBM 开源的企业级文档解析工具，专为生成式 AI 设计
- 复杂表格准确率达 97.9%，远超 Unstructured (75%)
- 支持 PDF、DOCX、PPTX、XLSX、HTML 等主流格式
- 提供结构化输出，包括表格、图像、公式等

**Alternatives considered**:
- Unstructured: 格式覆盖广但表格准确率较低 (75%)
- LlamaParse: 速度快但结构保真度较弱
- DeepDoc (RAGFlow): 自研方案，集成复杂度高

### 1.2 安装和配置

```bash
# 基础安装
pip install docling

# 完整安装（包含 OCR 支持）
pip install "docling[ocr]"
```

**依赖要求**:
- Python >= 3.9
- PyTorch (自动安装)
- 可选: Tesseract OCR (用于扫描文档)

### 1.3 API 使用方式

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("document.pdf")

# 获取 Markdown 格式输出
markdown_text = result.document.export_to_markdown()

# 获取结构化数据
for page in result.document.pages:
    for element in page.elements:
        if element.type == "table":
            # 处理表格
            pass
        elif element.type == "text":
            # 处理文本
            pass
```

### 1.4 输出格式映射

| Docling 输出 | 统一数据结构映射 |
|--------------|------------------|
| `document.export_to_markdown()` | `content.full_text` |
| `document.pages` | `content.pages` |
| `element.type == "table"` | `content.tables` |
| `element.type == "picture"` | `content.images` |
| `document.meta` | `metadata` |

### 1.5 性能基准

| 文档类型 | 大小 | Docling 耗时 | PyMuPDF 耗时 |
|----------|------|--------------|--------------|
| PDF (纯文本) | 1MB | ~2s | ~0.5s |
| PDF (含表格) | 5MB | ~10s | ~2s |
| PDF (复杂布局) | 10MB | ~20s | ~5s |
| DOCX | 2MB | ~3s | N/A |

**结论**: Docling 解析质量更高但速度较慢，适合作为主解析器；PyMuPDF 适合作为快速降级方案。

---

## 2. 格式支持研究

### 2.1 第一批格式 (PDF/DOCX/XLSX/PPTX)

| 格式 | 主解析器 | 降级解析器 | 依赖库 |
|------|----------|------------|--------|
| PDF | Docling | PyMuPDF, Unstructured | docling, PyMuPDF, unstructured |
| DOCX | Docling | python-docx | docling, python-docx |
| XLSX | Docling | openpyxl, pandas | docling, openpyxl, pandas |
| PPTX | Docling | python-pptx, Unstructured | docling, python-pptx, unstructured |

### 2.2 第二批格式 (HTML/CSV/TXT/MD)

| 格式 | 主解析器 | 降级解析器 | 依赖库 |
|------|----------|------------|--------|
| HTML/HTM | BeautifulSoup | Unstructured | beautifulsoup4, lxml |
| CSV | pandas | csv 模块 | pandas |
| TXT | 内置 open() | - | 无 |
| MD/MARKDOWN/MDX | markdown | mistune | markdown, mistune |

### 2.3 第三批格式 (其他)

| 格式 | 主解析器 | 降级解析器 | 依赖库 |
|------|----------|------------|--------|
| EPUB | ebooklib | Unstructured | ebooklib |
| EML | email 模块 | Unstructured | 内置 |
| MSG | extract-msg | Unstructured | extract-msg |
| XML | lxml | xml.etree | lxml |
| VTT | webvtt-py | 自定义解析 | webvtt-py |
| PROPERTIES | jproperties | 自定义解析 | jproperties |
| XLS | xlrd, pandas | Unstructured | xlrd, pandas |
| PPT | Unstructured | - | unstructured |
| DOC | 现有 doc_loader | Unstructured | antiword |

### 2.4 依赖安装清单

```bash
# 核心依赖
pip install docling PyMuPDF python-docx openpyxl python-pptx pandas

# 第二批格式
pip install beautifulsoup4 lxml markdown mistune

# 第三批格式
pip install ebooklib extract-msg webvtt-py jproperties xlrd

# 可选：Unstructured 作为通用降级
pip install "unstructured[all-docs]"
```

---

## 3. 降级策略研究

### 3.1 解析失败检测机制

**Decision**: 基于异常捕获和结果验证的双重检测

**检测条件**:
1. 解析器抛出异常
2. 返回结果 `success == False`
3. 提取文本为空或过短 (< 10 字符)
4. 处理超时 (默认 60s)

```python
def parse_with_fallback(file_path: str, format: str) -> Dict[str, Any]:
    strategies = format_strategy_map.get(format, ["text"])
    
    for parser_name in strategies:
        try:
            parser = get_parser(parser_name)
            result = parser.extract_text(file_path)
            
            # 验证结果
            if result.get("success") and len(result.get("full_text", "")) > 10:
                result["fallback_used"] = parser_name != strategies[0]
                result["fallback_reason"] = None if not result["fallback_used"] else f"Primary parser failed"
                return result
                
        except Exception as e:
            logger.warning(f"Parser {parser_name} failed: {e}")
            continue
    
    raise ProcessingError("All parsers failed")
```

### 3.2 降级顺序配置

```python
format_strategy_map = {
    # 第一批：Docling 优先
    "pdf": ["docling", "pymupdf", "unstructured"],
    "docx": ["docling", "docx", "unstructured"],
    "xlsx": ["docling", "xlsx", "pandas", "unstructured"],
    "pptx": ["docling", "pptx", "unstructured"],
    
    # 第二批：专用解析器优先
    "html": ["html", "unstructured"],
    "htm": ["html", "unstructured"],
    "csv": ["csv", "pandas"],
    "txt": ["text"],
    "md": ["text"],
    "markdown": ["text"],
    "mdx": ["text"],
    
    # 第三批：专用解析器
    "epub": ["epub", "unstructured"],
    "eml": ["email", "unstructured"],
    "msg": ["msg", "unstructured"],
    "xml": ["xml", "unstructured"],
    "vtt": ["vtt"],
    "properties": ["properties"],
    "xls": ["pandas", "unstructured"],
    "ppt": ["unstructured"],
    "doc": ["doc", "unstructured"],
}
```

### 3.3 用户通知方式

**Decision**: 在响应中包含降级信息，前端显示提示

**响应格式**:
```json
{
  "success": true,
  "loader": "pymupdf",
  "statistics": {
    "fallback_used": true,
    "fallback_reason": "Docling 解析失败: OCR 模块不可用",
    "original_parser": "docling"
  }
}
```

**前端提示**:
- 成功 + 无降级: 绿色提示 "文档解析成功"
- 成功 + 有降级: 黄色提示 "文档解析成功（使用备用解析器）"
- 失败: 红色提示 "文档解析失败，请检查文件格式"

---

## 4. 智能解析器选择研究

### 4.1 选择策略

**Decision**: 基于文件大小和格式的智能选择

```python
def select_optimal_parser(file_path: str, format: str, file_size: int) -> str:
    """根据文件特征选择最佳解析器"""
    
    # 获取该格式的解析器列表
    strategies = format_strategy_map.get(format, ["text"])
    
    # 对于 PDF 格式，根据文件大小选择
    if format == "pdf":
        if file_size > 20 * 1024 * 1024:  # > 20MB
            # 大文件优先使用 PyMuPDF（更快）
            return "pymupdf"
        else:
            # 小文件使用 Docling（更精确）
            return "docling"
    
    # 其他格式使用默认策略（第一个解析器）
    return strategies[0]
```

### 4.2 复杂度检测（可选增强）

未来可增加基于文档复杂度的选择：
- 检测是否包含表格
- 检测是否包含图像
- 检测是否为扫描件

---

## 5. 统一数据结构研究

### 5.1 结构设计

**Decision**: 设计通用的 StandardDocumentResult 结构

详见 [data-model.md](./data-model.md)

### 5.2 各解析器输出映射

| 解析器 | 原始输出 | 映射方式 |
|--------|----------|----------|
| Docling | DoclingDocument | 直接映射 pages, tables, images |
| PyMuPDF | Dict with pages | 转换为 PageContent 列表 |
| python-docx | Document 对象 | 提取段落转换为 pages |
| pandas (CSV/XLSX) | DataFrame | 转换为单页 + 表格数据 |
| BeautifulSoup | Tag 树 | 提取文本转换为单页 |

---

## 6. 总结

### 关键决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 主解析器 | Docling | 表格准确率 97.9%，结构化输出 |
| 降级策略 | 多层级顺序降级 | 确保解析成功率 |
| 数据结构 | 统一 StandardDocumentResult | 便于下游处理 |
| 用户通知 | 响应中包含降级信息 | 透明化处理过程 |

### 风险和缓解

| 风险 | 缓解措施 |
|------|----------|
| Docling 安装复杂 | 提供详细安装文档，可选安装 |
| 大文件处理慢 | 智能选择快速解析器 |
| 新格式解析失败 | Unstructured 作为通用降级 |

### 下一步

1. 创建 data-model.md 定义统一数据结构
2. 创建 contracts/loading-api.yaml 定义 API 契约
3. 创建 quickstart.md 提供快速开始指南
