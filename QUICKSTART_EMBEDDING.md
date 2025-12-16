# 向量嵌入快速开始指南

## 5分钟快速体验

### 前提条件

1. 后端服务正在运行
2. 已设置环境变量 `EMBEDDING_API_KEY`
3. 至少有一个已完成分块的文档

### 快速开始

```bash
# 1. 进入后端目录
cd backend

# 2. 运行测试脚本
python test_embedding_from_chunks.py
```

按照提示选择测试:
- **选项1**: 基于分块结果ID向量化
- **选项2**: 基于文档ID向量化(推荐)
- **选项3**: 单文本向量化(传统方式)

## 完整工作流示例

### 方法1: Python脚本

```bash
cd backend
python example_embedding_workflow.py
```

该脚本会引导你完成:
1. 文档上传
2. 文档加载
3. 文档分块
4. 向量嵌入

### 方法2: cURL命令

#### 步骤1: 上传文档
```bash
curl -X POST "http://localhost:8000/api/documents/upload" \
  -F "file=@/path/to/document.pdf"
```

**返回文档ID**: `doc-12345`

#### 步骤2: 加载文档
```bash
curl -X POST "http://localhost:8000/api/documents/load" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "doc-12345"}'
```

#### 步骤3: 分块文档
```bash
curl -X POST "http://localhost:8000/api/chunking/chunk" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc-12345",
    "strategy_type": "paragraph",
    "parameters": {
      "chunk_size": 500,
      "chunk_overlap": 50
    }
  }'
```

**返回分块结果ID**: `result-abc123`

#### 步骤4: 向量嵌入(推荐方式)
```bash
curl -X POST "http://localhost:8000/api/embedding/from-document" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc-12345",
    "model": "qwen3-embedding-8b",
    "strategy_type": "paragraph"
  }'
```

或者使用分块结果ID:
```bash
curl -X POST "http://localhost:8000/api/embedding/from-chunking-result" \
  -H "Content-Type: application/json" \
  -d '{
    "result_id": "result-abc123",
    "model": "qwen3-embedding-8b"
  }'
```

### 方法3: Postman/API客户端

1. 导入API collection (如果有提供)
2. 按顺序执行请求
3. 使用返回的ID进行下一步

## API端点速查

| 功能 | 端点 | 方法 | 说明 |
|------|------|------|------|
| 查看模型列表 | `/api/embedding/models` | GET | 列出所有支持的模型 |
| 从分块结果向量化 | `/api/embedding/from-chunking-result` | POST | 使用分块结果ID |
| 从文档向量化 | `/api/embedding/from-document` | POST | 使用文档ID(推荐) |
| 单文本向量化 | `/api/embedding/single` | POST | 用于查询 |
| 批量文本向量化 | `/api/embedding/batch` | POST | 任意文本 |
| 健康检查 | `/api/embedding/health` | GET | 检查服务状态 |

## 常见问题

### Q1: 如何获取分块结果ID?

通过分块API的响应获取:
```bash
POST /api/chunking/chunk
# 响应中包含 "result_id"
```

### Q2: 如何知道文档是否已分块?

查询文档的分块结果:
```bash
GET /api/chunking/result/latest/{document_id}
```

### Q3: 向量嵌入结果保存在哪里?

JSON文件保存在: `backend/results/embedding/{YYYY-MM-DD}/`

文件名格式: `embedding_{request_id}_{timestamp}.json`

### Q4: 如何选择合适的模型?

| 模型 | 维度 | 适用场景 |
|------|------|----------|
| qwen3-embedding-8b | 1536 | **推荐**,通用场景,中英文支持好 |
| bge-m3 | 1024 | 多语言,轻量级 |
| hunyuan-embedding | 1024 | 腾讯生态,中文优化 |
| jina-embeddings-v4 | 768 | 轻量级,快速 |

### Q5: 如何处理大文档?

系统会自动:
1. 将文档分块(最多1000个分块)
2. 批量向量化
3. 保持分块顺序

如果分块超过1000个,考虑:
- 增大分块大小
- 使用更简洁的分块策略

### Q6: 向量化失败怎么办?

1. 检查错误信息
2. 查看日志文件
3. 确认:
   - API密钥是否正确
   - 分块结果是否存在
   - 网络是否正常

系统会自动重试临时错误(网络、速率限制)。

## 下一步

完成向量嵌入后,你可以:

1. **查看结果文件**
   ```bash
   cat backend/results/embedding/$(date +%Y-%m-%d)/embedding_*.json | jq
   ```

2. **将向量存储到向量数据库**
   - Milvus
   - Qdrant
   - Weaviate

3. **实现语义搜索**
   - 查询文本向量化
   - 向量相似度搜索
   - 返回相关文档

4. **集成到前端**
   - 添加向量化按钮
   - 显示进度和结果
   - 支持模型选择

## 获取帮助

- 📖 详细文档: `backend/EMBEDDING_OPTIMIZATION.md`
- 📝 完整总结: `EMBEDDING_OPTIMIZATION_SUMMARY.md`
- 🧪 测试脚本: `backend/test_embedding_from_chunks.py`
- 💡 示例代码: `backend/example_embedding_workflow.py`
- 📋 规格文档: `specs/003-vector-embedding/spec.md`

## 故障排查

### 服务无法启动
```bash
# 检查依赖
pip install -r requirements.txt

# 检查环境变量
echo $EMBEDDING_API_KEY

# 查看日志
tail -f backend/logs/app.log
```

### API返回401错误
```bash
# 设置API密钥
export EMBEDDING_API_KEY="your-api-key-here"
```

### 分块结果不存在
```bash
# 先执行分块
curl -X POST "http://localhost:8000/api/chunking/chunk" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "doc-id", "strategy_type": "paragraph"}'
```

### 向量维度不匹配
```bash
# 检查模型配置
curl "http://localhost:8000/api/embedding/models"

# 确保使用正确的模型名称
```

---

🎉 **恭喜!** 你已经掌握了向量嵌入功能的基本使用!
