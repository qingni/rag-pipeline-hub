# 分块版本管理功能说明

## 概述

本次优化实现了智能的文档分块版本管理系统，解决了以下场景：

1. **同一文档 + 不同分块策略** → 创建新的分块记录 ✅
2. **同一文档 + 同一策略 + 不同参数** → 智能判断是覆盖还是新建 ✅

## 核心功能

### 1. 版本管理字段

在 `ChunkingResult` 模型中新增了以下字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `version` | Integer | 版本号（从1开始递增）|
| `previous_version_id` | String(36) | 前一版本的 result_id |
| `is_active` | Boolean | 是否为活跃版本（默认 True）|
| `replacement_reason` | String(200) | 替换原因说明 |

### 2. 智能覆盖模式

API 端点 `POST /api/v1/chunking/chunk` 新增 `overwrite_mode` 参数：

#### 参数说明

```http
POST /api/v1/chunking/chunk?overwrite_mode=auto
Content-Type: application/json

{
  "document_id": "xxx",
  "strategy_type": "character",
  "parameters": {
    "chunk_size": 512,
    "overlap": 50
  }
}
```

**overwrite_mode 可选值:**

- **`auto`** (默认): 智能判断
  - 参数变化 < 20% → 覆盖旧版本
  - 参数变化 ≥ 20% → 创建新版本
  - 关键参数变化 → 创建新版本
  
- **`always`**: 强制覆盖
  - 总是将同策略的旧结果标记为非活跃
  - 创建新版本
  
- **`never`**: 总是创建新版本
  - 保留完整历史记录
  - 适合需要对比实验的场景

### 3. 参数变化判断逻辑

**关键参数**:
- `chunk_size`: 分块大小
- `overlap`: 重叠大小
- `separator`: 分隔符
- `min_chunk_size`: 最小分块
- `max_chunk_size`: 最大分块

**判断规则**:
1. 关键参数数值变化超过 20% → 重大变化
2. 非关键参数任何变化 → 重大变化
3. 参数结构变化（增删键）→ 重大变化
4. 所有变化 < 20% → 微小变化

**示例**:

```python
# 微小变化 → 覆盖（auto 模式）
old_params = {"chunk_size": 500, "overlap": 50}
new_params = {"chunk_size": 512, "overlap": 50}  # 变化 2.4%

# 重大变化 → 新建（auto 模式）
old_params = {"chunk_size": 500, "overlap": 50}
new_params = {"chunk_size": 2000, "overlap": 50}  # 变化 300%
```

## API 端点

### 1. 创建分块任务（已增强）

```http
POST /api/v1/chunking/chunk?overwrite_mode=auto
```

**响应示例**:
```json
{
  "code": 200,
  "message": "Chunking completed (replaced version 2)",
  "data": {
    "task_id": "xxx",
    "result_id": "yyy",
    "version": 3,
    "is_active": true,
    "previous_version_id": "zzz",
    "replacement_reason": "Auto-optimization: Minor parameter optimization: chunk_size: 500 -> 512",
    "total_chunks": 42
  }
}
```

### 2. 查询历史（已增强）

```http
GET /api/v1/chunking/history?active_only=true
```

**新增参数**:
- `active_only`: 仅显示活跃版本（默认 true）

**响应包含版本信息**:
```json
{
  "result_id": "xxx",
  "version": 3,
  "is_active": true,
  "previous_version_id": "yyy",
  "replacement_reason": "Auto-optimization: ...",
  ...
}
```

### 3. 查看版本历史（新增）

```http
GET /api/v1/chunking/versions/{document_id}/{strategy_type}
```

**响应示例**:
```json
{
  "code": 200,
  "data": {
    "document_id": "doc123",
    "strategy_type": "character",
    "total_versions": 3,
    "active_version": {
      "result_id": "v3",
      "version": 3,
      "is_active": true,
      "parameters": {"chunk_size": 512},
      ...
    },
    "versions": [
      {
        "result_id": "v3",
        "version": 3,
        "is_active": true,
        "parameters": {"chunk_size": 512},
        "replacement_reason": "Auto-optimization: ...",
        "created_at": "2025-12-05T10:30:00"
      },
      {
        "result_id": "v2",
        "version": 2,
        "is_active": false,
        "parameters": {"chunk_size": 500},
        "created_at": "2025-12-05T10:20:00"
      }
    ]
  }
}
```

### 4. 激活指定版本（新增）

```http
POST /api/v1/chunking/versions/{result_id}/activate
```

**功能**: 将指定版本设为活跃，其他版本自动变为非活跃

**用途**: 回滚到之前的分块结果

## 使用场景

### 场景1: 参数微调优化

```bash
# 第一次分块
curl -X POST "http://localhost:8000/api/v1/chunking/chunk?overwrite_mode=auto" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc123",
    "strategy_type": "character",
    "parameters": {"chunk_size": 500, "overlap": 50}
  }'
# 结果: version=1, is_active=true

# 微调参数（变化 2.4%）
curl -X POST "http://localhost:8000/api/v1/chunking/chunk?overwrite_mode=auto" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc123",
    "strategy_type": "character",
    "parameters": {"chunk_size": 512, "overlap": 50}
  }'
# 结果: version=2, is_active=true
# version=1 自动变为 is_active=false
```

### 场景2: 对比实验

```bash
# 第一次分块
curl -X POST "http://localhost:8000/api/v1/chunking/chunk?overwrite_mode=never" \
  -d '{"document_id": "doc123", "strategy_type": "character", 
       "parameters": {"chunk_size": 500}}'
# 结果: version=1

# 第二次实验（不覆盖）
curl -X POST "http://localhost:8000/api/v1/chunking/chunk?overwrite_mode=never" \
  -d '{"document_id": "doc123", "strategy_type": "character", 
       "parameters": {"chunk_size": 1000}}'
# 结果: version=2
# 两个版本都是 is_active=true，可以对比
```

### 场景3: 强制覆盖

```bash
# 无论参数如何变化，都覆盖
curl -X POST "http://localhost:8000/api/v1/chunking/chunk?overwrite_mode=always" \
  -d '{"document_id": "doc123", "strategy_type": "character", 
       "parameters": {"chunk_size": 2000}}'
# 结果: 旧版本 is_active=false，新版本 is_active=true
```

### 场景4: 版本回滚

```bash
# 查看历史版本
curl "http://localhost:8000/api/v1/chunking/versions/doc123/character"

# 激活旧版本
curl -X POST "http://localhost:8000/api/v1/chunking/versions/{old_result_id}/activate"
```

## 数据库迁移

运行以下命令添加版本管理字段：

```bash
cd backend
python migrations/add_version_management.py
```

**迁移内容**:
- 添加 4 个新字段
- 创建复合索引 `idx_doc_strategy_active`
- 更新现有记录（version=1, is_active=true）

## 兼容性

### 向后兼容

- 现有代码无需修改即可运行
- 默认 `overwrite_mode=auto` 保持原有行为
- 旧记录自动初始化为 version=1, is_active=true

### API 变更

| 端点 | 变更类型 | 说明 |
|------|---------|------|
| `POST /chunk` | 新增参数 | 可选参数 `overwrite_mode` |
| `GET /history` | 新增参数 | 可选参数 `active_only` |
| `GET /versions/{doc}/{strategy}` | 新增端点 | 查看版本历史 |
| `POST /versions/{id}/activate` | 新增端点 | 激活指定版本 |

## 前端集成建议

### 1. 分块参数配置界面

```vue
<template>
  <div>
    <el-form>
      <el-form-item label="覆盖模式">
        <el-select v-model="overwriteMode">
          <el-option label="智能判断（推荐）" value="auto" />
          <el-option label="总是覆盖" value="always" />
          <el-option label="保留全部历史" value="never" />
        </el-select>
      </el-form-item>
    </el-form>
  </div>
</template>
```

### 2. 版本历史展示

```vue
<template>
  <el-timeline>
    <el-timeline-item 
      v-for="ver in versions" 
      :key="ver.result_id"
      :type="ver.is_active ? 'primary' : 'info'"
    >
      <div>
        <el-tag v-if="ver.is_active">当前版本</el-tag>
        版本 {{ ver.version }} - {{ ver.created_at }}
      </div>
      <div>{{ ver.replacement_reason }}</div>
      <el-button 
        v-if="!ver.is_active" 
        @click="activateVersion(ver.result_id)"
      >
        恢复此版本
      </el-button>
    </el-timeline-item>
  </el-timeline>
</template>
```

## 性能优化

### 索引优化

新增索引 `idx_doc_strategy_active` 优化以下查询：
```sql
SELECT * FROM chunking_results 
WHERE document_id = ? 
  AND chunking_strategy = ? 
  AND is_active = true;
```

### 数据清理

可以定期清理旧版本数据：
```python
# 保留最近 N 个版本，删除更旧的非活跃版本
def cleanup_old_versions(document_id, strategy, keep_count=5):
    results = query.filter(
        is_active=False
    ).order_by(version.desc()).offset(keep_count).all()
    
    for result in results:
        delete(result)
```

## 最佳实践

### 1. 推荐使用 auto 模式

大多数场景使用 `overwrite_mode=auto` 即可：
- 微调优化自动覆盖
- 重大变化自动保留历史

### 2. 实验对比使用 never 模式

需要 A/B 测试时：
- 使用 `overwrite_mode=never`
- 利用对比 API 分析效果
- 确定最佳参数后切换到 auto 模式

### 3. 定期清理历史版本

生产环境建议：
- 保留最近 5-10 个版本
- 定期清理旧的非活跃版本
- 备份重要版本的 JSON 文件

### 4. 版本命名规范

可以利用 `replacement_reason` 记录：
- "Initial version" - 首次创建
- "Parameter tuning" - 参数微调
- "Major update: chunk_size 500->2000" - 重大更新
- "Bug fix: separator corrected" - 修复问题

## 故障排查

### 问题1: 总是创建新版本

**原因**: 参数变化超过阈值

**解决**:
```bash
# 查看日志中的判断原因
tail -f logs/app.log | grep "parameter change"

# 使用 always 模式强制覆盖
curl "...?overwrite_mode=always"
```

### 问题2: 版本号不连续

**原因**: 多个策略独立计算版本号

**说明**: 这是正常行为，每个 (document_id, strategy_type) 组合独立维护版本号

### 问题3: 迁移后字段为 NULL

**解决**:
```bash
# 重新运行迁移脚本
python migrations/add_version_management.py
```

## 总结

本次优化实现了完整的版本管理系统：

✅ **智能判断**: 自动识别微小变化和重大变化  
✅ **灵活控制**: 3 种覆盖模式满足不同场景  
✅ **版本追溯**: 完整的历史记录和回滚能力  
✅ **性能优化**: 索引优化查询效率  
✅ **向后兼容**: 无需修改现有代码  

符合 RAG 应用的最佳实践，满足实验对比、参数优化、历史追溯等多种需求。
