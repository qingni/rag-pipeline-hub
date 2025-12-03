# 文档加载器说明

## 概述

文档加载服务已优化,支持多种文档格式的文本提取,包括 PDF、DOC、DOCX、TXT 和 Markdown 文件。

## 支持的文件格式

### 1. PDF 文档
- **pymupdf** (默认): 使用 PyMuPDF 库,提供最佳性能和功能
- **pypdf**: 使用 PyPDF2 库,轻量级替代方案
- **unstructured**: 使用 Unstructured 库,支持更复杂的文档结构

### 2. DOCX 文档
- **docx**: 使用 python-docx 库
- 支持段落提取
- 支持表格提取
- 提取文档元数据(标题、作者、创建时间等)

### 3. DOC 文档 (旧版 Word 文档)
- **doc**: 多种提取方法
- 优先使用 antiword (命令行工具)
- 备用方案: python-docx 或 textract
- 建议转换为 DOCX 格式以获得更好的支持

### 4. 文本文档
- **text**: 支持纯文本和 Markdown 文件
- 支持格式: .txt, .md, .markdown
- 自动编码检测(UTF-8, GBK, GB2312, Latin-1)

## 安装依赖

### 基础依赖
```bash
pip install PyMuPDF PyPDF2 python-docx
```

### 可选依赖

**Unstructured (用于复杂文档结构)**:
```bash
pip install unstructured
```

**Textract (用于 DOC 文件提取)**:
```bash
pip install textract
```

**Antiword (推荐用于 DOC 文件)**:
```bash
# Linux
sudo apt-get install antiword

# macOS
brew install antiword
```

## API 使用

### 1. 上传文档
```bash
curl -X POST "http://localhost:8000/documents" \
  -F "file=@document.docx"
```

支持的文件扩展名:
- `.pdf`
- `.doc`
- `.docx`
- `.txt`
- `.md`
- `.markdown`

### 2. 加载文档 (自动选择 loader)
```bash
curl -X POST "http://localhost:8000/load" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "your-document-id"
  }'
```

系统会根据文件格式自动选择最合适的 loader。

### 3. 加载文档 (指定 loader)
```bash
curl -X POST "http://localhost:8000/load" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "your-document-id",
    "loader_type": "docx"
  }'
```

### 4. 获取可用的 loaders
```bash
curl -X GET "http://localhost:8000/loaders"
```

响应示例:
```json
{
  "success": true,
  "data": {
    "loaders": ["pymupdf", "pypdf", "unstructured", "text", "docx", "doc"],
    "supported_formats": ["pdf", "txt", "md", "markdown", "docx", "doc"],
    "format_loader_map": {
      "pdf": "pymupdf",
      "txt": "text",
      "md": "text",
      "markdown": "text",
      "docx": "docx",
      "doc": "doc"
    }
  }
}
```

### 5. 文档预览
```bash
curl -X GET "http://localhost:8000/documents/{document_id}/preview?pages=3"
```

预览功能现在支持所有文档格式,会自动选择合适的 loader。

## 文档加载结果格式

所有 loader 返回统一的数据结构:

```json
{
  "success": true,
  "loader": "docx",
  "metadata": {
    "title": "Document Title",
    "author": "Author Name",
    "paragraph_count": 45,
    "table_count": 3
  },
  "pages": [
    {
      "page_number": 1,
      "text": "Page content...",
      "char_count": 1234
    }
  ],
  "full_text": "Complete document text...",
  "total_pages": 1,
  "total_chars": 5678
}
```

## 格式特定说明

### PDF 文档
- 支持多页文档
- 提取完整的文档元数据
- 可选择不同的 loader 以获得最佳结果

### DOCX 文档
- 自动提取段落和表格
- 保留文档元数据
- 表格内容以 " | " 分隔

### DOC 文档
- 需要安装额外工具(antiword 或 textract)
- 建议转换为 DOCX 格式
- 提取质量取决于所用工具

### 文本/Markdown 文档
- 自动编码检测
- 保留原始格式
- 单页文档(page_number = 1)

## 错误处理

如果文档加载失败,系统会返回详细的错误信息:

```json
{
  "success": false,
  "loader": "doc",
  "error": "Unable to extract text from DOC file. Please install one of: antiword, textract..."
}
```

## 性能建议

1. **PDF 文档**: 优先使用 `pymupdf`,性能最佳
2. **DOCX 文档**: `python-docx` 提供可靠的提取
3. **DOC 文档**: 建议转换为 DOCX 格式
4. **大文件**: 考虑使用异步处理
5. **批量处理**: 使用队列系统管理多个文档

## 扩展新格式

要添加新的文档格式支持:

1. 在 `backend/src/providers/loaders/` 创建新的 loader
2. 实现 `extract_text()` 方法,返回标准格式
3. 在 `loading_service.py` 中注册 loader
4. 在 `validators.py` 中添加文件扩展名
5. 更新 `format_loader_map` 映射

示例 loader 结构:
```python
class CustomLoader:
    def __init__(self):
        self.name = "custom"
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        try:
            # 实现提取逻辑
            return {
                "success": True,
                "loader": self.name,
                "metadata": {},
                "pages": [],
                "full_text": "",
                "total_pages": 0,
                "total_chars": 0
            }
        except Exception as e:
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }
```

## 测试

确保所有 loader 正常工作:

```bash
# 运行单元测试
pytest backend/tests/test_loaders.py

# 测试特定格式
pytest backend/tests/test_loaders.py::test_docx_loader
```
