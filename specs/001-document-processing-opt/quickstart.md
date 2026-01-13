# Quick Start: 文档处理模块优化

**Feature**: 001-document-processing-opt  
**Date**: 2025-01-13

## 1. 环境准备

### 1.1 安装核心依赖

```bash
cd backend

# 安装 Docling（主解析器）
pip install docling

# 安装第一批格式支持
pip install PyMuPDF python-docx openpyxl python-pptx

# 安装第二批格式支持
pip install beautifulsoup4 lxml markdown pandas

# 安装第三批格式支持
pip install ebooklib extract-msg webvtt-py jproperties xlrd

# 可选：Unstructured 作为通用降级
pip install "unstructured[all-docs]"
```

### 1.2 验证安装

```python
# 验证 Docling 安装
python -c "from docling.document_converter import DocumentConverter; print('Docling OK')"

# 验证 PyMuPDF 安装
python -c "import fitz; print('PyMuPDF OK')"
```

## 2. 快速测试

### 2.1 启动后端服务

```bash
cd backend
python -m uvicorn src.main:app --reload --port 8000
```

### 2.2 测试文档加载 API

```bash
# 上传文档
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@test.pdf"

# 加载文档（自动选择解析器）
curl -X POST "http://localhost:8000/api/v1/load/{document_id}"

# 加载文档（指定 Docling）
curl -X POST "http://localhost:8000/api/v1/load/{document_id}?loader_type=docling"

# 获取加载结果
curl "http://localhost:8000/api/v1/load/{document_id}/result"
```

### 2.3 查看可用加载器

```bash
# 获取所有加载器
curl "http://localhost:8000/api/v1/loaders"

# 获取支持的格式
curl "http://localhost:8000/api/v1/loaders/formats"
```

## 3. 代码示例

### 3.1 使用增强的 LoadingService

```python
from src.services.loading_service import loading_service
from sqlalchemy.orm import Session

# 自动选择最佳解析器
result = loading_service.load_document(
    db=session,
    document_id="your-document-id"
)

# 指定使用 Docling
result = loading_service.load_document(
    db=session,
    document_id="your-document-id",
    loader_type="docling"
)

# 检查是否使用了降级
if result.extra_metadata.get("fallback_used"):
    print(f"使用了降级解析器: {result.provider}")
    print(f"原因: {result.extra_metadata.get('fallback_reason')}")
```

### 3.2 直接使用 Docling 加载器

```python
from src.providers.loaders.docling_loader import docling_loader

# 解析 PDF
result = docling_loader.extract_text("document.pdf")

if result["success"]:
    print(f"解析器: {result['loader']}")
    print(f"页数: {result['statistics']['total_pages']}")
    print(f"表格数: {result['statistics']['table_count']}")
    
    # 访问表格数据
    for table in result["content"]["tables"]:
        print(f"表格 {table['table_index']}: {table['headers']}")
```

### 3.3 自定义降级策略

```python
from src.services.loading_service import LoadingService

class CustomLoadingService(LoadingService):
    def __init__(self):
        super().__init__()
        
        # 自定义格式策略
        self.format_strategy_map["pdf"] = ["pymupdf", "docling", "unstructured"]
```

## 4. 前端集成

### 4.1 调用加载 API

```javascript
// services/documentService.js
export async function loadDocument(documentId, loaderType = null) {
  const params = loaderType ? `?loader_type=${loaderType}` : '';
  const response = await api.post(`/load/${documentId}${params}`);
  return response.data;
}

export async function getLoadingResult(documentId) {
  const response = await api.get(`/load/${documentId}/result`);
  return response.data;
}
```

### 4.2 显示降级通知

```vue
<template>
  <div>
    <t-alert
      v-if="result.statistics?.fallback_used"
      theme="warning"
      message="文档使用备用解析器解析"
      :description="result.statistics.fallback_reason"
    />
    
    <t-alert
      v-else-if="result.success"
      theme="success"
      message="文档解析成功"
    />
  </div>
</template>
```

## 5. 支持的格式

### 5.1 第一批（核心格式）

| 格式 | 主解析器 | 降级解析器 |
|------|----------|------------|
| PDF | Docling | PyMuPDF → Unstructured |
| DOCX | Docling | python-docx → Unstructured |
| XLSX | Docling | openpyxl → pandas |
| PPTX | Docling | python-pptx → Unstructured |

### 5.2 第二批（常用格式）

| 格式 | 主解析器 | 降级解析器 |
|------|----------|------------|
| HTML/HTM | BeautifulSoup | Unstructured |
| CSV | pandas | csv 模块 |
| TXT | 内置 | - |
| MD/MARKDOWN | markdown | - |

### 5.3 第三批（扩展格式）

| 格式 | 主解析器 | 降级解析器 |
|------|----------|------------|
| EPUB | ebooklib | Unstructured |
| EML | email 模块 | Unstructured |
| MSG | extract-msg | Unstructured |
| XML | lxml | xml.etree |
| VTT | webvtt-py | - |
| PROPERTIES | jproperties | - |
| XLS | xlrd | pandas |
| PPT | Unstructured | - |
| DOC | antiword | Unstructured |

## 6. 故障排除

### 6.1 Docling 安装失败

```bash
# 尝试使用 conda 安装
conda install -c conda-forge docling

# 或者跳过 Docling，使用其他解析器
# 系统会自动降级到 PyMuPDF
```

### 6.2 OCR 功能不可用

```bash
# 安装 Tesseract OCR
# macOS
brew install tesseract

# Ubuntu
sudo apt-get install tesseract-ocr

# 安装 Docling OCR 支持
pip install "docling[ocr]"
```

### 6.3 大文件处理超时

```python
# 调整超时设置
loading_service.timeout = 120  # 秒

# 或者强制使用快速解析器
result = loading_service.load_document(
    db=session,
    document_id=doc_id,
    loader_type="pymupdf"  # 跳过 Docling
)
```

## 7. 下一步

1. 运行测试验证功能：`pytest tests/unit/loaders/`
2. 查看 API 文档：`http://localhost:8000/docs`
3. 阅读完整规格：[spec.md](./spec.md)
4. 查看数据模型：[data-model.md](./data-model.md)
