# 文档分块 API 接口文档

**生成日期**: 2025-12-08  
**项目**: RAG Framework - 文档分块模块  
**基础路径**: `/api/chunking`

---

## 目录

1. [通用说明](#1-通用说明)
2. [文档相关接口](#2-文档相关接口)
3. [策略相关接口](#3-策略相关接口)
4. [分块任务接口](#4-分块任务接口)
5. [结果查询接口](#5-结果查询接口)
6. [历史管理接口](#6-历史管理接口)
7. [版本管理接口](#7-版本管理接口)

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

目前无需认证，后续版本可能添加Token认证。

---

## 2. 文档相关接口

### 2.1 获取已解析文档列表

**接口**: `GET /documents/parsed`

**描述**: 获取已加载/解析的文档列表，可用于分块

**参数**:
- `page` (int, default=1): 页码
- `page_size` (int, default=20): 每页数量
- `search` (string, optional): 文件名搜索
- `format` (string, optional): 格式过滤(pdf/docx/txt/md)
- `sort_by` (string, default="upload_time"): 排序字段
- `sort_order` (string, default="desc"): 排序方向(asc/desc)

**响应**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "doc_123",
        "filename": "示例文档.pdf",
        "format": "pdf",
        "size_bytes": 1024000,
        "upload_time": "2025-12-08T10:00:00Z",
        "processing_type": "parsed",
        "processing_result": {
          "id": "result_456",
          "result_path": "/path/to/result.json",
          "created_at": "2025-12-08T10:05:00Z"
        }
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

## 3. 策略相关接口

### 3.1 获取可用策略列表

**接口**: `GET /strategies`

**描述**: 获取所有可用的分块策略

**参数**:
- `active_only` (bool, default=true): 只返回启用的策略

**响应**:
```json
{
  "success": true,
  "data": {
    "strategies": [
      {
        "id": "character",
        "name": "按字数分块",
        "type": "character",
        "description": "按固定字符数切分文本",
        "default_parameters": {
          "chunk_size": 500,
          "overlap": 50
        },
        "is_active": true
      },
      {
        "id": "paragraph",
        "name": "按段落分块",
        "type": "paragraph",
        "description": "按段落边界切分，合并小段落",
        "default_parameters": {
          "min_chunk_size": 300,
          "max_chunk_size": 1200
        },
        "is_active": true
      },
      {
        "id": "heading",
        "name": "按标题分块",
        "type": "heading",
        "description": "按Markdown标题层级切分",
        "default_parameters": {
          "min_heading_level": 1,
          "max_heading_level": 3
        },
        "is_active": true
      },
      {
        "id": "semantic",
        "name": "按语义分块",
        "type": "semantic",
        "description": "基于语义相似度智能切分",
        "default_parameters": {
          "similarity_threshold": 0.3,
          "min_chunk_size": 300,
          "max_chunk_size": 1200
        },
        "is_active": true
      }
    ]
  }
}
```

---

## 4. 分块任务接口

### 4.1 创建分块任务

**接口**: `POST /chunk`

**描述**: 创建新的分块任务，支持智能版本管理

**参数**:
- `overwrite_mode` (string, default="auto"): 覆盖模式
  - `auto`: 智能判断(参数微调→覆盖，大改→新建)
  - `always`: 总是覆盖同策略的旧结果
  - `never`: 总是新建版本

**请求体**:
```json
{
  "document_id": "doc_123",
  "strategy_type": "character",
  "parameters": {
    "chunk_size": 500,
    "overlap": 50
  }
}
```

**响应**:
```json
{
  "success": true,
  "message": "分块任务创建并完成",
  "data": {
    "task_id": "task_789",
    "status": "completed",
    "document_id": "doc_123",
    "strategy_type": "character",
    "parameters": {
      "chunk_size": 500,
      "overlap": 50
    },
    "queue_position": 0,
    "result_id": "result_999",
    "total_chunks": 15,
    "version": 2,
    "is_active": true,
    "previous_version_id": "result_888",
    "replacement_reason": "Auto-optimization: 参数微调(overlap: 100 → 50)",
    "created_at": "2025-12-08T10:30:00Z"
  }
}
```

### 4.2 查询任务状态

**接口**: `GET /task/{task_id}`

**描述**: 查询指定任务的状态

**响应**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_789",
    "status": "completed",
    "document_id": "doc_123",
    "strategy_type": "character",
    "parameters": {...},
    "queue_position": 0,
    "error_message": null,
    "created_at": "2025-12-08T10:30:00Z",
    "started_at": "2025-12-08T10:30:05Z",
    "completed_at": "2025-12-08T10:30:15Z",
    "result_id": "result_999",
    "total_chunks": 15
  }
}
```

---

## 5. 结果查询接口

### 5.1 获取分块结果详情

**接口**: `GET /result/{result_id}`

**描述**: 获取分块结果详细信息

**参数**:
- `include_chunks` (bool, default=true): 是否包含chunks内容
- `page` (int, default=1): chunks分页页码
- `page_size` (int, default=50): 每页chunks数量

**响应**:
```json
{
  "success": true,
  "data": {
    "result_id": "result_999",
    "task_id": "task_789",
    "document_id": "doc_123",
    "document_name": "示例文档.pdf",
    "strategy_type": "character",
    "parameters": {
      "chunk_size": 500,
      "overlap": 50
    },
    "status": "completed",
    "total_chunks": 15,
    "statistics": {
      "total_chunks": 15,
      "total_chars": 7845,
      "avg_chunk_size": 523,
      "max_chunk_size": 550,
      "min_chunk_size": 280
    },
    "file_path": "/path/to/result.json",
    "created_at": "2025-12-08T10:30:15Z",
    "chunks": {
      "items": [
        {
          "id": "chunk_1",
          "sequence_number": 0,
          "content": "这是第一个文本块的内容...",
          "metadata": {
            "start_position": 0,
            "end_position": 523,
            "char_count": 523,
            "strategy": "character"
          },
          "start_position": 0,
          "end_position": 523,
          "token_count": 523
        }
      ],
      "total": 15,
      "page": 1,
      "page_size": 50,
      "pages": 1
    }
  }
}
```

### 5.2 获取文档最新结果

**接口**: `GET /result/latest/{document_id}`

**描述**: 获取文档的最新分块结果，支持策略和参数过滤

**参数**:
- `strategy_type` (string, optional): 策略类型过滤
- `parameters` (string, optional): 参数过滤(JSON字符串)

**响应**:
```json
{
  "success": true,
  "data": {
    "result_id": "result_999",
    "task_id": "task_789",
    "document_id": "doc_123",
    "document_name": "示例文档.pdf",
    "strategy_type": "character",
    "parameters": {...},
    "status": "completed",
    "total_chunks": 15,
    "statistics": {...},
    "version": 2,
    "is_active": true,
    "processing_time": 10.5,
    "created_at": "2025-12-08T10:30:15Z"
  }
}
```

---

## 6. 历史管理接口

### 6.1 获取分块历史

**接口**: `GET /history`

**描述**: 获取所有分块历史记录，支持过滤、排序、分页

**参数**:
- `page` (int, default=1): 页码
- `page_size` (int, default=20): 每页数量
- `document_name` (string, optional): 文档名过滤
- `strategy` (string, optional): 策略类型过滤
- `status` (string, optional): 状态过滤
- `date_from` (string, optional): 开始日期(ISO格式)
- `date_to` (string, optional): 结束日期
- `active_only` (bool, default=true): 只显示激活版本
- `sort_by` (string, default="created_at"): 排序字段
- `sort_order` (string, default="desc"): 排序方向

**响应**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "result_id": "result_999",
        "document_id": "doc_123",
        "document_name": "示例文档.pdf",
        "strategy_type": "character",
        "status": "completed",
        "total_chunks": 15,
        "processing_time": 10.5,
        "file_size": 52000,
        "statistics": {...},
        "version": 2,
        "is_active": true,
        "previous_version_id": "result_888",
        "replacement_reason": "参数优化",
        "created_at": "2025-12-08T10:30:15Z"
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "pages": 5
  }
}
```

### 6.2 删除分块结果

**接口**: `DELETE /result/{result_id}`

**描述**: 删除指定的分块结果(数据库记录+文件)

**响应**:
```json
{
  "success": true,
  "message": "Result deleted successfully",
  "data": null
}
```

### 6.3 导出分块结果

**接口**: `GET /export/{result_id}`

**描述**: 导出分块结果为JSON或CSV格式

**参数**:
- `format` (string, default="json"): 导出格式(json/csv)

**响应**: 文件下载

---

## 7. 版本管理接口

### 7.1 获取版本历史

**接口**: `GET /versions/{document_id}/{strategy_type}`

**描述**: 获取指定文档和策略的所有版本

**响应**:
```json
{
  "success": true,
  "data": {
    "document_id": "doc_123",
    "strategy_type": "character",
    "total_versions": 3,
    "active_version": {
      "result_id": "result_999",
      "version": 3,
      "is_active": true,
      "total_chunks": 15,
      "parameters": {...},
      "processing_time": 10.5,
      "statistics": {...},
      "previous_version_id": "result_888",
      "replacement_reason": "参数优化",
      "created_at": "2025-12-08T10:30:15Z"
    },
    "versions": [
      {
        "result_id": "result_999",
        "version": 3,
        "is_active": true,
        ...
      },
      {
        "result_id": "result_888",
        "version": 2,
        "is_active": false,
        ...
      },
      {
        "result_id": "result_777",
        "version": 1,
        "is_active": false,
        ...
      }
    ]
  }
}
```

### 7.2 激活指定版本

**接口**: `POST /versions/{result_id}/activate`

**描述**: 激活指定版本(将其他版本设为非激活)

**响应**:
```json
{
  "success": true,
  "message": "Version 2 activated successfully",
  "data": {
    "result_id": "result_888",
    "version": 2,
    "is_active": true
  }
}
```

### 7.3 对比多个结果

**接口**: `POST /compare`

**描述**: 对比2-5个分块结果

**请求体**:
```json
{
  "result_ids": ["result_99", "result_100", "result_101"]
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "result_id": "result_99",
        "document_name": "示例.pdf",
        "strategy_type": "character",
        "total_chunks": 15,
        "processing_time": 10.5,
        "statistics": {...},
        "parameters": {...}
      }
    ],
    "statistics_comparison": {
      "avg_chunk_sizes": [523, 650, 400],
      "max_chunk_sizes": [550, 700, 500],
      "min_chunk_sizes": [280, 400, 200],
      "total_chunks": [15, 12, 20],
      "processing_times": [10.5, 15.2, 8.3]
    },
    "recommendations": [
      "最快处理: character (10.5s)",
      "最均衡分块: semantic"
    ]
  }
}
```

---

## 8. 状态码说明

| 状态码 | 说明 |
|-------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

