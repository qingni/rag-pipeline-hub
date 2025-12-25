# Quickstart: 搜索查询功能

**Feature**: 005-search-query  
**Date**: 2025-12-25

## 前置条件

1. **向量索引已创建**: 至少有一个包含向量数据的索引（通过 004-vector-index 模块创建）
2. **Embedding 服务可用**: 003-vector-embedding 模块的 Embedding API 正常运行
3. **后端服务运行中**: FastAPI 服务在 `http://localhost:8000` 运行
4. **前端服务运行中**: Vue 开发服务器在 `http://localhost:5173` 运行

## 场景 1: 基础语义搜索

### 步骤

1. 打开浏览器访问 `http://localhost:5173/search`
2. 在搜索框中输入查询文本，如 "什么是向量数据库？"
3. 点击搜索按钮或按回车键
4. 查看搜索结果列表

### 预期结果

- 搜索在 3 秒内返回结果
- 结果以卡片形式展示，包含文本摘要、相似度分数、来源文档
- 结果按相似度降序排列

### API 调用示例

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "什么是向量数据库？",
    "top_k": 10,
    "threshold": 0.5
  }'
```

### 预期响应

```json
{
  "success": true,
  "data": {
    "query_id": "550e8400-e29b-41d4-a716-446655440000",
    "query_text": "什么是向量数据库？",
    "results": [
      {
        "chunk_id": "chunk_001",
        "text_summary": "向量数据库是一种专门用于存储和检索高维向量数据的数据库系统...",
        "similarity_score": 0.95,
        "similarity_percent": "95.0%",
        "source_document": "database_intro.pdf",
        "rank": 1
      }
    ],
    "total_count": 5,
    "execution_time_ms": 120
  }
}
```

---

## 场景 2: 配置搜索参数

### 步骤

1. 点击搜索框旁的配置图标打开配置面板
2. 选择目标索引（如 "技术文档索引"）
3. 设置 TopK = 5
4. 设置相似度阈值 = 0.7
5. 选择相似度方法 = 余弦相似度
6. 执行搜索

### 预期结果

- 最多返回 5 条结果
- 所有结果的相似度分数 ≥ 0.7
- 结果仅来自选中的索引

### API 调用示例

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "如何优化数据库性能？",
    "index_ids": ["idx_tech_docs"],
    "top_k": 5,
    "threshold": 0.7,
    "metric_type": "cosine"
  }'
```

---

## 场景 3: 多索引联合搜索

### 步骤

1. 在配置面板中选择多个索引（按住 Ctrl/Cmd 多选）
2. 输入查询文本
3. 执行搜索

### 预期结果

- 结果包含来自所有选中索引的文档
- 每条结果标注来源索引名称
- 结果按统一的相似度排序

### API 调用示例

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "用户认证最佳实践",
    "index_ids": ["idx_tech_docs", "idx_security_docs"],
    "top_k": 10
  }'
```

---

## 场景 4: 查看和使用搜索历史

### 步骤

1. 点击搜索框右侧的历史图标
2. 查看历史搜索记录列表
3. 点击某条历史记录快速重新执行搜索
4. 或点击删除图标移除单条记录

### 预期结果

- 历史记录按时间倒序显示
- 点击记录后自动填充查询框并执行搜索
- 删除操作立即生效

### API 调用示例

```bash
# 获取搜索历史
curl http://localhost:8000/api/v1/search/history?limit=20

# 删除单条历史
curl -X DELETE http://localhost:8000/api/v1/search/history/550e8400-e29b-41d4-a716-446655440000

# 清空所有历史
curl -X DELETE http://localhost:8000/api/v1/search/history
```

---

## 场景 5: 查看结果详情

### 步骤

1. 执行搜索获得结果列表
2. 点击某个结果卡片的 "查看详情" 按钮
3. 在弹窗中查看完整内容

### 预期结果

- 弹窗显示完整的文档片段内容
- 显示元数据信息（来源文档、片段位置等）
- 可以关闭弹窗返回结果列表

---

## 错误处理场景

### 场景 A: 空查询

**输入**: 空字符串或仅包含空格  
**预期**: 显示错误提示 "请输入有效的查询内容"

### 场景 B: 无匹配结果

**输入**: 与索引内容完全不相关的查询  
**预期**: 显示提示 "未找到相关内容，请尝试其他关键词"

### 场景 C: 索引不存在

**输入**: 指定不存在的索引ID  
**预期**: 显示错误提示 "所选索引不存在或已被删除"

### 场景 D: 服务超时

**条件**: Embedding 服务响应超过 30 秒  
**预期**: 显示错误提示 "搜索请求超时，请稍后重试"

---

## 性能基准

| 场景 | 预期响应时间 |
|------|-------------|
| 单索引搜索 (10K 向量) | < 1 秒 |
| 多索引搜索 (2 索引) | < 2 秒 |
| 端到端搜索 (含 Embedding) | < 3 秒 |
| 加载搜索历史 | < 500 毫秒 |

---

## 开发调试

### 启动服务

```bash
# 后端
cd backend && source .venv/bin/activate && uvicorn src.main:app --reload

# 前端
cd frontend && npm run dev
```

### 查看日志

```bash
# 后端日志
tail -f backend/logs/app.log

# 搜索相关日志
grep "search" backend/logs/app.log
```

### 测试 API

```bash
# 健康检查
curl http://localhost:8000/health

# 获取可用索引
curl http://localhost:8000/api/v1/search/indexes
```
