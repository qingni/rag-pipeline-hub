# 文档加载 API 接口文档

**生成日期**: 2025-12-10  
**项目**: RAG Pipeline Hub - 文档加载模块  
**基础路径**: `/api/v1`

---

## 目录

1. [通用说明](#1-通用说明)
2. [文档管理接口](#2-文档管理接口)
3. [加载相关接口](#3-加载相关接口)
4. [结果查询接口](#4-结果查询接口)
5. [加载器信息接口](#5-加载器信息接口)

---

## 1. 通用说明

### 1.1 响应格式

所有接口返回统一的JSON格式:

```json
{
  "success": true,
  "message": "操作成功",
  "data": { ... }
}
```

### 1.2 错误响应

```json
{
  "success": false,
  "message": "错误描述",
  "error": {
    "code": "ERROR_CODE",
    "details": "详细信息"
  }
}
```

### 1.3 认证

目前无需认证,后续版本可能添加Token认证。

---

## 2. 文档管理接口

### 2.1 上传文档

**接口**: `POST /documents`

**描述**: 上传文档文件到系统

**Content-Type**: `multipart/form-data`

**参数**:
- `file` (file, required): 文档文件

**支持格式**:
- PDF (`.pdf`)
- Word文档 (`.docx`, `.doc`)
- 文本文件 (`.txt`, `.md`, `.markdown`)

**限制**:
- 最大文件大小: 50MB
- 单次上传: 1个文件

**请求示例**:
```bash
curl -X POST \
  http://localhost:8000/api/v1/documents \
  -F "file=@/path/to/document.pdf"
```

**响应**:
```json
{
  "success": true,
  "message": "Document uploaded successfully",
  "data": {
    "id": "doc_123456",
    "filename": "document.pdf",
    "original_filename": "document.pdf",
    "format": "pdf",
    "size_bytes": 1024000,
    "storage_path": "/path/to/uploads/doc_123456.pdf",
    "status": "uploaded",
    "upload_time": "2025-12-10T10:00:00Z"
  }
}
```

---

### 2.2 获取文档列表

**接口**: `GET /documents`

**描述**: 获取已上传的文档列表，并附带最近一次加载耗时和解析器信息

**参数**:
- `page` (int, default=1): 页码
- `page_size` (int, default=20): 每页数量
- `status` (string, optional): 状态过滤(uploaded/processing/ready/error)
- `has_chunking_result` (bool, optional): 是否只展示已经完成分块的文档

**响应**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "doc_123456",
        "filename": "document.pdf",
        "format": "pdf",
        "size_bytes": 1024000,
        "status": "ready",
        "upload_time": "2025-12-10T10:00:00Z",
        "last_processed": "2025-12-10T10:05:00Z",
        "loading_time": 2.53,
        "provider": "docling_serve"  
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "pages": 5
  }
}
```
---

### 2.3 获取文档详情

**接口**: `GET /documents/{document_id}`

**描述**: 获取指定文档的详细信息

**响应**:
```json
{
  "success": true,
  "data": {
    "id": "doc_123456",
    "filename": "document.pdf",
    "original_filename": "document.pdf",
    "format": "pdf",
    "size_bytes": 1024000,
    "storage_path": "/path/to/uploads/doc_123456.pdf",
    "status": "ready",
    "upload_time": "2025-12-10T10:00:00Z",
    "last_processed": "2025-12-10T10:05:00Z",
    "processing_results": [
      {
        "id": "result_789",
        "processing_type": "load",
        "provider": "pymupdf",
        "status": "completed",
        "created_at": "2025-12-10T10:05:00Z"
      }
    ]
  }
}
```

---

### 2.4 删除文档

**接口**: `DELETE /documents/{document_id}`

**描述**: 删除指定文档及其所有处理结果

**响应**:
```json
{
  "success": true,
  "message": "Document deleted successfully",
  "data": null
}
```

---

## 3. 加载相关接口

### 3.1 同步加载文档

**接口**: `POST /processing/load`

**描述**: 对已上传的文档执行同步加载操作, 提取文本内容并立即生成 `ProcessingResult`

**请求体**:
```json
{
  "document_id": "doc_123456",
  "loader_type": null,
  "enable_fallback": true
}
```

**参数说明**:
- `document_id` (string, required): 文档ID
- `loader_type` (string, optional): 加载器类型
  - `null` 或空: 自动选择(推荐，由 `fallback_manager` 根据格式和大小选择策略)
  - 具体值: `"docling_serve"`, `"pymupdf"`, `"pypdf"`, `"unstructured"`, `"docx"`, `"doc"`, `"text"` 等
- `enable_fallback` (bool, default=true): 是否启用多级降级策略

**响应**:
```json
{
  "success": true,
  "message": "Document loaded successfully",
  "data": {
    "id": "result_789",
    "document_id": "doc_123456",
    "processing_type": "load",
    "provider": "docling_serve",
    "status": "completed",
    "result_path": "/path/to/results/load/doc_123456_docling_serve_20251210_100500.json",
    "extra_metadata": {
      "total_pages": 10,
      "total_chars": 5234,
      "loader_type": "docling_serve",
      "file_format": "pdf",
      "processing_time": 2.53,
      "fallback_used": false,
      "fallback_reason": null,
      "table_count": 3,
      "image_count": 5
    },
    "created_at": "2025-12-10T10:05:00Z"
  }
}
```

### 3.2 异步加载任务

Docling Serve 对大文件/复杂文档推荐使用异步加载模式，通过任务队列和 `LoadingTask` 追踪进度。

#### 3.2.1 提交异步加载任务

**接口**: `POST /processing/load/async`

**请求体**:
```json
{
  "document_id": "doc_123456",
  "loader_type": "docling_serve"
}
```

**响应**:
```json
{
  "success": true,
  "message": "Async loading task submitted",
  "data": {
    "task_id": "task_abc123",
    "external_task_id": "docling-task-xyz",
    "status": "pending",
    "document_id": "doc_123456",
    "loader_type": "docling_serve"
  }
}
```

#### 3.2.2 查询异步任务状态

**接口**: `GET /processing/load/task/{task_id}/status`

**响应**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_abc123",
    "status": "started",          
    "progress": 35,                
    "document_id": "doc_123456",
    "error_message": null,
    "processing_time": null
  },
  "message": "Task status retrieved"
}
```

#### 3.2.3 获取异步任务结果

**接口**: `GET /processing/load/task/{task_id}/result`

**描述**: 任务成功后获取完整的加载结果（包含 `ProcessingResult` 信息和解析后的 JSON 数据）

**响应**:
```json
{
  "success": true,
  "message": "Task result retrieved",
  "data": {
    "id": "result_789",
    "document_id": "doc_123456",
    "processing_type": "load",
    "provider": "docling_serve",
    "status": "completed",
    "result_path": "/path/to/results/load/doc_123456_docling_serve_20251210_100500.json",
    "extra_metadata": {
      "total_pages": 10,
      "total_chars": 5234,
      "loader_type": "docling_serve",
      "file_format": "pdf",
      "processing_time": 12.34,
      "async_mode": true,
      "table_count": 3,
      "image_count": 5
    },
    "created_at": "2025-12-10T10:05:00Z",
    "result_data": {
      "success": true,
      "loader": "docling_serve",
      "full_text": "...markdown...",
      "pages": [
        {"page_number": 1, "text": "...", "char_count": 523}
      ],
      "total_pages": 10,
      "total_chars": 5234,
      "tables": [...],
      "images": [...],
      "metadata": {"image_count": 5, "table_count": 3}
    },
    "task_id": "task_abc123"
  }
}
```

#### 3.2.4 取消异步任务

**接口**: `POST /processing/load/task/{task_id}/cancel`

**响应**:
```json
{
  "success": true,
  "message": "Task cancellation requested",
  "data": {
    "task_id": "task_abc123",
    "cancelled": true,
    "status": "cancelled"
  }
}
```

**错误示例**:
```json
{
  "success": false,
  "message": "Loading failed: Unsupported file format: xyz",
  "error": {
    "code": "PROCESSING_ERROR",
    "details": {
      "supported_formats": ["pdf", "docx", "doc", "txt", "md", "markdown"]
    }
  }
}
```

---

### 3.3 任务队列与批量状态查询

为了支持前端轮询和多任务并行,加载模块还暴露了任务队列相关接口。

**接口 1**: `GET /processing/load/queue/stats`  
**描述**: 获取当前任务队列统计信息(各状态任务数量、不同类别池的配置等)。

**接口 2**: `GET /processing/load/queue/active`  
**描述**: 获取当前处于 pending/queued/running 状态的所有任务列表。

**接口 3**: `POST /processing/load/queue/batch-status`  
**请求体**:
```json
{
  "task_ids": ["task_abc123", "task_def456"]
}
```
**描述**: 批量查询多个任务的状态,减少前端轮询请求次数。返回结构示例:
```json
{
  "success": true,
  "data": {
    "statuses": {
      "task_abc123": {"status": "started", "progress": 30},
      "task_def456": {"status": "success", "progress": 100}
    },
    "queried": 2,
    "found": 2
  },
  "message": "Batch status retrieved"
}
```

---

## 4. 结果查询接口

### 4.1 获取处理结果列表

**接口**: `GET /processing/results/{document_id}`

**描述**: 获取指定文档的处理结果列表

**参数**:
- `document_id` (string, required): 文档ID（路径参数）
- `processing_type` (string, optional): 处理类型(load/chunk等)

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": "result_789",
      "document_id": "doc_123456",
      "processing_type": "load",
      "provider": "docling_serve",
      "status": "completed",
      "result_path": "/path/to/results/load/doc_123456_docling_serve_20251210_100500.json",
      "created_at": "2025-12-10T10:05:00Z",
      "extra_metadata": {
        "total_pages": 10,
        "total_chars": 5234,
        "loader_type": "docling_serve",
        "file_format": "pdf"
      }
    }
  ]
}
```
---

### 4.2 获取处理结果详情

**接口**: `GET /processing/results/detail/{result_id}`

**描述**: 获取指定处理结果的详细信息,包括完整的结果数据（从 JSON 文件中加载）

**响应**:
```json
{
  "success": true,
  "data": {
    "id": "result_789",
    "document_id": "doc_123456",
    "processing_type": "load",
    "provider": "pymupdf",
    "status": "completed",
    "result_path": "/path/to/results/load/doc_123456_pymupdf_20251210_100500.json",
    "created_at": "2025-12-10T10:05:00Z",
    "extra_metadata": {
      "total_pages": 10,
      "total_chars": 5234,
      "loader_type": "pymupdf",
      "file_format": "pdf"
    },
    "result_data": {
      "success": true,
      "loader": "pymupdf",
      "metadata": {
        "page_count": 10,
        "title": "示例文档",
        "author": "张三",
        "subject": "技术文档",
        "creator": "Microsoft Word",
        "producer": "Adobe PDF Library",
        "format": "PDF 1.7"
      },
      "pages": [
        {
          "page_number": 1,
          "text": "第一页的文本内容...",
          "char_count": 523
        },
        {
          "page_number": 2,
          "text": "第二页的文本内容...",
          "char_count": 487
        }
      ],
      "full_text": "完整的文档文本内容...",
      "total_pages": 10,
      "total_chars": 5234
    }
  }
}
```

---

### 4.3 下载结果JSON

**接口**: `GET /processing/results/detail/{result_id}`

**描述**: 通过结果详情接口获取完整结果数据,并在客户端将返回的 JSON 保存为文件(可配合 `curl -o` 或 SDK 中的 `download_result` 方法使用)。

**响应**: 同 [4.2 获取处理结果详情](#42-获取处理结果详情),包含 `result_data` 字段; 前端/客户端可自行决定只保存 `data.result_data` 或完整响应。

---

## 5. 加载器信息接口

### 5.1 获取可用加载器列表

**接口**: `GET /processing/loaders`

**描述**: 获取系统中可用的所有加载器及其配置(包括支持格式、性能特征、能力标记和当前可用状态)。

**响应**:
```json
{
  "success": true,
  "data": {
    "loaders": [
      {
        "name": "docling_serve",
        "display_name": "Docling Serve (HTTP)",
        "supported_formats": ["pdf", "docx", "xlsx", "pptx", "html", "md", "txt", "csv"],
        "priority": 0,
        "avg_speed": "medium",
        "quality_level": "high",
        "requires_installation": false,
        "installation_command": "./start_docling.sh",
        "supports_tables": true,
        "supports_images": true,
        "supports_formulas": true,
        "supports_ocr": true,
        "is_available": true,
        "unavailable_reason": null
      }
    ],
    "total": 1
  }
}
```

> 实际返回的 `loaders` 数量和字段取决于 `LOADER_REGISTRY` 配置,上例仅为典型示例。

---

### 5.2 获取支持格式与解析策略

**接口**: `GET /processing/loaders/formats`

**描述**: 获取所有支持的文件格式,以及每种格式对应的主加载器、降级链和大文件优先使用的快速加载器。

**响应**:
```json
{
  "success": true,
  "data": {
    "formats": [
      "pdf",
      "docx",
      "xlsx",
      "pptx",
      "html",
      "csv",
      "json",
      "txt",
      "md",
      "markdown",
      "xml",
      "msg",
      "vtt",
      "properties"
    ],
    "strategies": [
      {
        "format": "pdf",
        "primary_loader": "docling_serve",
        "fallback_loaders": ["pymupdf", "pypdf", "unstructured"],
        "size_threshold_mb": 20.0,
        "fast_loader": "pymupdf"
      }
    ],
    "total": 1
  }
}
```

> 实际返回会包含所有格式的策略,这里仅展示 `pdf` 的典型结构。 

---

### 5.3 获取推荐加载器

**接口**: `GET /processing/loaders/recommend`

**描述**: 根据文件格式和大小返回推荐的加载器,内部使用 `fallback_manager.get_recommended_loader` 结合策略与可用性做决策。

**请求参数**:

- `format` (string, required): 文件格式(如 `pdf`, `docx`)
- `size_bytes` (int, optional): 文件大小(字节)

**响应**:
```json
{
  "success": true,
  "data": {
    "format": "pdf",
    "size_bytes": 1048576,
    "recommended_loader": "docling_serve"
  }
}
```

---

## 6. 状态码说明

| 状态码 | 说明 |
|-------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 413 | 文件过大 |
| 415 | 不支持的文件格式 |
| 500 | 服务器错误 |

---

## 7. 错误码说明

| 错误码 | 说明 | 解决方法 |
|-------|------|----------|
| `DOCUMENT_NOT_FOUND` | 文档不存在 | 检查document_id是否正确 |
| `UNSUPPORTED_FORMAT` | 不支持的文件格式 | 使用支持的格式上传 |
| `FILE_TOO_LARGE` | 文件过大 | 文件大小不超过50MB |
| `PROCESSING_ERROR` | 处理失败 | 查看详细错误信息 |
| `LOADER_NOT_FOUND` | 加载器不存在 | 使用可用的加载器类型 |
| `INVALID_PARAMETERS` | 参数无效 | 检查请求参数格式 |

---

## 8. 使用示例

### 8.1 完整加载流程

```bash
# 1. 上传文档
curl -X POST http://localhost:8000/api/v1/documents \
  -F "file=@document.pdf"
# 返回: {"success":true,"data":{"id":"doc_123456",...}}

# 2. 自动加载文档
curl -X POST http://localhost:8000/api/v1/processing/load \
  -H "Content-Type: application/json" \
  -d '{"document_id":"doc_123456"}'
# 返回: {"success":true,"data":{"id":"result_789",...}}

# 3. 获取结果详情
curl http://localhost:8000/api/v1/processing/results/detail/result_789
# 返回完整的加载结果数据

# 4. 下载结果JSON
curl http://localhost:8000/api/v1/processing/results/detail/result_789 \
  -o result.json
```

### 8.2 指定加载器加载

```bash
# 使用PyPDF加载器
curl -X POST http://localhost:8000/api/v1/processing/load \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc_123456",
    "loader_type": "pypdf"
  }'
```

### 8.3 查询文档列表

```bash
# 查询PDF格式的文档
curl "http://localhost:8000/api/v1/documents?format=pdf&page=1&page_size=10"

# 搜索文件名包含"report"的文档
curl "http://localhost:8000/api/v1/documents?search=report"

# 获取状态为ready的文档
curl "http://localhost:8000/api/v1/documents?status=ready"
```

### 8.4 Python SDK示例

```python
import requests

class LoadingClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def upload_document(self, file_path):
        """上传文档"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{self.base_url}/api/v1/documents",
                files=files
            )
        return response.json()
    
    def load_document(self, document_id, loader_type=None):
        """加载文档"""
        payload = {"document_id": document_id}
        if loader_type:
            payload["loader_type"] = loader_type
        
        response = requests.post(
            f"{self.base_url}/api/v1/processing/load",
            json=payload
        )
        return response.json()
    
    def get_result(self, result_id):
        """获取结果详情"""
        response = requests.get(
            f"{self.base_url}/api/v1/processing/results/detail/{result_id}"
        )
        return response.json()
    
    def download_result(self, result_id, output_path):
        """下载结果JSON"""
        response = requests.get(
            f"{self.base_url}/api/v1/processing/results/detail/{result_id}"
        )
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(response.text)

# 使用示例
client = LoadingClient()

# 上传并加载
result = client.upload_document("document.pdf")
document_id = result["data"]["id"]

result = client.load_document(document_id)
result_id = result["data"]["id"]

# 获取结果
result_data = client.get_result(result_id)
print(result_data["data"]["result_data"]["total_pages"])

# 下载结果
client.download_result(result_id, "result.json")
```

---

## 9. 最佳实践

### 9.1 错误处理
```python
def safe_load_document(document_id):
    try:
        result = client.load_document(document_id)
        if result["success"]:
            return result["data"]
        else:
            print(f"加载失败: {result['message']}")
            return None
    except requests.RequestException as e:
        print(f"网络错误: {e}")
        return None
```

### 9.2 批量处理
```python
def batch_load_documents(document_ids):
    results = []
    for doc_id in document_ids:
        try:
            result = client.load_document(doc_id)
            results.append(result)
        except Exception as e:
            print(f"加载 {doc_id} 失败: {e}")
    return results
```

### 9.3 重试机制
```python
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def load_with_retry(document_id):
    result = client.load_document(document_id)
    if not result["success"]:
        raise Exception(result["message"])
    return result["data"]
```
