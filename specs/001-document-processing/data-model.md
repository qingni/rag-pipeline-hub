# Data Model: 文档处理和检索系统

**Date**: 2025-12-01  
**Feature**: 001-document-processing  
**Phase**: 1 - Design & Contracts

## 概述

本文档定义了文档处理和检索系统的完整数据模型，包括实体定义、关系、验证规则和状态转换。

## 核心实体

### 1. Document (文档)

**描述**: 表示用户上传的原始文档

**属性**:
| 字段 | 类型 | 必填 | 描述 | 验证规则 |
|------|------|------|------|----------|
| id | UUID | 是 | 文档唯一标识 | UUID v4 |
| filename | String(255) | 是 | 原始文件名 | 非空，长度 1-255 |
| format | String(50) | 是 | 文件格式 | 枚举: pdf, doc, docx, txt |
| size_bytes | Integer | 是 | 文件大小（字节） | > 0, <= 52428800 (50MB) |
| upload_time | DateTime | 是 | 上传时间 | ISO 8601 格式 |
| storage_path | String | 是 | 文件存储路径 | 有效路径 |
| content_hash | String(64) | 否 | 文件SHA256哈希 | 64字符十六进制 |
| status | String(20) | 是 | 文档状态 | 枚举: uploaded, processing, ready, error |

**状态转换**:
```
uploaded -> processing -> ready
         -> processing -> error
```

**索引**:
- 主键: id
- 索引: upload_time (降序)
- 索引: status

### 2. ProcessingResult (处理结果)

**描述**: 表示文档处理的结果记录

**属性**:
| 字段 | 类型 | 必填 | 描述 | 验证规则 |
|------|------|------|------|----------|
| id | UUID | 是 | 结果唯一标识 | UUID v4 |
| document_id | UUID | 是 | 关联文档ID | 外键: Document.id |
| processing_type | String(50) | 是 | 处理类型 | 枚举: load, parse, chunk, embed, index, generate |
| provider | String(50) | 否 | 使用的提供商 | 如: pymupdf, openai, milvus |
| result_path | String | 是 | JSON结果文件路径 | {filename}_{timestamp}_{type}.json |
| metadata | JSON | 否 | 处理元数据 | 有效JSON对象 |
| created_at | DateTime | 是 | 创建时间 | ISO 8601 格式 |
| status | String(20) | 是 | 处理状态 | 枚举: pending, running, completed, failed |
| error_message | String | 否 | 错误信息 | 仅status=failed时 |

**关系**:
- 多对一: Document (一个文档可以有多个处理结果)

**索引**:
- 主键: id
- 外键索引: document_id
- 复合索引: (document_id, processing_type, created_at)

### 3. DocumentChunk (文档分块)

**描述**: 表示文档分块后的片段

**属性**:
| 字段 | 类型 | 必填 | 描述 | 验证规则 |
|------|------|------|------|----------|
| id | UUID | 是 | 分块唯一标识 | UUID v4 |
| document_id | UUID | 是 | 关联文档ID | 外键: Document.id |
| processing_result_id | UUID | 是 | 关联处理结果ID | 外键: ProcessingResult.id |
| chunk_index | Integer | 是 | 分块序号 | >= 0 |
| content | Text | 是 | 分块文本内容 | 非空 |
| char_count | Integer | 是 | 字符数 | > 0 |
| strategy | String(50) | 是 | 分块策略 | 如: paragraph, fixed, semantic |
| metadata | JSON | 否 | 分块元数据 | 页码、章节等信息 |
| created_at | DateTime | 是 | 创建时间 | ISO 8601 格式 |

**关系**:
- 多对一: Document
- 多对一: ProcessingResult
- 一对一: VectorEmbedding (可选)

**索引**:
- 主键: id
- 复合索引: (document_id, chunk_index)
- 外键索引: processing_result_id

### 4. VectorEmbedding (向量嵌入)

**描述**: 表示文本块的向量表示

**属性**:
| 字段 | 类型 | 必填 | 描述 | 验证规则 |
|------|------|------|------|----------|
| id | UUID | 是 | 嵌入唯一标识 | UUID v4 |
| chunk_id | UUID | 是 | 关联分块ID | 外键: DocumentChunk.id |
| processing_result_id | UUID | 是 | 关联处理结果ID | 外键: ProcessingResult.id |
| provider | String(50) | 是 | 嵌入提供商 | 枚举: openai, bedrock, huggingface |
| model_name | String(100) | 是 | 模型名称 | 如: text-embedding-ada-002 |
| dimension | Integer | 是 | 向量维度 | > 0, 如: 1536 |
| vector | Binary/JSON | 是 | 向量数据 | 浮点数数组 |
| created_at | DateTime | 是 | 创建时间 | ISO 8601 格式 |

**关系**:
- 一对一: DocumentChunk
- 多对一: ProcessingResult

**索引**:
- 主键: id
- 唯一索引: chunk_id (每个分块只有一个嵌入)
- 索引: provider, model_name

**说明**: 向量数据实际存储在向量数据库中，此表仅存储元数据和引用

### 5. SearchQuery (搜索查询)

**描述**: 表示用户的搜索查询记录

**属性**:
| 字段 | 类型 | 必填 | 描述 | 验证规则 |
|------|------|------|------|----------|
| id | UUID | 是 | 查询唯一标识 | UUID v4 |
| query_text | String | 是 | 查询文本 | 非空，长度 1-500 |
| search_type | String(20) | 是 | 搜索类型 | 枚举: similarity, semantic |
| filter_conditions | JSON | 否 | 过滤条件 | 有效JSON对象 |
| top_k | Integer | 是 | 返回结果数 | 1-100 |
| vector_provider | String(50) | 是 | 使用的向量提供商 | 与嵌入提供商对应 |
| created_at | DateTime | 是 | 查询时间 | ISO 8601 格式 |
| response_time_ms | Integer | 否 | 响应时间（毫秒） | >= 0 |

**索引**:
- 主键: id
- 索引: created_at (降序)
- 索引: search_type

### 6. SearchResult (搜索结果)

**描述**: 表示搜索查询的结果项

**属性**:
| 字段 | 类型 | 必填 | 描述 | 验证规则 |
|------|------|------|------|----------|
| id | UUID | 是 | 结果唯一标识 | UUID v4 |
| query_id | UUID | 是 | 关联查询ID | 外键: SearchQuery.id |
| chunk_id | UUID | 是 | 关联分块ID | 外键: DocumentChunk.id |
| score | Float | 是 | 相似度分数 | 0.0-1.0 |
| rank | Integer | 是 | 排名 | >= 1 |

**关系**:
- 多对一: SearchQuery
- 多对一: DocumentChunk

**索引**:
- 主键: id
- 复合索引: (query_id, rank)

### 7. GenerationTask (文本生成任务)

**描述**: 表示文本生成任务

**属性**:
| 字段 | 类型 | 必填 | 描述 | 验证规则 |
|------|------|------|------|----------|
| id | UUID | 是 | 任务唯一标识 | UUID v4 |
| context_chunks | JSON | 是 | 上下文分块ID数组 | UUID数组 |
| prompt | Text | 是 | 生成提示词 | 非空 |
| model_provider | String(50) | 是 | 模型提供商 | 枚举: ollama, huggingface |
| model_name | String(100) | 是 | 模型名称 | 如: llama2, mistral |
| parameters | JSON | 否 | 生成参数 | temperature, max_tokens等 |
| output | Text | 否 | 生成结果 | 任务完成后填充 |
| created_at | DateTime | 是 | 创建时间 | ISO 8601 格式 |
| completed_at | DateTime | 否 | 完成时间 | ISO 8601 格式 |
| status | String(20) | 是 | 任务状态 | 枚举: pending, running, completed, failed |
| error_message | String | 否 | 错误信息 | 仅status=failed时 |

**状态转换**:
```
pending -> running -> completed
        -> running -> failed
```

**索引**:
- 主键: id
- 索引: status
- 索引: created_at (降序)

## 实体关系图 (ER Diagram)

```
Document (1) ----< (N) ProcessingResult
    |                       |
    |                       |
    +----< (N) DocumentChunk (1) ---- (1) VectorEmbedding
                |
                |
                +----< (N) SearchResult (N) >---- (1) SearchQuery

GenerationTask (独立实体，通过context_chunks JSON字段关联DocumentChunk)
```

## 数据验证规则

### 文件上传验证
- 文件大小：<= 50MB (52428800 bytes)
- 文件格式：pdf, doc, docx, txt (白名单)
- 文件名：移除特殊字符，保留字母数字和常用符号

### JSON 结果存储规范
- 文件名格式：`{document_filename}_{timestamp}_{processing_type}.json`
- 时间戳格式：`YYYYMMDDHHmmss`
- 示例：`report_20251201120000_parsed.json`

### 向量维度验证
- OpenAI text-embedding-ada-002: 1536
- HuggingFace (可变): 通常 384, 768, 1024
- 存储前验证维度与模型匹配

## 数据生命周期

### 文档处理流程
1. **Upload** -> Document (status: uploaded)
2. **Load** -> ProcessingResult (type: load)
3. **Parse** -> ProcessingResult (type: parse)
4. **Chunk** -> DocumentChunk + ProcessingResult (type: chunk)
5. **Embed** -> VectorEmbedding + ProcessingResult (type: embed)
6. **Index** -> 向量数据库 + ProcessingResult (type: index)

### 搜索流程
1. **Query** -> SearchQuery
2. **Vector Search** -> 向量数据库查询
3. **Results** -> SearchResult (关联DocumentChunk)

### 生成流程
1. **Select Context** -> 选择 DocumentChunk
2. **Create Task** -> GenerationTask (status: pending)
3. **Generate** -> 调用AI模型 (status: running)
4. **Complete** -> 保存输出 (status: completed)

## 性能考虑

### 查询优化
- Document: 按 upload_time 降序索引（最近上传）
- ProcessingResult: 复合索引 (document_id, processing_type, created_at)
- DocumentChunk: 复合索引 (document_id, chunk_index)

### 存储估算
- Document: ~200 bytes/record
- ProcessingResult: ~300 bytes/record
- DocumentChunk: ~2KB/record (含content)
- VectorEmbedding: ~6KB/record (1536维 * 4bytes)
- 1000个文档 * 平均50个chunks = 50,000个chunks ≈ 100MB + 300MB(向量) = 400MB

### 数据清理策略
- 定期清理失败的ProcessingResult（保留最近7天）
- 定期清理未完成的GenerationTask（保留最近24小时）
- 提供文档删除时的级联删除功能

## 总结

数据模型完全支持6个核心功能模块的需求，遵循宪章中的模块化和结果持久化原则。所有实体定义清晰，关系明确，验证规则完善，为后续API设计和实现提供坚实基础。
