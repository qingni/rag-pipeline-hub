# 文档加载服务详细说明

## 一、核心功能是什么?

**简单来说**: 文档加载服务就是把 PDF 文件"读懂"并转换成程序可以处理的文本数据。

### 1.1 为什么需要这个服务?

假设你有一个 PDF 文档《提问的智慧.pdf》:
- PDF 是二进制格式,计算机程序无法直接理解内容
- 需要"解析"PDF,提取出里面的文字
- 提取后的文字可以用于搜索、问答、分析等

### 1.2 具体做什么?

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

## 四、数据存储结构

### 4.1 数据库存储

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

### 4.2 文件系统存储

```
项目根目录/
├── uploads/                          # 原始文件
│   └── 提问的智慧.pdf                 # 用户上传的 PDF
│
└── results/                          # 处理结果
    └── load/                         # 加载结果
        └── 提问的智慧_20251203111841_load.json  # 解析后的文本数据
```

### 4.3 JSON 结果文件内容

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

## 五、支持的加载器

加载服务支持 3 种 PDF 解析器,可根据需求选择:

### 5.1 PyMuPDF (默认,推荐)
```python
loader_type = "pymupdf"
```
- **优点**: 速度快、准确度高、功能强大
- **适用**: 通用 PDF 文档
- **示例**: 《提问的智慧.pdf》就是用这个解析的

### 5.2 PyPDF
```python
loader_type = "pypdf"
```
- **优点**: 纯 Python、依赖少
- **适用**: 简单的 PDF 文档
- **缺点**: 对复杂 PDF 支持不如 PyMuPDF

### 5.3 Unstructured
```python
loader_type = "unstructured"
```
- **优点**: 支持表格、图片、布局识别
- **适用**: 复杂的学术论文、报告
- **缺点**: 速度较慢、依赖多

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

## 七、实际使用示例

### 示例 1: 命令行测试

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

# 3. 查看结果
curl "http://localhost:8000/api/v1/processing/load/abc-123/results"

# 返回完整的解析数据 (JSON)
```

### 示例 2: 前端 Vue 组件

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
      const response = await fetch('http://localhost:8000/api/v1/processing/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: this.documentId,
          loader_type: 'pymupdf'
        })
      })
      
      // 加载完成后获取结果
      const resultResponse = await fetch(
        `http://localhost:8000/api/v1/processing/load/${this.documentId}/results`
      )
      this.result = await resultResponse.json()
    }
  }
}
</script>
```

## 八、总结

### 核心功能
✅ **PDF → 文本**: 将 PDF 文档转换为结构化的文本数据  
✅ **页面级提取**: 逐页提取,保留页面结构  
✅ **多加载器**: 支持 3 种不同的 PDF 解析引擎  
✅ **状态跟踪**: 实时跟踪处理进度和状态  
✅ **结果存储**: JSON 格式保存,便于后续使用  

### 数据流向
```
用户上传 PDF 
  → 保存到硬盘 
  → 创建数据库记录 
  → 调用加载器解析 
  → 保存 JSON 结果 
  → 更新数据库状态 
  → 返回给前端
```

### 下一步
这个加载服务是 RAG 系统的**第一步**,后续还会有:
- **分块服务**: 将长文本切成小块
- **嵌入服务**: 为文本生成向量
- **索引服务**: 存储到向量数据库
- **搜索服务**: 语义搜索
- **生成服务**: AI 问答

**加载服务是基础**, 只有先把 PDF "读懂", 后面的步骤才能进行!
