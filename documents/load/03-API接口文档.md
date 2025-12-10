# 文档加载 API 接口文档

**生成日期**: 2025-12-10  
**项目**: RAG Framework - 文档加载模块  
**基础路径**: `/api`

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

**接口**: `POST /documents/upload`

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
  http://localhost:8000/api/documents/upload \
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

**描述**: 获取已上传的文档列表

**参数**:
- `page` (int, default=1): 页码
- `page_size` (int, default=20): 每页数量
- `search` (string, optional): 文件名搜索
- `format` (string, optional): 格式过滤(pdf/docx/doc/txt/md)
- `status` (string, optional): 状态过滤(uploaded/processing/ready/error)
- `sort_by` (string, default="upload_time"): 排序字段
- `sort_order` (string, default="desc"): 排序方向(asc/desc)

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
        "last_processed": "2025-12-10T10:05:00Z"
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

### 3.1 加载文档

**接口**: `POST /loading/load`

**描述**: 对已上传的文档执行加载操作,提取文本内容

**请求体**:
```json
{
  "document_id": "doc_123456",
  "loader_type": "pymupdf"
}
```

**参数说明**:
- `document_id` (string, required): 文档ID
- `loader_type` (string, optional): 加载器类型
  - `null` 或空: 自动选择(推荐)
  - `"pymupdf"`: PyMuPDF加载器
  - `"pypdf"`: PyPDF加载器
  - `"unstructured"`: Unstructured加载器
  - `"docx"`: DOCX加载器
  - `"doc"`: DOC加载器
  - `"text"`: 文本加载器

**响应**:
```json
{
  "success": true,
  "message": "Document loaded successfully",
  "data": {
    "id": "result_789",
    "document_id": "doc_123456",
    "processing_type": "load",
    "provider": "pymupdf",
    "status": "completed",
    "result_path": "/path/to/results/load/doc_123456_pymupdf_20251210_100500.json",
    "extra_metadata": {
      "total_pages": 10,
      "total_chars": 5234,
      "loader_type": "pymupdf",
      "file_format": "pdf"
    },
    "created_at": "2025-12-10T10:05:00Z"
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

## 4. 结果查询接口

### 4.1 获取处理结果列表

**接口**: `GET /processing/results`

**描述**: 获取指定文档的处理结果列表

**参数**:
- `document_id` (string, required): 文档ID
- `processing_type` (string, optional): 处理类型(load/parse/chunk等)

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": "result_789",
      "document_id": "doc_123456",
      "processing_type": "load",
      "provider": "pymupdf",
      "status": "completed",
      "created_at": "2025-12-10T10:05:00Z",
      "extra_metadata": {
        "total_pages": 10,
        "total_chars": 5234
      }
    }
  ]
}
```

---

### 4.2 获取处理结果详情

**接口**: `GET /processing/results/{result_id}`

**描述**: 获取指定处理结果的详细信息,包括完整的结果数据

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

**接口**: `GET /processing/results/{result_id}/download`

**描述**: 下载处理结果的JSON文件

**响应**: JSON文件下载

**Content-Type**: `application/json`

**文件名**: `{document_name}_{processing_type}_result.json`

---

## 5. 加载器信息接口

### 5.1 获取可用加载器列表

**接口**: `GET /loading/loaders`

**描述**: 获取系统中可用的所有加载器及其支持的格式

**响应**:
```json
{
  "success": true,
  "data": {
    "loaders": [
      "pymupdf",
      "pypdf",
      "unstructured",
      "docx",
      "doc",
      "text"
    ],
    "supported_formats": [
      "pdf",
      "docx",
      "doc",
      "txt",
      "md",
      "markdown"
    ],
    "format_loader_map": {
      "pdf": "pymupdf",
      "docx": "docx",
      "doc": "doc",
      "txt": "text",
      "md": "text",
      "markdown": "text"
    }
  }
}
```

---

### 5.2 获取加载器详细信息

**接口**: `GET /loading/loaders/{loader_type}`

**描述**: 获取指定加载器的详细信息

**响应**:
```json
{
  "success": true,
  "data": {
    "name": "pymupdf",
    "display_name": "PyMuPDF",
    "description": "高性能PDF加载器,支持文本提取和元数据读取",
    "supported_formats": ["pdf"],
    "features": [
      "文本提取",
      "元数据提取",
      "图片提取",
      "页面信息"
    ],
    "performance": "excellent",
    "recommended": true,
    "dependencies": ["PyMuPDF>=1.23.8"]
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
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@document.pdf"
# 返回: {"success":true,"data":{"id":"doc_123456",...}}

# 2. 自动加载文档
curl -X POST http://localhost:8000/api/loading/load \
  -H "Content-Type: application/json" \
  -d '{"document_id":"doc_123456"}'
# 返回: {"success":true,"data":{"id":"result_789",...}}

# 3. 获取结果详情
curl http://localhost:8000/api/processing/results/result_789
# 返回完整的加载结果数据

# 4. 下载结果JSON
curl http://localhost:8000/api/processing/results/result_789/download \
  -o result.json
```

### 8.2 指定加载器加载

```bash
# 使用PyPDF加载器
curl -X POST http://localhost:8000/api/loading/load \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc_123456",
    "loader_type": "pypdf"
  }'
```

### 8.3 查询文档列表

```bash
# 查询PDF格式的文档
curl "http://localhost:8000/api/documents?format=pdf&page=1&page_size=10"

# 搜索文件名包含"report"的文档
curl "http://localhost:8000/api/documents?search=report"

# 获取状态为ready的文档
curl "http://localhost:8000/api/documents?status=ready"
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
                f"{self.base_url}/api/documents/upload",
                files=files
            )
        return response.json()
    
    def load_document(self, document_id, loader_type=None):
        """加载文档"""
        payload = {"document_id": document_id}
        if loader_type:
            payload["loader_type"] = loader_type
        
        response = requests.post(
            f"{self.base_url}/api/loading/load",
            json=payload
        )
        return response.json()
    
    def get_result(self, result_id):
        """获取结果详情"""
        response = requests.get(
            f"{self.base_url}/api/processing/results/{result_id}"
        )
        return response.json()
    
    def download_result(self, result_id, output_path):
        """下载结果JSON"""
        response = requests.get(
            f"{self.base_url}/api/processing/results/{result_id}/download"
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
