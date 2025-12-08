# 快速开始：分块版本管理

## 5 分钟上手指南

### 第一步：运行数据库迁移

```bash
cd backend
python migrations/add_version_management.py
```

**预期输出**:
```
============================================================
Starting database migration: Add version management
============================================================
✓ Found chunking_results table
✓ Added 'version' column
✓ Added 'previous_version_id' column
✓ Added 'is_active' column
✓ Added 'replacement_reason' column
✓ Created index idx_doc_strategy_active
✓ Updated N existing records
============================================================
✅ Migration completed successfully!
============================================================
```

### 第二步：测试基础功能

#### 场景A：参数微调（自动覆盖）

```bash
# 首次分块
curl -X POST "http://localhost:8000/api/v1/chunking/chunk?overwrite_mode=auto" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "your_doc_id",
    "strategy_type": "character",
    "parameters": {
      "chunk_size": 500,
      "overlap": 50
    }
  }'

# 微调参数（变化 < 20%，会自动覆盖）
curl -X POST "http://localhost:8000/api/v1/chunking/chunk?overwrite_mode=auto" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "your_doc_id",
    "strategy_type": "character",
    "parameters": {
      "chunk_size": 512,
      "overlap": 50
    }
  }'

# 响应包含:
# {
#   "version": 2,
#   "previous_version_id": "xxx",
#   "replacement_reason": "Auto-optimization: Minor parameter optimization..."
# }
```

#### 场景B：对比实验（保留全部版本）

```bash
# 实验1: 小块
curl -X POST "http://localhost:8000/api/v1/chunking/chunk?overwrite_mode=never" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "your_doc_id",
    "strategy_type": "character",
    "parameters": {"chunk_size": 500}
  }'

# 实验2: 大块
curl -X POST "http://localhost:8000/api/v1/chunking/chunk?overwrite_mode=never" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "your_doc_id",
    "strategy_type": "character",
    "parameters": {"chunk_size": 2000}
  }'

# 两个版本都保留，可以对比效果
```

### 第三步：查看版本历史

```bash
# 查看某文档的所有版本
curl "http://localhost:8000/api/v1/chunking/versions/{document_id}/character" | jq

# 响应示例:
# {
#   "total_versions": 3,
#   "active_version": { "version": 3, ... },
#   "versions": [
#     { "version": 3, "is_active": true, ... },
#     { "version": 2, "is_active": false, ... },
#     { "version": 1, "is_active": false, ... }
#   ]
# }
```

### 第四步：版本回滚

```bash
# 激活旧版本
curl -X POST "http://localhost:8000/api/v1/chunking/versions/{old_result_id}/activate"

# 响应:
# {
#   "message": "Version 2 activated successfully",
#   "data": {
#     "result_id": "xxx",
#     "version": 2,
#     "is_active": true
#   }
# }
```

## 常见问题

### Q1: 什么时候使用哪种模式？

| 场景 | 推荐模式 | 原因 |
|------|---------|------|
| 日常使用 | `auto` | 智能判断，自动优化 |
| 参数调优 | `auto` | 微调自动覆盖，大改保留历史 |
| A/B 测试 | `never` | 保留所有版本对比 |
| 修复错误 | `always` | 直接替换错误版本 |

### Q2: 参数变化多少算"微小"？

**数值类参数**（chunk_size, overlap等）:
- 变化 < 20% → 微小变化（覆盖）
- 变化 ≥ 20% → 重大变化（新建）

**非数值参数**（separator等）:
- 任何变化 → 重大变化（新建）

### Q3: 版本号如何计算？

每个 `(document_id, strategy_type)` 组合独立维护版本号：

```
document_A + character策略 → 版本 1, 2, 3...
document_A + paragraph策略 → 版本 1, 2, 3...  (独立计数)
document_B + character策略 → 版本 1, 2, 3...  (独立计数)
```

### Q4: 旧版本占用存储怎么办？

可以定期清理：

```python
from backend.src.api.chunking_history import delete_result

# 删除非活跃的旧版本
for old_version in inactive_versions[5:]:  # 保留最近5个
    delete_result(old_version.result_id, db)
```

## 运行完整测试

```bash
cd backend

# 1. 确保后端服务运行
# ./start_backend.sh

# 2. 运行测试脚本
./test_version_management.sh

# 3. 查看测试结果
# 脚本会创建多个版本，测试各种覆盖模式
```

## 下一步

1. **前端集成**: 参考 `CHUNKING_VERSION_MANAGEMENT.md` 的前端集成建议
2. **监控告警**: 监控版本数量，避免过度堆积
3. **数据清理**: 设置定时任务清理旧版本
4. **业务规则**: 根据实际需求调整参数变化阈值

## 技术支持

- 详细文档: `CHUNKING_VERSION_MANAGEMENT.md`
- 测试脚本: `test_version_management.sh`
- 迁移脚本: `migrations/add_version_management.py`
- 核心代码: `src/utils/chunking_version_helper.py`
