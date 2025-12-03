# 文档加载服务 - 完成说明

## ✅ 已完成的工作

### 1. 修复了 SQLAlchemy 模型问题

**问题**: Document 模型引用了不存在的 DocumentChunk 模型,导致应用启动失败。

**解决方案**:
- 创建了 `DocumentChunk` 模型 (`src/models/document_chunk.py`)
- 修复了模型间的关系引用,使用字符串引用避免循环导入
- 修复了索引名称冲突问题
- 将保留字段名 `metadata` 改为 `chunk_metadata`

### 2. 完善了文档加载服务

**文件**: `src/services/loading_service.py`

**新增功能**:
- ✅ 支持 PDF 文档解析为可处理的文本数据
- ✅ 页面级文本提取
- ✅ 字符统计和页面计数
- ✅ 完整的错误处理
- ✅ 状态跟踪 (processing, ready, error)
- ✅ 日志记录
- ✅ 支持多种加载器 (pymupdf, pypdf, unstructured)

**核心方法**:

```python
# 加载文档
result = loading_service.load_document(
    db=db,
    document_id="doc_id",
    loader_type="pymupdf"  # 默认使用 PyMuPDF
)

# 获取加载结果
data = loading_service.get_loading_result(
    db=db,
    document_id="doc_id"
)

# 获取可用的加载器列表
loaders = loading_service.get_available_loaders()
# 返回: ["pymupdf", "pypdf", "unstructured"]
```

### 3. 创建了数据库模型

#### Document (文档)
- 文档基本信息 (文件名、格式、大小等)
- 存储路径和内容哈希
- 状态跟踪 (uploaded, processing, ready, error)
- 关联的处理结果和文本块

#### DocumentChunk (文档块)
- 文本块内容和索引
- 字符统计
- 源页面信息
- 嵌入状态跟踪
- 附加元数据

#### ProcessingResult (处理结果)
- 处理类型和提供者
- 结果存储路径
- 状态和错误信息
- 时间戳

### 4. 数据库初始化

创建了数据库初始化脚本 `init_database.py`:

```bash
cd backend
source .venv/bin/activate
python init_database.py
```

## 📋 模型关系图

```
Document (documents)
  ├── ProcessingResult (processing_results) - 一对多
  └── DocumentChunk (document_chunks) - 一对多
```

## 🚀 使用指南

### 1. 启动后端服务

使用更新后的启动脚本(现在使用 uvicorn):

```bash
cd backend
./start_backend.sh
```

或者手动启动:

```bash
cd backend
source .venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. API 使用流程

#### Step 1: 上传文档
```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -F "file=@test.pdf"
```

返回:
```json
{
  "success": true,
  "data": {
    "id": "doc_uuid",
    "filename": "test.pdf",
    "format": "pdf",
    "status": "uploaded",
    ...
  }
}
```

#### Step 2: 加载文档
```bash
curl -X POST "http://localhost:8000/api/v1/processing/load/doc_uuid?loader=pymupdf"
```

返回:
```json
{
  "success": true,
  "data": {
    "id": "result_uuid",
    "status": "completed",
    "extra_metadata": {
      "total_pages": 10,
      "total_chars": 5000
    }
  }
}
```

#### Step 3: 查看加载结果
```bash
curl "http://localhost:8000/api/v1/processing/load/doc_uuid/results"
```

返回:
```json
{
  "success": true,
  "data": {
    "success": true,
    "total_pages": 10,
    "total_chars": 5000,
    "pages": [
      {
        "page_number": 1,
        "text": "页面内容...",
        "char_count": 500
      },
      ...
    ]
  }
}
```

## 📁 文件结构

```
backend/
├── src/
│   ├── models/
│   │   ├── __init__.py           # 导出所有模型
│   │   ├── document.py           # 文档模型 ✅
│   │   ├── document_chunk.py     # 文档块模型 ✅ (新建)
│   │   └── processing_result.py  # 处理结果模型 ✅
│   ├── services/
│   │   └── loading_service.py    # 加载服务 ✅ (完善)
│   ├── storage/
│   │   └── database.py           # 数据库配置
│   └── main.py                   # 应用入口 ✅
├── init_database.py              # 数据库初始化 ✅ (新建)
├── test_document_loading.py      # 测试脚本 ✅ (新建)
└── start_backend.sh              # 启动脚本 ✅ (已更新)
```

## 🔧 技术栈

- **FastAPI**: Web 框架
- **SQLAlchemy**: ORM
- **SQLite**: 数据库
- **Uvicorn**: ASGI 服务器
- **PyMuPDF/PyPDF/Unstructured**: PDF 解析器

## ✨ 核心特性

### 加载服务特性

1. **多加载器支持**
   - PyMuPDF (默认,速度快,准确度高)
   - PyPDF (备选)
   - Unstructured (高级解析)

2. **完整的错误处理**
   - 文档不存在检测
   - 文件格式验证
   - 加载失败回滚
   - 详细的错误信息

3. **状态管理**
   - uploaded → processing → ready
   - 失败时标记为 error
   - 完整的处理历史记录

4. **结果存储**
   - JSON 格式存储详细结果
   - 元数据提取
   - 页面级内容保存

## 🧪 测试

运行测试脚本:

```bash
cd backend
source .venv/bin/activate
python test_document_loading.py
```

## 📊 数据库模式

### documents 表
```sql
CREATE TABLE documents (
    id VARCHAR(36) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    format VARCHAR(50) NOT NULL,
    size_bytes INTEGER NOT NULL,
    upload_time DATETIME NOT NULL,
    storage_path VARCHAR NOT NULL,
    content_hash VARCHAR(64),
    status VARCHAR(20) NOT NULL DEFAULT 'uploaded'
);
```

### document_chunks 表
```sql
CREATE TABLE document_chunks (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    char_count INTEGER NOT NULL,
    source_pages JSON,
    chunk_metadata JSON,
    created_time DATETIME NOT NULL,
    embedding_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
```

### processing_results 表
```sql
CREATE TABLE processing_results (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL,
    processing_type VARCHAR(50) NOT NULL,
    provider VARCHAR(50),
    result_path VARCHAR NOT NULL,
    extra_metadata JSON,
    created_at DATETIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message VARCHAR,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
```

## 🎯 下一步

文档加载服务已经完成,后续可以继续开发:

1. **分块服务** (Chunking)
   - 将加载的文本分割成适当大小的块
   - 使用 DocumentChunk 模型存储

2. **嵌入服务** (Embedding)
   - 为文本块生成向量嵌入
   - 集成 OpenAI/本地嵌入模型

3. **索引服务** (Indexing)
   - 将向量存储到向量数据库
   - 支持快速相似度搜索

4. **搜索服务** (Search)
   - 语义搜索
   - 混合搜索(关键词+语义)

5. **生成服务** (Generation)
   - RAG 问答
   - 上下文生成

## 🐛 问题修复记录

### 问题 1: SQLAlchemy 映射错误
```
InvalidRequestError: One or more mappers failed to initialize - 
can't proceed with initialization of other mappers. 
Original exception was: When initializing mapper Mapper[Document(documents)], 
expression 'DocumentChunk' failed to locate a name ('DocumentChunk').
```

**原因**: DocumentChunk 模型未定义

**解决**: 创建了 DocumentChunk 模型并正确配置关系

### 问题 2: 保留字段名冲突
```
InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
```

**原因**: SQLAlchemy 的 Base 类有 metadata 属性

**解决**: 将字段名改为 `chunk_metadata`

### 问题 3: 索引名称冲突
```
OperationalError: index idx_document_id already exists
```

**原因**: 多个模型使用了相同的索引名

**解决**: 为每个表的索引添加唯一前缀

## 📝 日志示例

```
INFO: Starting document loading: doc_123 with pymupdf
INFO: Successfully loaded doc_123: 10 pages, 5000 characters
INFO: Document loading completed: doc_123
```

---

**状态**: ✅ 完成并测试通过
**创建时间**: 2025-12-03
**版本**: 1.0.0
