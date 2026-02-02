# 文档分块 API 接口文档

**更新日期**: 2026-02-02  
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
8. [父子分块专用接口](#9-父子分块专用接口)
9. [混合分块与多模态接口](#10-混合分块与多模态接口)
10. [智能推荐接口](#11-智能推荐接口)
11. [参数推荐接口](#12-参数推荐接口)

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
        "description": "基于语义相似度智能切分，支持 Embedding 模型",
        "default_parameters": {
          "similarity_threshold": 0.3,
          "embedding_similarity_threshold": 0.7,
          "min_chunk_size": 300,
          "max_chunk_size": 1200,
          "use_embedding": true,
          "embedding_model": "bge-m3"
        },
        "is_active": true
      },
      {
        "id": "parent_child",
        "name": "父子分块",
        "type": "parent_child",
        "description": "生成两层分块结构，父块提供上下文，子块用于检索",
        "default_parameters": {
          "parent_chunk_size": 2000,
          "child_chunk_size": 500,
          "child_overlap": 50,
          "parent_overlap": 200
        },
        "is_active": true
      },
      {
        "id": "hybrid",
        "name": "混合分块",
        "type": "hybrid",
        "description": "针对不同内容类型（正文、代码、表格、图片）应用最合适的策略",
        "default_parameters": {
          "text_strategy": "semantic",
          "text_chunk_size": 500,
          "text_overlap": 50,
          "embedding_model": "bge-m3",
          "use_embedding": true,
          "code_strategy": "lines",
          "code_chunk_lines": 50,
          "table_strategy": "independent",
          "min_table_rows": 2,
          "include_tables": true,
          "include_images": true,
          "include_code": true,
          "min_code_lines": 3
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

---

## 9. 父子分块专用接口

### 9.1 创建父子分块任务

**接口**: `POST /chunk`

**描述**: 使用父子分块策略创建分块任务

**请求体**:
```json
{
  "document_id": "doc_123",
  "strategy_type": "parent_child",
  "parameters": {
    "parent_chunk_size": 2000,
    "child_chunk_size": 500,
    "child_overlap": 50,
    "parent_overlap": 200
  }
}
```

**响应**:
```json
{
  "success": true,
  "message": "父子分块任务创建并完成",
  "data": {
    "task_id": "task_789",
    "status": "completed",
    "document_id": "doc_123",
    "strategy_type": "parent_child",
    "result_id": "result_999",
    "total_parent_chunks": 5,
    "total_child_chunks": 20,
    "created_at": "2025-12-08T10:30:00Z"
  }
}
```

### 9.2 获取父子分块结果

**接口**: `GET /result/{result_id}`

**描述**: 获取父子分块结果，包含父块和子块的层级关系

**响应**:
```json
{
  "success": true,
  "data": {
    "result_id": "result_999",
    "strategy_type": "parent_child",
    "total_parent_chunks": 5,
    "total_child_chunks": 20,
    "parent_chunks": [
      {
        "chunk_id": "parent_0",
        "sequence_number": 0,
        "content": "父块完整内容...",
        "chunk_type": "parent",
        "metadata": {
          "start_position": 0,
          "end_position": 2000,
          "child_count": 4,
          "child_ids": ["child_0_0", "child_0_1", "child_0_2", "child_0_3"]
        }
      }
    ],
    "child_chunks": [
      {
        "chunk_id": "child_0_0",
        "sequence_number": 0,
        "content": "子块内容...",
        "chunk_type": "child",
        "parent_id": "parent_0",
        "metadata": {
          "parent_sequence": 0,
          "child_sequence": 0,
          "start_position": 0,
          "end_position": 500
        }
      }
    ]
  }
}
```

### 9.3 通过子块ID获取父块

**接口**: `GET /chunk/{child_chunk_id}/parent`

**描述**: 根据子块ID获取对应的父块内容（用于检索后获取完整上下文）

**响应**:
```json
{
  "success": true,
  "data": {
    "child_chunk_id": "child_0_0",
    "parent_chunk": {
      "chunk_id": "parent_0",
      "content": "父块完整内容...",
      "metadata": {
        "child_count": 4,
        "child_ids": ["child_0_0", "child_0_1", "child_0_2", "child_0_3"]
      }
    }
  }
}
```

---

## 10. 混合分块与多模态接口

### 10.1 创建混合分块任务

**接口**: `POST /chunk`

**描述**: 使用混合分块策略，针对不同内容类型应用不同策略

**请求体**:
```json
{
  "document_id": "doc_123",
  "strategy_type": "hybrid",
  "parameters": {
    "text_strategy": "semantic",
    "text_chunk_size": 500,
    "text_overlap": 50,
    "embedding_model": "bge-m3",
    "use_embedding": true,
    "code_strategy": "lines",
    "code_chunk_lines": 50,
    "table_strategy": "independent",
    "min_table_rows": 2,
    "include_tables": true,
    "include_images": true,
    "include_code": true,
    "min_code_lines": 3
  }
}
```

**响应**:
```json
{
  "success": true,
  "message": "混合分块任务创建并完成",
  "data": {
    "task_id": "task_789",
    "status": "completed",
    "document_id": "doc_123",
    "strategy_type": "hybrid",
    "result_id": "result_999",
    "total_chunks": 35,
    "chunk_type_distribution": {
      "text": 25,
      "table": 5,
      "image": 3,
      "code": 2
    },
    "created_at": "2025-12-08T10:30:00Z"
  }
}
```

### 10.2 获取多模态分块结果

**接口**: `GET /result/{result_id}`

**描述**: 获取混合分块结果，包含不同类型的分块

**参数**:
- `chunk_type` (string, optional): 过滤分块类型(text/table/image/code)

**响应**:
```json
{
  "success": true,
  "data": {
    "result_id": "result_999",
    "strategy_type": "hybrid",
    "total_chunks": 35,
    "chunk_type_distribution": {
      "text": 25,
      "table": 5,
      "image": 3,
      "code": 2
    },
    "chunks": [
      {
        "chunk_id": "text_0",
        "chunk_type": "text",
        "content": "正文内容...",
        "metadata": {
          "strategy": "semantic",
          "char_count": 523
        }
      },
      {
        "chunk_id": "table_0",
        "chunk_type": "table",
        "content": "| 列1 | 列2 |\n|-----|-----|\n| 值1 | 值2 |",
        "metadata": {
          "row_count": 2,
          "column_count": 2,
          "headers": ["列1", "列2"],
          "page_number": 1
        }
      },
      {
        "chunk_id": "image_0",
        "chunk_type": "image",
        "content": "图片描述文本",
        "metadata": {
          "image_index": 0,
          "image_path": "/path/to/image.png",
          "image_base64": "iVBORw0KGgo...",
          "alt_text": "示例图片",
          "caption": "图1: 系统架构图",
          "width": 800,
          "height": 600,
          "mime_type": "image/png",
          "page_number": 1,
          "context_before": "前文上下文...",
          "context_after": "后文上下文..."
        }
      },
      {
        "chunk_id": "code_0",
        "chunk_type": "code",
        "content": "def example():\n    return 'Hello'",
        "metadata": {
          "language": "python",
          "line_count": 2,
          "page_number": 2
        }
      }
    ]
  }
}
```

### 10.3 按类型获取分块

**接口**: `GET /result/{result_id}/chunks/{chunk_type}`

**描述**: 获取指定类型的所有分块

**路径参数**:
- `chunk_type`: 分块类型(text/table/image/code)

**响应**:
```json
{
  "success": true,
  "data": {
    "chunk_type": "image",
    "total": 3,
    "chunks": [
      {
        "chunk_id": "image_0",
        "chunk_type": "image",
        "content": "图片描述文本",
        "metadata": {
          "image_index": 0,
          "image_path": "/path/to/image.png",
          "image_base64": "iVBORw0KGgo...",
          "alt_text": "示例图片",
          "width": 800,
          "height": 600
        }
      }
    ]
  }
}
```

---

## 11. 智能推荐接口

### 11.1 获取分块策略推荐

**接口**: `POST /recommend`

**描述**: 根据文档特征推荐最佳分块策略

**请求体**:
```json
{
  "document_id": "doc_123"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "document_id": "doc_123",
    "document_name": "技术文档.pdf",
    "document_features": {
      "has_headings": true,
      "heading_count": {
        "h1": 3,
        "h2": 12,
        "h3": 25
      },
      "has_tables": true,
      "table_count": 5,
      "has_images": true,
      "image_count": 8,
      "has_code_blocks": true,
      "code_block_count": 10,
      "total_chars": 50000,
      "avg_paragraph_length": 300
    },
    "recommended_strategy": {
      "strategy_type": "hybrid",
      "confidence": 0.95,
      "reason": "文档包含多种内容类型（标题、表格、图片、代码），建议使用混合分块策略",
      "parameters": {
        "text_strategy": "heading",
        "code_strategy": "lines",
        "table_strategy": "independent",
        "include_tables": true,
        "include_images": true,
        "include_code": true
      }
    },
    "alternative_strategies": [
      {
        "strategy_type": "heading",
        "confidence": 0.75,
        "reason": "文档有清晰的标题层级结构"
      },
      {
        "strategy_type": "semantic",
        "confidence": 0.60,
        "reason": "文档内容连贯，适合语义分块"
      }
    ]
  }
}
```

### 11.2 预览分块效果

**接口**: `POST /preview`

**描述**: 预览分块效果（使用文档前 10% 内容进行试分块）

**请求体**:
```json
{
  "document_id": "doc_123",
  "strategy_type": "hybrid",
  "parameters": {
    "text_strategy": "semantic",
    "text_chunk_size": 500
  }
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "preview_text_length": 5000,
    "preview_percentage": 10,
    "estimated_total_chunks": 35,
    "preview_chunks": [
      {
        "chunk_id": "preview_0",
        "chunk_type": "text",
        "content": "预览块内容...",
        "char_count": 523
      }
    ],
    "statistics": {
      "avg_chunk_size": 500,
      "max_chunk_size": 650,
      "min_chunk_size": 350,
      "chunk_type_distribution": {
        "text": 3,
        "table": 1,
        "image": 0
      }
    },
    "estimated_processing_time": 12.5
  }
}
```

---

## 12. 参数推荐接口

### 12.1 获取格式相关参数推荐

**接口**: `GET /format-params`

**描述**: 根据文档格式获取推荐的分块参数

**参数**:
- `document_format` (string, optional): 文档格式(pdf/csv/docx/xlsx等)
- `char_count` (int, optional): 文档字符数

**响应**:
```json
{
  "success": true,
  "data": {
    "format": "csv",
    "recommended_params": {
      "chunk_size": 800,
      "overlap": 50,
      "text_strategy": "paragraph"
    }
  }
}
```

### 12.2 获取智能参数推荐

**接口**: `GET /smart-params`

**描述**: 根据文档特征获取智能参数推荐

**参数**:
- `strategy_type` (string, required): 策略类型(character/paragraph/heading/semantic/parent_child/hybrid)
- `document_format` (string, default="default"): 文档格式
- `char_count` (int, default=10000): 文档字符数
- `embedding_model` (string, default="bge-m3"): Embedding模型
- `code_block_ratio` (float, default=0.0): 代码块比例(0-1)
- `table_count` (int, default=0): 表格数量
- `image_count` (int, default=0): 图片数量
- `heading_count` (int, default=0): 标题数量

**响应**:
```json
{
  "success": true,
  "data": {
    "strategy_type": "hybrid",
    "parameters": {
      "text_strategy": "semantic",
      "text_chunk_size": 500,
      "embedding_model": "bge-m3",
      "include_tables": true,
      "include_images": true,
      "include_code": true
    },
    "reasoning": "文档包含表格和图片，推荐使用混合分块策略"
  }
}
```

### 12.3 获取Embedding参数推荐

**接口**: `GET /embedding-params`

**描述**: 获取Embedding相关的参数推荐

**参数**:
- `model` (string, default="bge-m3"): Embedding模型名称

**响应**:
```json
{
  "success": true,
  "data": {
    "model": "bge-m3",
    "dimensions": 1024,
    "max_tokens": 8192,
    "recommended_similarity_threshold": 0.7,
    "batch_size": 32
  }
}
```

---

## 13. 其他接口

### 13.1 获取任务队列状态

**接口**: `GET /queue`

**描述**: 获取当前分块任务队列状态

**响应**:
```json
{
  "success": true,
  "data": {
    "pending_tasks": 2,
    "running_tasks": 1,
    "queue": [
      {
        "task_id": "task_001",
        "document_name": "文档1.pdf",
        "strategy_type": "semantic",
        "status": "running",
        "queue_position": 0
      },
      {
        "task_id": "task_002",
        "document_name": "文档2.docx",
        "strategy_type": "paragraph",
        "status": "pending",
        "queue_position": 1
      }
    ]
  }
}
```

### 13.2 批量删除分块结果

**接口**: `POST /results/batch-delete`

**描述**: 批量删除多个分块结果

**请求体**:
```json
{
  "result_ids": ["result_001", "result_002", "result_003"]
}
```

**响应**:
```json
{
  "success": true,
  "message": "成功删除 3 个结果",
  "data": {
    "deleted_count": 3,
    "failed_count": 0
  }
}
```

### 13.3 分析文档特征

**接口**: `POST /analyze`

**描述**: 分析文档特征，用于策略推荐

**请求体**:
```json
{
  "document_id": "doc_123"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "document_id": "doc_123",
    "features": {
      "total_chars": 50000,
      "heading_count": 15,
      "paragraph_count": 80,
      "table_count": 5,
      "image_count": 8,
      "code_block_count": 10,
      "code_block_ratio": 0.15,
      "avg_paragraph_length": 500
    }
  }
}
```

---

## 14. 状态码说明

| 状态码 | 说明 |
|-------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

