# 测试说明：文档选择后自动加载向量结果

**功能**: 当用户在文档选择器中选择一个已经向量化的文档时，系统会立即加载并显示该文档的最新向量化结果。

**实现时间**: 2025-12-17  
**修复时间**: 2025-12-17（修复显示问题）

> **重要更新**: 2025-12-17修复了向量化结果显示问题。详见 [FIX_DISPLAY_ISSUE.md](./FIX_DISPLAY_ISSUE.md)

---

## 功能概述

### 改进前
- 用户需要手动点击"开始向量化"才能看到结果
- 无法直接查看历史向量化结果
- 每次都需要重新向量化才能查看数据

### 改进后
- 选择已向量化文档后，**立即自动显示**最新向量结果
- 模型选择器**自动切换**到历史结果使用的模型
- 按钮文本从"开始向量化"变为"重新向量化"
- 显示完整的向量数据、元数据和统计信息
- 加载过程有友好的 loading 状态提示

---

## 测试步骤

### 前置条件
1. 后端服务已启动（`./start_backend.sh`）
2. 前端服务已启动（`./start_frontend.sh`）
3. 数据库中已有至少一个已向量化的文档

### 创建测试数据（如果没有）

```bash
# 1. 上传文档
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@test.pdf" \
  -H "X-API-Key: your-api-key"

# 记录返回的 document_id

# 2. 分块文档
curl -X POST http://localhost:8000/api/chunking/chunk \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "document_id": "your-document-id",
    "strategy": "fixed_size",
    "chunk_size": 500,
    "overlap": 50
  }'

# 记录返回的 chunking_result_id

# 3. 向量化文档
curl -X POST http://localhost:8000/api/embedding/from-document \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "document_id": "your-document-id",
    "model": "qwen3-embedding-8b"
  }'
```

### 测试场景 1: 选择已向量化文档

1. 打开浏览器访问 `http://localhost:5173/documents/embed`
2. 在文档选择器下拉框中选择一个已分块的文档
3. **预期结果**:
   - 右侧面板显示 loading 状态（"正在加载向量化结果..."）
   - 0.5秒内显示向量化结果
   - 显示文档名称、向量数量、向量维度、处理时间
   - 显示状态卡片（成功/部分成功/失败）
   - 显示处理元数据（模型、批次大小、成功数量等）
   - 显示向量列表（带热力图、统计信息）
   - 模型选择器自动切换到历史结果使用的模型
   - 按钮文本显示"重新向量化"

### 测试场景 2: 切换到未向量化文档

1. 在场景1的基础上，选择另一个已分块但未向量化的文档
2. **预期结果**:
   - 右侧面板显示空状态（"暂无向量化结果"）
   - 按钮文本显示"开始向量化"
   - 不显示任何错误消息（404是正常情况）

### 测试场景 3: 重新向量化

1. 在场景1显示历史结果的基础上
2. 修改模型选择器（例如从 qwen3 改为 bge-m3）
3. 点击"重新向量化"按钮
4. **预期结果**:
   - 按钮显示 loading 状态（"向量化中..."）
   - 向量化完成后显示新的结果
   - 模型保持为新选择的模型
   - 显示成功消息："向量化完成"

### 测试场景 4: 模型自动切换

1. 文档A使用 qwen3 模型向量化
2. 文档B使用 bge-m3 模型向量化
3. 依次选择文档A和文档B
4. **预期结果**:
   - 选择文档A时，模型选择器自动切换到 qwen3
   - 选择文档B时，模型选择器自动切换到 bge-m3
   - 右侧面板分别显示对应的向量结果

### 测试场景 5: 错误处理

1. 停止后端服务
2. 在前端选择一个文档
3. **预期结果**:
   - 显示网络错误消息（不会崩溃）
   - 右侧面板保持上一个状态或显示空状态

---

## API 变更说明

### 后端变更

#### 新增模型
```python
class EmbeddingResultWithVectors(EmbeddingResultDetail):
    """扩展的结果模型，包含向量数据"""
    vectors: List[Vector]
    failures: List[EmbeddingFailure]
    metadata: Optional[dict]
```

#### API 端点变更
```
GET /api/embedding/results/by-document/{document_id}
```

**新增查询参数**:
- `include_vectors` (bool, default: true) - 是否包含向量数据

**响应示例**:
```json
{
  "result_id": "123e4567-e89b-12d3-a456-426614174000",
  "document_id": "doc-001",
  "model": "qwen3-embedding-8b",
  "status": "SUCCESS",
  "successful_count": 50,
  "failed_count": 0,
  "vector_dimension": 4096,
  "json_file_path": "2025-12-17/embedding_123_20251217_143000.json",
  "processing_time_ms": 2500.5,
  "created_at": "2025-12-17T14:30:00Z",
  "vectors": [
    {
      "index": 0,
      "vector": [0.123, -0.456, ...],
      "dimension": 4096,
      "text_length": 450,
      "processing_time_ms": 50.2
    }
  ],
  "failures": [],
  "metadata": {
    "model": "qwen3-embedding-8b",
    "model_dimension": 4096,
    "successful_count": 50,
    "failed_count": 0,
    "processing_time_ms": 2500.5,
    "vectors_per_second": 20.0
  }
}
```

### 前端变更

#### 新增 API 方法
```javascript
// frontend/src/services/embeddingService.js

async getLatestByDocument(documentId, model = null)
async getResultById(resultId)
async listResults(params = {})
```

#### 新增 Store Action
```javascript
// frontend/src/stores/embedding.js

async fetchLatestEmbeddingResult(documentId, modelFilter = null)
```

#### 页面变更
```vue
<!-- frontend/src/views/DocumentEmbedding.vue -->

<!-- 新增 watch 监听文档选择 -->
watch(
  () => store.selectedDocumentId,
  async (newDocumentId) => {
    if (newDocumentId) {
      await loadLatestResult(newDocumentId)
    }
  }
)

<!-- 新增 loading 状态 -->
<div v-if="loadingResult" class="loading-overlay">
  <t-loading size="large" text="正在加载向量化结果..." />
</div>

<!-- 更新按钮文本 -->
{{ buttonText }} <!-- "开始向量化" 或 "重新向量化" -->
```

---

## 性能指标

- **加载时间目标**: < 500ms
- **JSON 文件大小**: 约 1-10MB（取决于向量数量和维度）
- **并发支持**: 多用户同时查询不同文档

---

## 已知限制

1. **JSON 文件丢失**: 如果数据库记录存在但 JSON 文件丢失，会返回元数据但 vectors 为空数组
2. **大文件加载**: 包含10000+向量的文档加载可能需要1-2秒
3. **模型过滤**: 如果指定了 model 参数但找不到匹配的结果，返回404

---

## 故障排查

### 问题: 选择文档后右侧面板一直显示 loading

**可能原因**:
1. 后端服务未启动
2. 网络连接问题
3. API 端点地址配置错误

**解决方法**:
```bash
# 检查后端服务
curl http://localhost:8000/api/embedding/health

# 检查浏览器控制台的网络请求
# 查看是否有 CORS 错误或 404 错误
```

### 问题: 显示元数据但没有向量数据

**可能原因**:
1. JSON 文件路径错误
2. JSON 文件已被删除
3. 文件权限问题

**解决方法**:
```bash
# 检查 JSON 文件是否存在
ls -la results/embedding/2025-12-17/

# 检查数据库记录
sqlite3 app.db "SELECT result_id, json_file_path FROM embedding_results WHERE document_id='your-doc-id';"

# 手动检查 JSON 文件内容
cat results/embedding/2025-12-17/embedding_*.json | jq .
```

### 问题: 模型选择器没有自动切换

**可能原因**:
1. 历史结果的 model 字段为空
2. 前端 availableModels 列表不包含该模型

**解决方法**:
- 检查后端返回的响应数据
- 确认模型列表已正确加载
- 查看浏览器控制台是否有错误

---

## 相关文件

### 后端
- `backend/src/models/embedding_models.py` - 数据模型定义
- `backend/src/api/embedding_query_routes.py` - 查询API端点
- `backend/src/storage/embedding_db.py` - 数据库查询
- `backend/src/storage/embedding_storage.py` - JSON文件存储

### 前端
- `frontend/src/services/embeddingService.js` - API客户端
- `frontend/src/stores/embedding.js` - Pinia状态管理
- `frontend/src/views/DocumentEmbedding.vue` - 主页面
- `frontend/src/components/embedding/EmbeddingResults.vue` - 结果展示组件

---

## 总结

这次改进实现了用户选择已向量化文档后立即显示向量结果的功能，大大提升了用户体验。主要变更包括：

1. ✅ 后端支持返回完整向量数据
2. ✅ 前端自动监听文档选择变化
3. ✅ 模型选择器智能自动切换
4. ✅ 按钮文本动态更新
5. ✅ 友好的加载状态提示
6. ✅ 完整的错误处理

用户现在可以：
- 快速浏览历史向量化结果
- 对比不同文档的向量化效果
- 无需重复向量化即可查看数据
- 一键重新向量化并比较结果
