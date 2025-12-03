# 快速开始 - 新文档加载器

## 🚀 立即使用

### 1. 安装依赖

```bash
cd backend

# 安装基础依赖 (必需)
pip install python-docx==1.1.0

# 安装可选依赖 (用于DOC文件)
pip install textract==1.6.5

# 或安装系统工具 (推荐用于DOC)
# macOS:
brew install antiword

# Linux:
sudo apt-get install antiword
```

### 2. 上传文档

现在支持的格式:
- ✅ PDF
- ✅ DOCX (Word 2007+)
- ✅ DOC (旧版 Word)
- ✅ TXT
- ✅ Markdown (.md, .markdown)

**方法1: 通过前端界面**
1. 启动前端: `cd frontend && npm run dev`
2. 访问文档加载页面
3. 拖拽或选择文件上传
4. 系统会自动选择最佳加载器

**方法2: 通过API**
```bash
# 上传文档
curl -X POST "http://localhost:8000/documents" \
  -F "file=@你的文档.docx"
```

### 3. 加载文档

**自动选择加载器 (推荐)**:
```bash
curl -X POST "http://localhost:8000/load" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "你的文档ID"
  }'
```

系统会根据文件格式自动选择:
- PDF → pymupdf
- DOCX → docx
- DOC → doc
- TXT/MD → text

**手动指定加载器**:
```bash
curl -X POST "http://localhost:8000/load" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "你的文档ID",
    "loader_type": "docx"
  }'
```

### 4. 查看支持的格式

```bash
curl http://localhost:8000/loaders
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

## 📝 示例代码

### Python 示例

```python
from src.services.loading_service import loading_service
from src.storage.database import get_db

# 获取数据库会话
db = next(get_db())

# 方式1: 自动选择加载器
result = loading_service.load_document(
    db=db,
    document_id="your-document-id"
)

# 方式2: 指定加载器
result = loading_service.load_document(
    db=db,
    document_id="your-document-id",
    loader_type="docx"
)

# 查看结果
print(f"加载状态: {result.status}")
print(f"总页数: {result.extra_metadata.get('total_pages')}")
print(f"总字符: {result.extra_metadata.get('total_chars')}")
```

### JavaScript 示例 (前端)

```javascript
// stores/processing.js
export const useProcessingStore = defineStore('processing', () => {
  async function loadDocument(documentId, loaderType = null) {
    const response = await fetch('/load', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        document_id: documentId,
        loader_type: loaderType // null 为自动选择
      })
    })
    
    return await response.json()
  }
  
  return { loadDocument }
})
```

## 🧪 测试

### 运行测试脚本

```bash
cd backend
python examples/test_loaders.py
```

输出示例:
```
============================================================
文档加载器测试工具
============================================================

============================================================
测试加载服务
============================================================

可用的加载器:
  - pymupdf
  - pypdf
  - unstructured
  - text
  - docx
  - doc

支持的文件格式:
  - .pdf -> pymupdf
  - .txt -> text
  - .md -> text
  - .markdown -> text
  - .docx -> docx
  - .doc -> doc

...
```

### 单元测试

```bash
# 需要先安装 pytest
pip install pytest

# 运行测试
pytest tests/test_new_loaders.py -v
```

## 📖 格式特定说明

### TXT 文件
```python
# 自动编码检测
# 支持: UTF-8, GBK, GB2312, Latin-1
result = text_loader.extract_text("document.txt")
```

### Markdown 文件
```python
# 与TXT使用相同的加载器
# 保留原始Markdown格式
result = text_loader.extract_text("README.md")
```

### DOCX 文件
```python
# 自动提取段落和表格
# 包含文档元数据
result = docx_loader.extract_text("document.docx")

# 访问元数据
metadata = result['metadata']
print(f"作者: {metadata.get('author')}")
print(f"段落数: {metadata.get('paragraph_count')}")
```

### DOC 文件
```python
# 需要额外工具支持
# 优先使用 antiword
result = doc_loader.extract_text("document.doc")

# 如果失败,会返回详细的错误信息
if not result['success']:
    print(result['error'])  # 包含安装指导
```

## ⚡ 常见问题

### Q1: DOC 文件加载失败?
**A:** DOC 格式需要额外工具:
```bash
# 安装 antiword (推荐)
brew install antiword  # macOS
sudo apt-get install antiword  # Linux

# 或安装 textract
pip install textract
```

### Q2: 如何知道使用了哪个加载器?
**A:** 检查结果中的 `loader` 字段:
```python
result = loading_service.load_document(db, doc_id)
print(f"使用的加载器: {result.extra_metadata.get('loader_type')}")
```

### Q3: 可以批量加载文档吗?
**A:** 当前支持单个文档加载,批量功能在开发计划中。临时方案:
```python
for doc_id in document_ids:
    result = loading_service.load_document(db, doc_id)
    # 处理结果
```

### Q4: 大文件加载很慢?
**A:** 建议:
1. 使用性能最佳的加载器 (PDF用pymupdf)
2. 考虑异步处理
3. 大文件考虑分块处理

## 🎯 最佳实践

1. **自动选择优先**: 让系统自动选择加载器,除非有特殊需求

2. **DOC转DOCX**: 如果处理大量DOC文件,建议预先转换为DOCX格式

3. **错误处理**: 总是检查 `success` 字段
   ```python
   result = loader.extract_text(file_path)
   if result['success']:
       # 处理文本
       text = result['full_text']
   else:
       # 处理错误
       print(f"错误: {result['error']}")
   ```

4. **编码问题**: 文本文件如果编码错误,text_loader会自动尝试多种编码

5. **元数据利用**: 使用元数据进行文档分类和索引
   ```python
   metadata = result['metadata']
   # 可用于文档管理、搜索等
   ```

## 📚 更多信息

- [详细文档](backend/DOCUMENT_LOADERS.md)
- [API文档](backend/API.md)
- [完整变更记录](DOCUMENT_LOADING_OPTIMIZATION.md)
- [变更总结](CHANGES_SUMMARY.md)

## 🆘 获取帮助

遇到问题?
1. 查看 [详细文档](backend/DOCUMENT_LOADERS.md)
2. 运行测试脚本诊断: `python examples/test_loaders.py`
3. 检查日志文件: `logs/`

---

**更新时间**: 2025-12-03  
**版本**: 1.0.0
