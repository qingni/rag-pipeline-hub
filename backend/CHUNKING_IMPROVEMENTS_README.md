# 文档分块优化 - 快速指南

## 🎯 优化目标

解决两个关键问题：
1. ❌ 同一文档+相同策略产生重复任务
2. ❌ 失败任务保存到数据库（脏数据）

## ✅ 已完成的优化

### 1. 幂等性检查（防止重复）

**效果**：相同请求返回相同结果，不创建重复任务

**实现**：
- 检查已有成功结果
- 比较文档ID + 策略 + 参数
- 匹配则直接返回已有结果

### 2. 事务回滚（防止脏数据）

**效果**：失败任务自动删除，数据库保持干净

**实现**：
- 成功才提交事务
- 失败自动回滚
- 不留下任何失败记录

## 📊 优化效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 总任务数 | 6 | 3 |
| 失败任务 | 3 条 | 0 条 |
| 重复处理 | 是 | 否 |
| 响应速度 | 慢 | 快 |

## 🚀 快速开始

### 1. 清理历史数据（一次性）

```bash
cd backend

# 预览清理效果
python -m src.utils.cleanup_tasks

# 执行清理
python -m src.utils.cleanup_tasks --execute
```

### 2. 验证优化效果

```bash
cd backend

# 运行自动化测试
./test_chunking_optimization.sh
```

### 3. 正常使用

优化已自动生效，无需任何额外配置！

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `CHUNKING_OPTIMIZATION.md` | 详细优化方案和实现 |
| `OPTIMIZATION_SUMMARY.md` | 优化总结 |
| `VERIFICATION_REPORT.md` | 验证报告 |
| `src/utils/cleanup_tasks.py` | 数据清理工具 |
| `test_chunking_optimization.sh` | 测试脚本 |

## 🔍 监控命令

### 查看任务状态
```bash
sqlite3 app.db "SELECT status, COUNT(*) FROM chunking_tasks GROUP BY status;"
```

### 检查重复任务
```bash
sqlite3 app.db "
SELECT source_document_id, chunking_strategy, COUNT(*) as count
FROM chunking_tasks
GROUP BY source_document_id, chunking_strategy
HAVING count > 1;
"
```

### 查看最近任务
```bash
sqlite3 app.db "
SELECT task_id, status, chunking_strategy, created_at
FROM chunking_tasks
ORDER BY created_at DESC
LIMIT 5;
"
```

## 💡 使用示例

### 正常分块请求
```bash
curl -X POST http://localhost:8000/api/v1/chunking/chunk \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "xxx",
    "strategy_type": "heading",
    "parameters": {"heading_formats": ["markdown"]}
  }'
```

### 重复请求（会返回已有结果）
```bash
# 再次发送相同请求
curl -X POST http://localhost:8000/api/v1/chunking/chunk \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "xxx",
    "strategy_type": "heading",
    "parameters": {"heading_formats": ["markdown"]}
  }'

# 返回相同的 task_id，message 提示使用已有结果
```

## ❓ 常见问题

### Q1: 如何强制重新分块？

A: 更改任何参数即可：
```json
{
  "parameters": {
    "heading_formats": ["markdown", "html"]  // 增加 html
  }
}
```

### Q2: 如何查看是否使用了缓存结果？

A: 查看响应的 `message` 字段：
- `"Chunking task created and completed successfully"` - 新任务
- `"Using existing chunking result..."` - 使用缓存

### Q3: 失败任务会怎样？

A: 自动回滚，不会保存到数据库，用户会收到错误提示

### Q4: 如何定期清理数据？

A: 可以设置 cron 任务：
```bash
# 每周日凌晨3点执行清理
0 3 * * 0 cd /path/to/backend && python -m src.utils.cleanup_tasks --execute
```

## 📞 支持

如有问题，请查看：
1. `CHUNKING_OPTIMIZATION.md` - 详细技术文档
2. `VERIFICATION_REPORT.md` - 验证报告
3. 运行测试脚本 - `./test_chunking_optimization.sh`

---

**优化版本**：v1.0  
**更新时间**：2025-12-05  
**状态**：✅ 已完成并验证
