# 文档加载功能优化记录

## 更新日期
2025-12-03

## 概述
扩展了文档加载服务,新增对 DOC、DOCX、TXT 和 Markdown 格式的支持,并实现了智能加载器自动选择功能。

## 新增功能

### 1. 新增文档加载器

#### Text Loader (`text_loader.py`)
- **支持格式**: `.txt`, `.md`, `.markdown`
- **特性**:
  - 多编码自动检测 (UTF-8, GBK, GB2312, Latin-1)
  - 保留原始文本格式
  - 提供行数统计
  - 文件元数据提取

#### DOCX Loader (`docx_loader.py`)
- **支持格式**: `.docx`
- **特性**:
  - 段落文本提取
  - 表格内容提取
  - 文档元数据 (标题、作者、创建时间等)
  - 段落和表格计数
- **依赖**: `python-docx==1.1.0`

#### DOC Loader (`doc_loader.py`)
- **支持格式**: `.doc`
- **特性**:
  - 多种提取方法支持
  - 优先级: antiword > python-docx > textract
  - 详细的错误提示和安装指导
- **依赖**: 
  - `antiword` (推荐, 命令行工具)
  - `textract==1.6.5` (备选)

### 2. 智能加载器选择

#### 自动格式映射
系统会根据文件扩展名自动选择最佳加载器:

```python
format_loader_map = {
    "pdf": "pymupdf",      # 高性能 PDF 解析
    "txt": "text",         # 文本文件
    "md": "text",          # Markdown 文件
    "markdown": "text",    # Markdown 文件
    "docx": "docx",        # Word 2007+ 文档
    "doc": "doc"           # 旧版 Word 文档
}
```

#### API 改进
- `loader_type` 参数现在是可选的
- 当不指定 `loader_type` 时,系统自动选择最佳加载器
- 新增 `/loaders` 端点查询可用加载器和支持格式

### 3. 后端优化

#### LoadingService 新方法
```python
# 获取支持的文件格式
get_supported_formats() -> List[str]

# 获取特定格式的默认加载器
get_loader_for_format(file_format: str) -> Optional[str]
```

#### 统一返回格式
所有加载器返回一致的数据结构:
```json
{
  "success": true/false,
  "loader": "loader_name",
  "metadata": {...},
  "pages": [...],
  "full_text": "...",
  "total_pages": 1,
  "total_chars": 1234,
  "error": "..." // 仅在失败时
}
```

### 4. 前端优化

#### DocumentUploader.vue
- 支持新文件格式: `.md`, `.markdown`
- 更新文件类型提示
- 更新验证逻辑

#### DocumentLoad.vue
- 新增自动选择选项 (默认)
- 分组显示不同类型的加载器
- 为每个加载器添加说明文本
- 支持格式特定的提示信息

### 5. 文档预览增强

#### documents.py API
- 预览功能现在支持所有文档格式
- 自动选择合适的加载器进行预览
- 返回加载器信息和详细统计

## 文件变更清单

### 新增文件
1. `backend/src/providers/loaders/text_loader.py` - 文本/Markdown 加载器
2. `backend/src/providers/loaders/docx_loader.py` - DOCX 加载器
3. `backend/src/providers/loaders/doc_loader.py` - DOC 加载器
4. `backend/DOCUMENT_LOADERS.md` - 加载器使用文档
5. `backend/tests/test_new_loaders.py` - 新加载器测试

### 修改文件
1. `backend/src/services/loading_service.py`
   - 添加新加载器注册
   - 添加格式映射
   - 实现自动选择逻辑
   - 添加新的辅助方法

2. `backend/src/api/loading.py`
   - `loader_type` 改为可选参数
   - 添加 `/loaders` 端点
   - 更新 API 文档

3. `backend/src/api/documents.py`
   - 增强预览功能
   - 支持多格式预览
   - 返回更详细的统计信息

4. `backend/src/utils/validators.py`
   - 扩展允许的文件扩展名
   - 添加 `.md`, `.markdown` 支持

5. `backend/src/providers/loaders/__init__.py`
   - 导出新加载器
   - 更新 `__all__`

6. `backend/requirements.txt`
   - 添加 `python-docx==1.1.0`
   - 添加 `textract==1.6.5`

7. `frontend/src/components/document/DocumentUploader.vue`
   - 支持新文件格式
   - 更新文件类型提示
   - 更新验证逻辑

8. `frontend/src/views/DocumentLoad.vue`
   - 添加自动选择选项
   - 重新组织加载器选项
   - 添加加载器说明

## 依赖安装

### Python 依赖
```bash
# 基础依赖
pip install python-docx==1.1.0

# 可选: 用于 DOC 文件
pip install textract==1.6.5
```

### 系统工具 (可选)
```bash
# Linux
sudo apt-get install antiword

# macOS
brew install antiword
```

## 测试方法

### 运行新的测试
```bash
cd backend
pytest tests/test_new_loaders.py -v
```

### 测试 API
```bash
# 获取支持的加载器
curl http://localhost:8000/loaders

# 使用自动选择
curl -X POST http://localhost:8000/load \
  -H "Content-Type: application/json" \
  -d '{"document_id": "your-id"}'

# 指定加载器
curl -X POST http://localhost:8000/load \
  -H "Content-Type: application/json" \
  -d '{"document_id": "your-id", "loader_type": "docx"}'
```

## 兼容性说明

### 向后兼容
- 现有的 PDF 加载功能完全保持不变
- 旧的 API 调用方式仍然有效
- 默认的 PDF 加载器仍然是 `pymupdf`

### 推荐使用
- 对于 PDF: 使用自动选择或 `pymupdf`
- 对于 DOCX: 自动选择会使用 `docx`
- 对于 DOC: 建议转换为 DOCX 格式
- 对于文本/Markdown: 自动选择会使用 `text`

## 性能考虑

1. **PDF 文档**: `pymupdf` 性能最佳,建议大文件使用
2. **DOCX 文档**: `python-docx` 稳定可靠
3. **DOC 文档**: 
   - `antiword` 速度最快 (需单独安装)
   - `textract` 作为备选
   - 大量 DOC 文件建议批量转换为 DOCX
4. **文本文件**: 直接读取,性能最佳

## 错误处理

所有加载器都实现了统一的错误处理:
- 返回明确的错误信息
- 提供依赖安装指导
- 在日志中记录详细错误

## 后续优化建议

1. **批量处理**: 实现批量文档加载队列
2. **缓存机制**: 缓存已加载的文档结果
3. **格式转换**: 添加文档格式转换功能
4. **增量加载**: 大文件支持分页加载
5. **异步处理**: 大文件使用后台任务处理
6. **更多格式**: 支持 RTF, ODT 等其他格式

## 相关文档

- [文档加载器详细说明](backend/DOCUMENT_LOADERS.md)
- [API 文档](backend/API.md)
- [测试文档](backend/tests/README.md)
