# 文档加载服务 - 完整指南

## 目录

- [一、核心功能概述](#一核心功能概述)
- [二、前后台完整交互流程](#二前后台完整交互流程)
- [三、核心代码解析](#三核心代码解析)
- [四、数据存储结构](#四数据存储结构)
- [五、支持的加载器](#五支持的加载器)
- [六、状态流转](#六状态流转)
- [七、实际使用示例](#七实际使用示例)
- [八、技术实现细节](#八技术实现细节)
- [九、不同格式文档的加载示例](#九不同格式文档的加载示例)
- [十、问题修复记录](#十问题修复记录)
- [十一、总结与下一步](#十一总结与下一步)

---

## 一、核心功能概述

### 1.1 什么是文档加载服务?

**简单来说**: 文档加载服务就是把 PDF 文件"读懂"并转换成程序可以处理的文本数据。

### 1.2 为什么需要这个服务?

假设你有一个 PDF 文档《提问的智慧.pdf》:
- PDF 是二进制格式,计算机程序无法直接理解内容
- 需要"解析"PDF,提取出里面的文字
- 提取后的文字可以用于搜索、问答、分析等

### 1.3 具体做什么?

```
输入: 一个 PDF 文件 (提问的智慧.pdf)
                ↓
         【加载服务处理】
                ↓
输出: 结构化的文本数据
     {
       "total_pages": 19,           // 总共19页
       "total_chars": 21772,        // 总共21772个字符
       "pages": [
         {
           "page_number": 1,        // 第1页
           "text": "提问的智慧...", // 该页的文字内容
           "char_count": 617        // 该页字符数
         },
         {
           "page_number": 2,
           "text": "描述问题症状...",
           "char_count": 570
         },
         ...
       ]
     }
```

### 1.4 已实现的功能

- ✅ 支持多种文档格式解析为可处理的文本数据
  - PDF: pymupdf (默认), pypdf, unstructured
  - Word: docx, doc
  - 文本: txt, markdown
- ✅ 页面级文本提取（支持多页文档）
- ✅ 字符统计和页面计数
- ✅ 完整的错误处理
- ✅ 状态跟踪 (uploaded, processing, ready, error)
- ✅ 日志记录
- ✅ 自动加载器选择（根据文件格式）
- ✅ 文档预览功能
- ✅ 文件去重检测

---

## 二、前后台完整交互流程

### 场景: 用户上传一个 PDF 并获取解析结果

```
┌─────────────┐                  ┌─────────────┐                  ┌─────────────┐
│   前端页面   │                  │  后端 API   │                  │  数据库      │
│  (Vue.js)   │                  │  (FastAPI)  │                  │  (SQLite)   │
└─────────────┘                  └─────────────┘                  └─────────────┘
      │                                 │                                 │
      │                                 │                                 │
      
═════════════════════════════════════════════════════════════════════════════════
第一步: 上传文档
═════════════════════════════════════════════════════════════════════════════════
      │                                 │                                 │
      │  1. 用户选择 PDF 文件            │                                 │
      │     点击"上传"按钮               │                                 │
      │                                 │                                 │
      │  POST /api/v1/documents         │                                 │
      │  文件: 提问的智慧.pdf            │                                 │
      ├────────────────────────────────>│                                 │
      │                                 │                                 │
      │                                 │  2. 保存文件到硬盘                │
      │                                 │     uploads/提问的智慧.pdf        │
      │                                 │                                 │
      │                                 │  3. 计算文件哈希值                │
      │                                 │                                 │
      │                                 │  4. 创建 Document 记录           │
      │                                 ├────────────────────────────────>│
      │                                 │   INSERT INTO documents         │
      │                                 │   (id, filename, status...)     │
      │                                 │                                 │
      │                                 │<────────────────────────────────┤
      │                                 │   返回 document_id: "abc-123"   │
      │                                 │                                 │
      │  返回文档信息                     │                                 │
      │  {                              │                                 │
      │    "id": "abc-123",             │                                 │
      │    "filename": "提问的智慧.pdf", │                                 │
      │    "status": "uploaded"         │                                 │
      │  }                              │                                 │
      │<────────────────────────────────┤                                 │
      │                                 │                                 │
      │  5. 页面显示上传成功              │                                 │
      │     文档ID: abc-123             │                                 │
      │                                 │                                 │

═════════════════════════════════════════════════════════════════════════════════
第二步: 加载文档(核心步骤)
═════════════════════════════════════════════════════════════════════════════════
      │                                 │                                 │
      │  6. 用户点击"解析文档"按钮        │                                 │
      │                                 │                                 │
      │  POST /api/v1/processing/load   │                                 │
      │  {                              │                                 │
      │    "document_id": "abc-123",    │                                 │
      │    "loader_type": "pymupdf"     │                                 │
      │  }                              │                                 │
      ├────────────────────────────────>│                                 │
      │                                 │                                 │
      │                                 │  7. 查询文档信息                  │
      │                                 ├────────────────────────────────>│
      │                                 │   SELECT * FROM documents       │
      │                                 │   WHERE id = 'abc-123'          │
      │                                 │                                 │
      │                                 │<────────────────────────────────┤
      │                                 │   返回文档路径、状态等信息         │
      │                                 │                                 │
      │                                 │  8. 更新文档状态为"处理中"        │
      │                                 ├────────────────────────────────>│
      │                                 │   UPDATE documents              │
      │                                 │   SET status = 'processing'     │
      │                                 │                                 │
      │                                 │  9. 创建处理记录                  │
      │                                 ├────────────────────────────────>│
      │                                 │   INSERT INTO                   │
      │                                 │   processing_results            │
      │                                 │   (type='load', status='running')│
      │                                 │                                 │
      │                                 │ 10. 🔥 调用 PDF 解析器 🔥        │
      │                                 │                                 │
      │                                 │    ┌─────────────────────────┐  │
      │                                 │    │  PyMuPDF Loader         │  │
      │                                 │    │  ─────────────────      │  │
      │                                 │    │  读取 PDF 文件           │  │
      │                                 │    │  逐页提取文字            │  │
      │                                 │    │  统计字符数、页数        │  │
      │                                 │    │  返回结构化数据          │  │
      │                                 │    └─────────────────────────┘  │
      │                                 │                                 │
      │                                 │ 11. 保存解析结果为 JSON          │
      │                                 │     results/load/               │
      │                                 │     提问的智慧_20251203_load.json│
      │                                 │                                 │
      │                                 │ 12. 更新处理记录                 │
      │                                 ├────────────────────────────────>│
      │                                 │   UPDATE processing_results     │
      │                                 │   SET status = 'completed',     │
      │                                 │       result_path = '...',      │
      │                                 │       extra_metadata = {...}    │
      │                                 │                                 │
      │                                 │ 13. 更新文档状态为"就绪"          │
      │                                 ├────────────────────────────────>│
      │                                 │   UPDATE documents              │
      │                                 │   SET status = 'ready'          │
      │                                 │                                 │
      │  返回处理结果                     │                                 │
      │  {                              │                                 │
      │    "status": "completed",       │                                 │
      │    "extra_metadata": {          │                                 │
      │      "total_pages": 19,         │                                 │
      │      "total_chars": 21772       │                                 │
      │    }                            │                                 │
      │  }                              │                                 │
      │<────────────────────────────────┤                                 │
      │                                 │                                 │
      │ 14. 页面显示解析成功              │                                 │
      │     共19页，21772个字符          │                                 │
      │                                 │                                 │

═════════════════════════════════════════════════════════════════════════════════
第三步: 查看解析结果
═════════════════════════════════════════════════════════════════════════════════
      │                                 │                                 │
      │ 15. 用户点击"查看结果"            │                                 │
      │                                 │                                 │
      │  GET /api/v1/processing/load/   │                                 │
      │      abc-123/results            │                                 │
      ├────────────────────────────────>│                                 │
      │                                 │                                 │
      │                                 │ 16. 查询处理记录                 │
      │                                 ├────────────────────────────────>│
      │                                 │   SELECT * FROM                 │
      │                                 │   processing_results            │
      │                                 │   WHERE document_id='abc-123'   │
      │                                 │   AND type='load'               │
      │                                 │                                 │
      │                                 │<────────────────────────────────┤
      │                                 │   返回 result_path              │
      │                                 │                                 │
      │                                 │ 17. 读取 JSON 文件               │
      │                                 │     (从 result_path)            │
      │                                 │                                 │
      │  返回完整解析数据                 │                                 │
      │  {                              │                                 │
      │    "total_pages": 19,           │                                 │
      │    "pages": [                   │                                 │
      │      {                          │                                 │
      │        "page_number": 1,        │                                 │
      │        "text": "提问的智慧...",  │                                 │
      │        "char_count": 617        │                                 │
      │      },                         │                                 │
      │      ...                        │                                 │
      │    ]                            │                                 │
      │  }                              │                                 │
      │<────────────────────────────────┤                                 │
      │                                 │                                 │
      │ 18. 页面展示文档内容              │                                 │
      │     - 显示每一页的文字            │                                 │
      │     - 支持搜索、高亮等功能         │                                 │
      │                                 │                                 │
```

---

## 三、核心代码解析

### 3.1 前端上传文档

```javascript
// frontend/src/api/documents.js
async function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await fetch('http://localhost:8000/api/v1/documents', {
    method: 'POST',
    body: formData
  })
  
  return await response.json()
  // 返回: { success: true, data: { id: "abc-123", filename: "...", ... } }
}
```

### 3.2 前端触发加载

```javascript
// frontend/src/api/processing.js
async function loadDocument(documentId, loaderType = 'pymupdf') {
  const response = await fetch('http://localhost:8000/api/v1/processing/load', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      document_id: documentId,
      loader_type: loaderType
    })
  })
  
  return await response.json()
  // 返回: { success: true, data: { status: "completed", ... } }
}
```

### 3.3 后端处理上传

```python
# backend/src/api/documents.py
@router.post("/documents")
async def upload_document(file: UploadFile, db: Session):
    # 1. 验证文件
    validate_file_upload(file.file, file.filename)
    
    # 2. 保存文件到 uploads/ 目录
    storage_path, content_hash = file_storage.save_upload(file.file, file.filename)
    
    # 3. 创建数据库记录
    document = Document(
        filename=file.filename,
        format="pdf",
        size_bytes=os.path.getsize(storage_path),
        storage_path=storage_path,
        content_hash=content_hash,
        status="uploaded"  # 初始状态
    )
    
    db.add(document)
    db.commit()
    
    return success_response(data=document_to_dict(document))
```

### 3.4 后端加载文档 (核心!)

```python
# backend/src/services/loading_service.py
def load_document(db: Session, document_id: str, loader_type: str = "pymupdf"):
    # 1. 查询文档
    document = db.query(Document).filter(Document.id == document_id).first()
    
    # 2. 更新状态为"处理中"
    document.status = "processing"
    db.commit()
    
    # 3. 创建处理记录
    processing_result = ProcessingResult(
        document_id=document_id,
        processing_type="load",
        provider=loader_type,
        status="running"
    )
    db.add(processing_result)
    db.commit()
    
    try:
        # 🔥 4. 核心步骤: 调用 PDF 解析器 🔥
        loader = pymupdf_loader  # 或 pypdf_loader, unstructured_loader
        result_data = loader.extract_text(document.storage_path)
        
        # result_data 示例:
        # {
        #   "success": True,
        #   "total_pages": 19,
        #   "total_chars": 21772,
        #   "pages": [
        #     {"page_number": 1, "text": "...", "char_count": 617},
        #     {"page_number": 2, "text": "...", "char_count": 570},
        #     ...
        #   ]
        # }
        
        # 5. 保存结果到 JSON 文件
        result_path = json_storage.save_result(
            document.filename,
            "load",
            result_data
        )
        # 保存到: results/load/提问的智慧_20251203111841_load.json
        
        # 6. 更新处理记录
        processing_result.result_path = result_path
        processing_result.status = "completed"
        processing_result.extra_metadata = {
            "total_pages": result_data.get("total_pages", 0),
            "total_chars": result_data.get("total_chars", 0)
        }
        
        # 7. 更新文档状态
        document.status = "ready"
        
        db.commit()
        return processing_result
        
    except Exception as e:
        # 出错时标记为失败
        processing_result.status = "failed"
        document.status = "error"
        db.commit()
        raise
```

### 3.5 核心 API 方法

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

---

## 四、数据存储结构

### 4.1 数据库模型

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

### 4.2 模型关系图

```
Document (documents)
  ├── ProcessingResult (processing_results) - 一对多
  └── DocumentChunk (document_chunks) - 一对多
```

### 4.3 数据库存储示例

```sql
-- 文档表
documents
  id: "abc-123"
  filename: "提问的智慧.pdf"
  format: "pdf"
  size_bytes: 245678
  storage_path: "uploads/提问的智慧.pdf"
  status: "ready"  -- uploaded -> processing -> ready/error
  upload_time: "2025-12-03 11:18:41"

-- 处理结果表
processing_results
  id: "xyz-789"
  document_id: "abc-123"  -- 关联到上面的文档
  processing_type: "load"
  provider: "pymupdf"
  status: "completed"  -- running -> completed/failed
  result_path: "results/load/提问的智慧_20251203111841_load.json"
  extra_metadata: {
    "total_pages": 19,
    "total_chars": 21772
  }
```

### 4.4 文件系统存储

```
项目根目录/
├── uploads/                          # 原始文件
│   └── 提问的智慧.pdf                 # 用户上传的 PDF
│
└── results/                          # 处理结果
    └── load/                         # 加载结果
        └── 提问的智慧_20251203111841_load.json  # 解析后的文本数据
```

### 4.5 JSON 结果文件内容

```json
{
  "success": true,
  "loader": "pymupdf",
  "total_pages": 19,
  "total_chars": 21772,
  "metadata": {
    "title": "",
    "author": "",
    "creator": "Typora"
  },
  "pages": [
    {
      "page_number": 1,
      "text": "提问的智慧 来源：https://github.com/...",
      "char_count": 617
    },
    {
      "page_number": 2,
      "text": "描述问题症状而非你的猜测...",
      "char_count": 570
    }
    // ... 共19页
  ],
  "full_text": "提问的智慧 来源：... (所有页面的完整文本)"
}
```

### 4.6 数据库模式

#### documents 表
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

#### document_chunks 表
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

#### processing_results 表
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

---

## 五、支持的加载器

加载服务支持 6 种加载器,可根据文件格式和需求选择:

### 5.1 PyMuPDF (默认 PDF 加载器,推荐)

```python
loader_type = "pymupdf"
```

- **优点**: 速度快、准确度高、功能强大
- **适用**: 通用 PDF 文档
- **文件格式**: PDF
- **示例**: 《提问的智慧.pdf》就是用这个解析的

### 5.2 PyPDF

```python
loader_type = "pypdf"
```

- **优点**: 纯 Python、依赖少
- **适用**: 简单的 PDF 文档
- **文件格式**: PDF
- **缺点**: 对复杂 PDF 支持不如 PyMuPDF

### 5.3 Unstructured

```python
loader_type = "unstructured"
```

- **优点**: 支持表格、图片、布局识别
- **适用**: 复杂的学术论文、报告
- **文件格式**: PDF
- **缺点**: 速度较慢、依赖多

### 5.4 DOCX Loader

```python
loader_type = "docx"
```

- **优点**: 原生支持 Word 2007+ 格式
- **适用**: .docx 文件
- **文件格式**: DOCX
- **特性**: 提取文本、段落、样式信息

### 5.5 DOC Loader

```python
loader_type = "doc"
```

- **优点**: 支持旧版 Word 格式
- **适用**: .doc 文件（Word 97-2003）
- **文件格式**: DOC
- **依赖**: 需要 antiword 工具

### 5.6 Text Loader

```python
loader_type = "text"
```

- **优点**: 简单高效
- **适用**: 纯文本文件、Markdown 文件
- **文件格式**: TXT, MD, MARKDOWN
- **特性**: 自动编码检测、行级处理

### 5.7 自动加载器选择

如果不指定 `loader_type`，系统会根据文件格式自动选择合适的加载器：

```python
# 自动选择映射
format_loader_map = {
    "pdf": "pymupdf",      # PDF 默认使用 PyMuPDF
    "txt": "text",         # 文本文件使用 Text Loader
    "md": "text",          # Markdown 使用 Text Loader
    "markdown": "text",
    "docx": "docx",        # DOCX 使用 DOCX Loader
    "doc": "doc"           # DOC 使用 DOC Loader
}
```

示例：
```bash
# 不指定 loader_type，系统自动选择
curl -X POST "http://localhost:8000/api/v1/processing/load" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "doc_uuid"}'
```

---

## 六、状态流转

### 6.1 文档状态

```
uploaded (上传完成)
    ↓
processing (正在解析)
    ↓
ready (解析完成) / error (解析失败)
```

### 6.2 处理状态

```
running (正在运行)
    ↓
completed (完成) / failed (失败)
```

### 6.3 状态管理特性

1. **完整的状态跟踪**
   - uploaded → processing → ready
   - 失败时标记为 error
   - 完整的处理历史记录

2. **错误处理**
   - 文档不存在检测
   - 文件格式验证
   - 加载失败回滚
   - 详细的错误信息

---

## 七、实际使用示例

### 7.0 完整 API 端点列表

#### 文档管理相关
- `POST /api/v1/documents` - 上传文档
- `GET /api/v1/documents` - 获取文档列表（支持分页和状态过滤）
- `GET /api/v1/documents/{document_id}` - 获取单个文档信息
- `GET /api/v1/documents/{document_id}/preview?pages=3` - 预览文档内容
- `DELETE /api/v1/documents/{document_id}` - 删除文档

#### 文档加载相关
- `POST /api/v1/processing/load` - 加载文档
- `GET /api/v1/processing/loaders` - 获取可用加载器列表

#### 处理结果相关
- `GET /api/v1/processing/results/{document_id}?processing_type=load` - 获取文档的处理结果列表
- `GET /api/v1/processing/results/detail/{result_id}` - 获取处理结果详情

### 7.1 命令行测试

```bash
# 1. 上传文档
curl -X POST "http://localhost:8000/api/v1/documents" \
  -F "file=@提问的智慧.pdf"

# 返回:
# {
#   "success": true,
#   "data": {
#     "id": "abc-123",
#     "filename": "提问的智慧.pdf",
#     "status": "uploaded"
#   }
# }

# 2. 加载文档
curl -X POST "http://localhost:8000/api/v1/processing/load" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "abc-123",
    "loader_type": "pymupdf"
  }'

# 返回:
# {
#   "success": true,
#   "data": {
#     "status": "completed",
#     "extra_metadata": {
#       "total_pages": 19,
#       "total_chars": 21772
#     }
#   }
# }

# 3. 查看结果（需要先获取 result_id）
curl "http://localhost:8000/api/v1/processing/results/abc-123?processing_type=load"

# 获取到 result_id 后，查看详细结果
curl "http://localhost:8000/api/v1/processing/results/detail/result_id"

# 返回完整的解析数据 (JSON)
```

### 7.2 前端 Vue 组件

```vue
<template>
  <div class="document-loader">
    <!-- 上传文件 -->
    <input type="file" @change="handleFileUpload" accept=".pdf" />
    
    <!-- 加载按钮 -->
    <button @click="loadDocument" :disabled="!documentId">
      解析文档
    </button>
    
    <!-- 显示结果 -->
    <div v-if="result">
      <h3>解析结果</h3>
      <p>总页数: {{ result.total_pages }}</p>
      <p>总字符数: {{ result.total_chars }}</p>
      
      <div v-for="page in result.pages" :key="page.page_number">
        <h4>第 {{ page.page_number }} 页</h4>
        <pre>{{ page.text }}</pre>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      documentId: null,
      result: null
    }
  },
  
  methods: {
    async handleFileUpload(event) {
      const file = event.target.files[0]
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await fetch('http://localhost:8000/api/v1/documents', {
        method: 'POST',
        body: formData
      })
      
      const data = await response.json()
      this.documentId = data.data.id
    },
    
    async loadDocument() {
      // 发起加载请求
      const loadResponse = await fetch('http://localhost:8000/api/v1/processing/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: this.documentId,
          loader_type: 'pymupdf'  // 或不指定，让系统自动选择
        })
      })
      
      const loadData = await loadResponse.json()
      const resultId = loadData.data.id
      
      // 加载完成后获取详细结果
      const resultResponse = await fetch(
        `http://localhost:8000/api/v1/processing/results/detail/${resultId}`
      )
      const resultData = await resultResponse.json()
      this.result = resultData.data.result_data
    }
  }
}
</script>
```

### 7.3 API 使用流程

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
curl -X POST "http://localhost:8000/api/v1/processing/load" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc_uuid",
    "loader_type": "pymupdf"
  }'
```

返回:
```json
{
  "success": true,
  "message": "Document loaded successfully",
  "data": {
    "id": "result_uuid",
    "document_id": "doc_uuid",
    "processing_type": "load",
    "provider": "pymupdf",
    "status": "completed",
    "created_at": "2025-12-03T12:00:00Z",
    "extra_metadata": {
      "total_pages": 10,
      "total_chars": 5000,
      "loader_type": "pymupdf",
      "file_format": "pdf"
    }
  }
}
```

#### Step 3: 查看加载结果

```bash
curl "http://localhost:8000/api/v1/processing/results/detail/result_uuid"
```

返回:
```json
{
  "success": true,
  "data": {
    "id": "result_uuid",
    "document_id": "doc_uuid",
    "processing_type": "load",
    "status": "completed",
    "result_data": {
      "success": true,
      "total_pages": 10,
      "total_chars": 5000,
      "pages": [
        {
          "page_number": 1,
          "text": "页面内容...",
          "char_count": 500
        }
      ]
    }
  }
}
```

#### Step 4: 获取文档预览（快速查看内容）

```bash
curl "http://localhost:8000/api/v1/documents/doc_uuid/preview?pages=3"
```

返回:
```json
{
  "success": true,
  "data": {
    "preview_text": "前3页的内容预览...",
    "page_count": 3,
    "total_pages": 10,
    "total_chars": 5000,
    "loader_used": "pymupdf"
  }
}
```

#### Step 5: 获取可用加载器信息

```bash
curl "http://localhost:8000/api/v1/processing/loaders"
```

返回:
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

---

## 八、技术实现细节

### 8.1 文件结构

```
backend/
├── src/
│   ├── api/
│   │   ├── documents.py          # 文档管理 API ✅
│   │   ├── loading.py            # 加载 API ✅
│   │   ├── parsing.py            # 解析 API ✅
│   │   └── processing.py         # 处理结果 API ✅
│   ├── models/
│   │   ├── __init__.py           # 导出所有模型
│   │   ├── document.py           # 文档模型 ✅
│   │   ├── document_chunk.py     # 文档块模型 ✅
│   │   └── processing_result.py  # 处理结果模型 ✅
│   ├── providers/
│   │   └── loaders/
│   │       ├── pymupdf_loader.py      # PyMuPDF 加载器 ✅
│   │       ├── pypdf_loader.py        # PyPDF 加载器 ✅
│   │       ├── unstructured_loader.py # Unstructured 加载器 ✅
│   │       ├── docx_loader.py         # DOCX 加载器 ✅
│   │       ├── doc_loader.py          # DOC 加载器 ✅
│   │       └── text_loader.py         # 文本加载器 ✅
│   ├── services/
│   │   ├── loading_service.py    # 加载服务 ✅
│   │   └── parsing_service.py    # 解析服务 ✅
│   ├── storage/
│   │   ├── database.py           # 数据库配置
│   │   ├── file_storage.py       # 文件存储
│   │   └── json_storage.py       # JSON 结果存储
│   ├── utils/
│   │   ├── error_handlers.py     # 错误处理
│   │   ├── formatters.py         # 响应格式化
│   │   └── validators.py         # 数据验证
│   ├── config.py                 # 配置文件
│   └── main.py                   # 应用入口 ✅
├── documents/
│   └── LOADING_SERVICE.md        # 加载服务文档 ✅
├── init_database.py              # 数据库初始化 ✅
├── test_document_loading.py      # 测试脚本 ✅
└── start_backend.sh              # 启动脚本 ✅
```

### 8.2 技术栈

- **FastAPI**: Web 框架
- **SQLAlchemy**: ORM
- **SQLite**: 数据库
- **Uvicorn**: ASGI 服务器
- **文档加载器**:
  - PyMuPDF/PyPDF/Unstructured: PDF 解析器
  - python-docx: DOCX 文档解析
  - antiword: DOC 文档解析
  - 内置文本加载器: TXT/Markdown 解析

### 8.3 核心特性

#### 加载服务特性

1. **多格式支持**
   - PDF: pymupdf (默认), pypdf, unstructured
   - Word: docx, doc
   - 文本: txt, markdown
   - 自动格式检测和加载器选择

2. **完整的错误处理**
   - 文档不存在检测
   - 文件格式验证
   - 加载失败回滚
   - 详细的错误信息
   - 文件去重检测

3. **状态管理**
   - uploaded → processing → ready
   - 失败时标记为 error
   - 完整的处理历史记录

4. **结果存储**
   - JSON 格式存储详细结果
   - 元数据提取
   - 页面级内容保存

5. **文档预览**
   - 快速预览文档内容
   - 支持指定预览页数
   - 自动选择合适的加载器

6. **文档管理**
   - 分页查询文档列表
   - 状态过滤
   - 文件去重检测
   - 级联删除（删除文档时自动清理相关文件和记录）

### 8.4 启动服务

#### 使用启动脚本

```bash
cd backend
./start_backend.sh
```

#### 手动启动

```bash
cd backend
source .venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 数据库初始化

```bash
cd backend
source .venv/bin/activate
python init_database.py
```

### 8.5 测试

运行测试脚本:

```bash
cd backend
source .venv/bin/activate
python test_document_loading.py
```

### 8.6 日志示例

```
INFO: Starting document loading: doc_123 with pymupdf
INFO: Successfully loaded doc_123: 10 pages, 5000 characters
INFO: Document loading completed: doc_123
```

---

## 九、不同格式文档的加载示例

### 9.1 加载 PDF 文档

```bash
# 上传 PDF
curl -X POST "http://localhost:8000/api/v1/documents" \
  -F "file=@document.pdf"

# 使用 PyMuPDF 加载（推荐）
curl -X POST "http://localhost:8000/api/v1/processing/load" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "doc_id", "loader_type": "pymupdf"}'

# 或使用 Unstructured（复杂 PDF）
curl -X POST "http://localhost:8000/api/v1/processing/load" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "doc_id", "loader_type": "unstructured"}'
```

### 9.2 加载 Word 文档

```bash
# 上传 DOCX
curl -X POST "http://localhost:8000/api/v1/documents" \
  -F "file=@document.docx"

# 自动选择 docx 加载器
curl -X POST "http://localhost:8000/api/v1/processing/load" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "doc_id"}'

# 或上传 DOC（需要 antiword）
curl -X POST "http://localhost:8000/api/v1/documents" \
  -F "file=@document.doc"

curl -X POST "http://localhost:8000/api/v1/processing/load" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "doc_id"}'
```

### 9.3 加载文本文档

```bash
# 上传 TXT 或 Markdown
curl -X POST "http://localhost:8000/api/v1/documents" \
  -F "file=@document.txt"

# 自动使用 text 加载器
curl -X POST "http://localhost:8000/api/v1/processing/load" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "doc_id"}'
```

### 9.4 批量处理文档

```bash
#!/bin/bash
# 批量上传和加载文档

for file in *.pdf; do
  echo "Processing $file..."
  
  # 上传文档
  response=$(curl -s -X POST "http://localhost:8000/api/v1/documents" \
    -F "file=@$file")
  
  # 提取 document_id
  doc_id=$(echo $response | jq -r '.data.id')
  
  # 加载文档
  curl -X POST "http://localhost:8000/api/v1/processing/load" \
    -H "Content-Type: application/json" \
    -d "{\"document_id\": \"$doc_id\"}"
  
  echo "Completed $file (ID: $doc_id)"
done
```

---

## 十、问题修复记录

### 10.1 SQLAlchemy 映射错误

**问题**:
```
InvalidRequestError: One or more mappers failed to initialize - 
can't proceed with initialization of other mappers. 
Original exception was: When initializing mapper Mapper[Document(documents)], 
expression 'DocumentChunk' failed to locate a name ('DocumentChunk').
```

**原因**: DocumentChunk 模型未定义

**解决方案**:
- 创建了 `DocumentChunk` 模型 (`src/models/document_chunk.py`)
- 修复了模型间的关系引用,使用字符串引用避免循环导入
- 修复了索引名称冲突问题

### 10.2 保留字段名冲突

**问题**:
```
InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
```

**原因**: SQLAlchemy 的 Base 类有 metadata 属性

**解决**: 将字段名改为 `chunk_metadata`

### 10.3 索引名称冲突

**问题**:
```
OperationalError: index idx_document_id already exists
```

**原因**: 多个模型使用了相同的索引名

**解决**: 为每个表的索引添加唯一前缀

---

## 十一、总结与下一步

### 11.1 核心功能总结

✅ **多格式文档支持**: 支持 PDF、Word（DOCX/DOC）、文本（TXT/Markdown）等多种格式  
✅ **智能加载器选择**: 根据文件格式自动选择最佳加载器  
✅ **页面级提取**: 逐页提取,保留页面结构  
✅ **6种加载器**: PyMuPDF、PyPDF、Unstructured、DOCX、DOC、Text  
✅ **状态跟踪**: 实时跟踪处理进度和状态  
✅ **结果存储**: JSON 格式保存,便于后续使用  
✅ **文档预览**: 快速预览文档内容  
✅ **文件去重**: 自动检测重复文件  
✅ **完整 API**: RESTful API 设计，支持各种操作  

### 11.2 数据流向

```
用户上传 PDF 
  → 保存到硬盘 
  → 创建数据库记录 
  → 调用加载器解析 
  → 保存 JSON 结果 
  → 更新数据库状态 
  → 返回给前端
```

### 11.3 下一步开发计划

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

**加载服务是基础**, 只有先把 PDF "读懂", 后面的步骤才能进行!

---

**状态**: ✅ 完成并测试通过  
**创建时间**: 2025-12-03  
**版本**: 1.0.0
