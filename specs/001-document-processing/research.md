# Research: 文档处理和检索系统技术选型

**Date**: 2025-12-01  
**Feature**: 001-document-processing  
**Phase**: 0 - Outline & Research

## 研究目标

解决技术上下文中的所有未知项，确定最佳技术选型和实践方案，为详细设计提供依据。

## 1. 文档处理库选型

### 决策：PyMuPDF (主推荐) + PyPDF (备选) + Unstructured (高级场景)

**研究内容**:
- **PyMuPDF (fitz)**: 性能最优，支持PDF、EPUB等格式，提取文本、图片、表格能力强
- **PyPDF2**: 纯Python实现，依赖少，但功能相对基础
- **Unstructured**: 专门用于非结构化文档处理，支持复杂布局和表格识别

**理由**:
- PyMuPDF 性能最佳（C++实现），适合大部分场景
- PyPDF 作为轻量级备选，无二进制依赖
- Unstructured 用于需要高级文档结构理解的场景

**替代方案**:
- PDFMiner: 功能强大但速度较慢
- PyPDF4: PyPDF2 的分支，维护不活跃

**实施要点**:
- 使用适配器模式统一三种加载器接口
- 提供加载器切换配置
- 性能基准测试：目标 < 30秒/10MB PDF

## 2. 文档分块策略

### 决策：LangChain TextSplitter + 自定义语义分块

**研究内容**:
- **按字符分块**: 固定字符数分块，简单高效
- **按段落分块**: 保留文档自然段落结构
- **语义分块**: 基于句子嵌入的相似度分块
- **滑动窗口**: 重叠分块，避免上下文丢失

**理由**:
- LangChain 提供成熟的分块工具（CharacterTextSplitter, RecursiveCharacterTextSplitter）
- 语义分块可基于句子嵌入实现，提高检索相关性
- 支持自定义chunk_size和chunk_overlap参数

**最佳实践**:
- 默认 chunk_size: 1000 字符
- chunk_overlap: 200 字符
- 保留元数据（页码、章节、来源文档）

## 3. 向量嵌入提供商集成

### 决策：OpenAI (默认) + HuggingFace (本地) + Bedrock (企业)

**研究内容**:
- **OpenAI Embeddings**: text-embedding-ada-002, 1536维，效果优秀
- **HuggingFace**: sentence-transformers, 支持本地部署，多语言模型
- **AWS Bedrock**: Amazon Titan Embeddings, 企业级安全和性能

**接口设计**:
```python
class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        pass
    
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        pass
```

**配置管理**:
- API密钥通过环境变量配置
- 支持批量嵌入以提高效率
- 实现重试和错误处理

## 4. 向量数据库选型

### 决策：Milvus (主推荐) + Pinecone (云托管备选)

**研究内容**:
- **Milvus**: 开源向量数据库，高性能，支持混合查询，可本地部署
- **Pinecone**: 云托管向量数据库，零运维，按使用付费
- **Qdrant**: 新兴开源方案，Rust实现，性能优秀

**理由**:
- Milvus 适合本地部署和自主控制
- Pinecone 适合快速原型和云部署
- 统一向量存储接口便于切换

**性能目标**:
- 索引构建: < 5秒/1000向量
- 搜索响应: < 2秒（SC-004要求）
- 支持 top-k 相似度搜索和过滤

## 5. AI 模型集成

### 决策：Ollama (本地) + HuggingFace Inference API (云)

**研究内容**:
- **Ollama**: 本地运行大语言模型，支持 Llama2, Mistral 等
- **HuggingFace**: 云端推理API，模型选择丰富
- **OpenAI GPT**: 高质量但成本较高

**使用场景**:
- 文本摘要生成
- 问答生成
- 基于上下文的内容生成

**实施策略**:
- 提供模型切换配置
- 实现流式输出支持
- 设置生成参数（temperature, max_tokens等）

## 6. 数据持久化策略

### 决策：SQLite (开发) + PostgreSQL (生产) + 文件系统

**研究内容**:
- **元数据存储**: 关系型数据库（文档信息、处理记录、查询历史）
- **处理结果**: JSON文件，文件系统存储
- **向量数据**: 向量数据库专用存储

**数据库Schema设计**:
```sql
-- documents 表
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    filename VARCHAR(255),
    format VARCHAR(50),
    size_bytes INTEGER,
    upload_time TIMESTAMP,
    storage_path TEXT
);

-- processing_results 表
CREATE TABLE processing_results (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    processing_type VARCHAR(50),
    result_path TEXT,
    created_at TIMESTAMP,
    status VARCHAR(20)
);
```

**文件命名规范**:
- 格式：`{document_name}_{timestamp}_{processing_type}.json`
- 示例：`report_20251201120000_parsed.json`

## 7. 前端状态管理

### 决策：Pinia (官方推荐)

**研究内容**:
- **Pinia**: Vue3 官方状态管理，TypeScript支持好
- **Vuex**: 旧版状态管理，不推荐用于新项目

**Store 设计**:
- `documentStore`: 管理文档列表和上传
- `processingStore`: 管理处理状态和进度
- `searchStore`: 管理搜索查询和结果

## 8. API 设计模式

### 决策：RESTful API + OpenAPI 规范

**端点设计原则**:
- **资源命名**: 使用名词复数（/documents, /chunks, /embeddings）
- **HTTP方法**: GET(查询), POST(创建), PUT(更新), DELETE(删除)
- **状态码**: 200(成功), 201(创建), 400(客户端错误), 500(服务器错误)

**响应格式**:
```json
{
  "success": true,
  "data": {...},
  "message": "操作成功",
  "timestamp": "2025-12-01T12:00:00Z"
}
```

**错误响应**:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "文件大小超过限制",
    "details": {...}
  }
}
```

## 9. 文件上传处理

### 决策：分块上传 + 进度跟踪

**研究内容**:
- **前端**: File API + FormData
- **后端**: FastAPI UploadFile + 临时存储
- **限制**: 50MB 单文件限制（SC-002要求）

**实施流程**:
1. 前端验证文件大小和格式
2. 上传到临时目录
3. 后端验证和处理
4. 移动到永久存储
5. 返回文档ID

**安全考虑**:
- 文件类型白名单：pdf, doc, docx, txt
- 文件名消毒（移除特殊字符）
- 病毒扫描（可选，生产环境）

## 10. 性能优化策略

### 决策：异步处理 + 任务队列

**研究内容**:
- **异步处理**: FastAPI async/await
- **任务队列**: Celery + Redis（可选，用于重量级任务）
- **缓存**: Redis 缓存常用查询结果

**优化目标**:
- 文档处理并发：支持10个并发（SC-002）
- 搜索响应：< 2秒（SC-004）
- 系统可用性：99%（SC-006）

**实施策略**:
- 大文档异步处理，返回任务ID
- WebSocket 推送处理进度
- 结果缓存减少重复计算

## 总结

所有技术选型均已确定，无遗留NEEDS CLARIFICATION项。选型遵循以下原则：
1. **稳定性优先**: 选择成熟、活跃维护的技术
2. **灵活性**: 支持多提供商切换，符合宪章II
3. **性能**: 满足所有性能目标（SC-001至SC-008）
4. **简洁性**: MVP阶段避免过度设计

下一步：进入 Phase 1 设计阶段，生成数据模型和API合约。
