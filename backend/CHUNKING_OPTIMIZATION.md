# 文档分块优化方案

## 问题描述

1. **重复任务问题**：同一文档使用相同分块策略会产生多条任务记录
2. **失败任务入库**：分块失败的任务会保存在数据库中，产生脏数据

## 优化方案

### 1. 幂等性检查（防止重复任务）

#### 实现逻辑
在 `src/api/chunking.py` 的 `create_chunking_task` 函数中：

1. **检查已有成功结果**
   - 在创建新任务前，查询是否存在相同文档+策略+参数的成功结果
   - 使用 JSON 字符串比较确保参数完全一致

2. **返回已有结果**
   - 如果找到匹配的成功结果，直接返回该结果
   - 避免重复处理，节省计算资源

3. **支持重新分块**
   - 如果参数不同，仍会创建新任务
   - 用户可以使用不同参数重新分块

#### 代码示例
```python
# 检查是否已存在成功的结果
existing_result = db.query(ChunkingResult).join(
    ChunkingTask,
    ChunkingResult.task_id == ChunkingTask.task_id
).filter(
    ChunkingTask.source_document_id == request.document_id,
    ChunkingTask.chunking_strategy == strategy_enum,
    ChunkingResult.status == ResultStatus.COMPLETED
).order_by(ChunkingResult.created_at.desc()).first()

# 比较参数是否一致
if existing_result:
    existing_params_json = json.dumps(existing_result.chunking_params, sort_keys=True)
    if existing_params_json == params_json:
        # 返回已有结果
        return success_response(data={...}, message="Using existing chunking result")
```

### 2. 事务回滚机制（防止失败任务入库）

#### 实现逻辑

1. **延迟提交**
   - 创建任务时使用 `db.flush()` 而不是 `db.commit()`
   - 先获取 task_id，但不提交到数据库

2. **条件提交**
   - 只有在分块处理成功后才 `db.commit()`
   - 成功标准：`task.status == TaskStatus.COMPLETED`

3. **失败回滚**
   - 如果处理失败，调用 `db.rollback()`
   - 任务记录和相关数据不会保存到数据库

#### 代码示例
```python
# 创建任务但不提交
db.add(task)
db.flush()  # 获取 task_id

try:
    result = chunking_service.process_chunking_task(task.task_id, db)
    db.refresh(task)
    
    if task.status == TaskStatus.COMPLETED:
        db.commit()  # 只有成功才提交
        return success_response(...)
    else:
        db.rollback()  # 失败则回滚
        raise ValidationError(...)
except Exception as e:
    db.rollback()  # 异常也回滚
    raise ValidationError(...)
```

### 3. 数据清理工具

创建了 `src/utils/cleanup_tasks.py` 工具脚本，用于清理历史数据：

#### 功能

1. **清理重复任务** (`cleanup_duplicate_tasks`)
   - 对于同一文档+策略+参数的多个成功任务
   - 保留最新的一个，删除其他旧任务

2. **清理失败任务** (`cleanup_failed_tasks`)
   - 删除所有状态为 FAILED 的任务记录
   - 这些是优化前产生的历史脏数据

3. **统一清理** (`cleanup_all`)
   - 执行所有清理操作
   - 提供详细的统计信息

#### 使用方法

**1. 预览模式（不删除数据）**
```bash
cd backend
python -m src.utils.cleanup_tasks
```

**2. 执行模式（实际删除数据）**
```bash
cd backend
python -m src.utils.cleanup_tasks --execute
```

**输出示例**
```
[DRY RUN] Starting cleanup operations...

1. Cleaning up duplicate tasks...
   - Found 2 duplicate document+strategy combinations
   - Tasks to delete: 3

2. Cleaning up failed tasks...
   - Found 5 failed tasks

[DRY RUN] Cleanup completed!
```

### 4. 数据库优化建议（可选）

#### 方案A：添加唯一索引（强约束）
如果完全禁止重复任务，可以添加：

```python
# 在 ChunkingTask 模型中添加
__table_args__ = (
    Index('idx_unique_task', 'source_document_id', 'chunking_strategy', 'chunking_params', unique=True),
)
```

**优点**：数据库层面强制唯一性
**缺点**：
- 不支持重新分块（即使参数改变）
- JSON 字段难以建立唯一索引
- 可能影响灵活性

#### 方案B：添加任务哈希字段（推荐）
为每个任务生成唯一哈希：

```python
import hashlib
import json

def generate_task_hash(document_id: str, strategy: str, params: dict) -> str:
    """生成任务唯一标识哈希"""
    content = f"{document_id}:{strategy}:{json.dumps(params, sort_keys=True)}"
    return hashlib.sha256(content.encode()).hexdigest()

# 在任务创建时
task_hash = generate_task_hash(document_id, strategy_type, params)
# 检查是否存在相同哈希的成功任务
```

**优点**：
- 快速查询和比较
- 支持建立唯一索引
- 灵活性好

## 优化效果

### 问题1解决：重复任务
- ✅ 相同文档+策略+参数会直接返回已有结果
- ✅ 不会创建新的重复任务记录
- ✅ 节省计算资源和存储空间
- ✅ 保留历史记录用于审计

### 问题2解决：失败任务
- ✅ 失败的任务不会保存到数据库
- ✅ 数据库保持干净，无脏数据
- ✅ 清理工具可处理历史脏数据
- ✅ 用户只看到成功的任务记录

## 测试建议

### 1. 测试幂等性
```bash
# 对同一文档执行相同分块策略两次
curl -X POST http://localhost:8000/api/v1/chunking/chunk \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "xxx",
    "strategy_type": "heading",
    "parameters": {"heading_formats": ["markdown"]}
  }'

# 第二次应该返回已有结果
curl -X POST http://localhost:8000/api/v1/chunking/chunk \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "xxx",
    "strategy_type": "heading",
    "parameters": {"heading_formats": ["markdown"]}
  }'
```

### 2. 测试失败回滚
```bash
# 使用错误的参数触发失败
curl -X POST http://localhost:8000/api/v1/chunking/chunk \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "xxx",
    "strategy_type": "character",
    "parameters": {"invalid_param": "xxx"}
  }'

# 检查数据库中是否有失败任务
sqlite3 app.db "SELECT COUNT(*) FROM chunking_tasks WHERE status='FAILED';"
# 应该返回 0
```

### 3. 测试清理工具
```bash
# 预览清理效果
python -m src.utils.cleanup_tasks

# 执行清理
python -m src.utils.cleanup_tasks --execute
```

## 监控建议

定期监控任务状态分布：
```sql
-- 查看任务状态统计
SELECT status, COUNT(*) as count 
FROM chunking_tasks 
GROUP BY status;

-- 查看重复任务数量
SELECT source_document_id, chunking_strategy, COUNT(*) as count
FROM chunking_tasks
GROUP BY source_document_id, chunking_strategy
HAVING count > 1;
```

## 未来优化方向

1. **任务队列**：引入消息队列（如 Celery）处理异步任务
2. **结果缓存**：使用 Redis 缓存常用分块结果
3. **增量更新**：文档更新时只重新分块变化部分
4. **智能重试**：对临时失败自动重试，永久失败才记录
5. **定期清理**：设置定时任务自动清理过期数据
