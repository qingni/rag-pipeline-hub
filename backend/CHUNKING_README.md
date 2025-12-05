# 文档分块模块 (Document Chunking)

## 概述

文档分块模块提供灵活的文档切分功能，支持多种分块策略，适用于不同类型的文档和使用场景。

## 功能特性

### ✅ 核心功能
- **4种分块策略**: 按字数、按段落、按标题、按语义
- **实时预览**: 分块前预览效果和估算块数
- **历史管理**: 查看、对比、导出历史分块结果
- **队列管理**: 最多3个并发任务，自动队列排队
- **灵活配置**: 每种策略支持自定义参数

### 📊 分块策略

#### 1. 按字数分块 (Character-based)
- **适用场景**: 通用文本、无明显结构的文档
- **参数**:
  - `chunk_size`: 块大小（100-5000字符）
  - `overlap`: 重叠度（0-30%）
- **特点**: 简单高效，分块均匀

#### 2. 按段落分块 (Paragraph-based)
- **适用场景**: 有段落结构的文档、文章
- **参数**:
  - `min_chunk_size`: 最小块大小（50-2000字符）
  - `max_chunk_size`: 最大块大小（500-10000字符）
- **特点**: 保持段落完整性，语义连贯

#### 3. 按标题分块 (Heading-based)
- **适用场景**: Markdown、HTML等结构化文档
- **参数**:
  - `min_heading_level`: 最小标题层级（H1-H6）
  - `max_heading_level`: 最大标题层级（H1-H6）
- **特点**: 按文档逻辑结构分块
- **降级机制**: 无标题时自动降级为段落分块

#### 4. 按语义分块 (Semantic-based)
- **适用场景**: 长文本、需要保持语义一致性
- **参数**:
  - `similarity_threshold`: 相似度阈值（0.3-0.9）
  - `min_chunk_size`: 最小块大小（100-2000字符）
- **特点**: 基于TF-IDF的语义相似度分块
- **降级机制**: 语义分析失败时降级为句子分块

## API 端点

### 文档和策略
- `GET /api/v1/chunking/documents/parsed` - 获取已解析文档列表
- `GET /api/v1/chunking/strategies` - 获取可用分块策略

### 分块操作
- `POST /api/v1/chunking/chunk` - 创建分块任务
- `POST /api/v1/chunking/preview` - 预览分块效果（不保存）
- `GET /api/v1/chunking/task/{task_id}` - 查询任务状态
- `GET /api/v1/chunking/result/{result_id}` - 获取分块结果

### 历史管理
- `GET /api/v1/chunking/history` - 获取历史记录（支持筛选、排序、分页）
- `POST /api/v1/chunking/compare` - 对比多个分块结果
- `GET /api/v1/chunking/export/{result_id}` - 导出结果（JSON/CSV）
- `DELETE /api/v1/chunking/result/{result_id}` - 删除结果

### 队列管理
- `GET /api/v1/chunking/queue` - 获取队列状态

## 使用示例

### 1. 创建分块任务

```python
import requests

# 创建按字数分块任务
response = requests.post('http://localhost:8000/api/v1/chunking/chunk', json={
    "document_id": "doc_123",
    "strategy_type": "character",
    "parameters": {
        "chunk_size": 500,
        "overlap": 50
    }
})

task = response.json()['data']
print(f"任务ID: {task['task_id']}")
```

### 2. 查询任务状态

```python
task_id = "task_456"
response = requests.get(f'http://localhost:8000/api/v1/chunking/task/{task_id}')
status = response.json()['data']

print(f"状态: {status['status']}")
print(f"块数: {status.get('total_chunks', 0)}")
```

### 3. 获取分块结果

```python
result_id = "result_789"
response = requests.get(
    f'http://localhost:8000/api/v1/chunking/result/{result_id}',
    params={'include_chunks': True, 'page': 1, 'page_size': 50}
)

result = response.json()['data']
print(f"总块数: {result['total_chunks']}")
print(f"第一块: {result['chunks']['items'][0]['content'][:100]}...")
```

### 4. 对比分块结果

```python
response = requests.post('http://localhost:8000/api/v1/chunking/compare', json={
    "result_ids": ["result_1", "result_2", "result_3"]
})

comparison = response.json()['data']
print(f"推荐: {comparison['recommendations']}")
```

## 数据模型

### ChunkingTask
```json
{
  "task_id": "uuid",
  "document_id": "string",
  "strategy_type": "character|paragraph|heading|semantic",
  "parameters": {},
  "status": "pending|processing|completed|failed",
  "created_at": "ISO 8601",
  "completed_at": "ISO 8601"
}
```

### ChunkingResult
```json
{
  "result_id": "uuid",
  "document_name": "string",
  "strategy_type": "string",
  "total_chunks": 123,
  "processing_time": 1.23,
  "statistics": {
    "avg_chunk_size": 456,
    "max_chunk_size": 789,
    "min_chunk_size": 123
  },
  "created_at": "ISO 8601"
}
```

### Chunk
```json
{
  "id": "uuid",
  "sequence_number": 0,
  "content": "文本内容...",
  "metadata": {
    "char_count": 456,
    "word_count": 78,
    "start_position": 0,
    "end_position": 456
  }
}
```

## 性能指标

- **10k字符文档**: < 5秒完成分块
- **50k字符文档**: < 30秒完成分块
- **并发处理**: 最多3个任务同时执行
- **分页性能**: 500+记录流畅查询

## 降级机制

### 按标题分块降级
- **触发条件**: 文档中标题少于2个
- **降级策略**: 自动切换为按段落分块
- **元数据标记**: `fallback_strategy: "paragraph"`

### 按语义分块降级
- **触发条件**: 句子数量不足或语义分析失败
- **降级策略**: 简单的按句子分块
- **元数据标记**: `fallback_strategy: "sentence"`

## 文件存储

- **结果JSON**: `results/chunking/{document_id}_{strategy}_{timestamp}.json`
- **包含内容**: 完整分块数据、统计信息、元数据
- **导出格式**: JSON（完整）、CSV（简化）

## 错误处理

- **参数验证**: 自动验证并返回具体错误信息
- **文档不存在**: 返回404 Not Found
- **处理失败**: 记录错误信息到task表
- **部分结果**: 支持保存部分完成的分块（ResultStatus.PARTIAL）

## 开发指南

### 添加新的分块策略

1. 创建新的Chunker类继承BaseChunker
2. 实现`validate_params()`和`chunk()`方法
3. 在`CHUNKER_REGISTRY`中注册
4. 添加参数验证器到`chunking_validators.py`
5. 在数据库中seed新策略

### 扩展API功能

1. 在`backend/src/api/chunking.py`添加新端点
2. 在`ChunkingService`中实现业务逻辑
3. 在前端`chunkingService.js`添加API调用
4. 更新Pinia store的actions

## 测试

```bash
# 运行后端
cd backend
python -m src.main

# 测试API
curl http://localhost:8000/api/v1/chunking/strategies

# 运行前端
cd frontend
npm run dev
```

## 故障排查

### 问题: 分块任务一直pending
- 检查队列管理器是否启动
- 查看`/api/v1/chunking/queue`状态
- 检查数据库连接

### 问题: 语义分块总是降级
- 确认文档有足够的句子（至少2句）
- 检查文本是否有明显的句子分隔符
- 降低`similarity_threshold`参数

### 问题: 前端无法加载文档列表
- 确认文档已完成解析（status="completed"）
- 检查`/api/v1/chunking/documents/parsed`返回
- 查看浏览器控制台错误

## 更新日志

### v1.0.0 (2025-12-05)
- ✅ 实现4种分块策略
- ✅ 添加历史管理和对比功能
- ✅ 实现队列管理（最多3并发）
- ✅ 支持JSON/CSV导出
- ✅ 完整的前端UI（TDesign Vue Next）
