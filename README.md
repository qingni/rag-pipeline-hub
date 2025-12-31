# RAG Framework

一个完整的检索增强生成（Retrieval-Augmented Generation）框架，实现从文档处理到智能问答的全流程 RAG 系统。

## 功能特性

| 模块 | 功能 | 状态 |
|------|------|------|
| 文档处理 | PDF、DOCX、DOC、TXT、Markdown 文档上传与加载 | ✅ |
| 文档分块 | 固定大小、语义分块、递归分块、按标题分块 | ✅ |
| 向量嵌入 | OpenAI、HuggingFace、本地模型向量化 | ✅ |
| 向量索引 | Milvus、FAISS 向量存储与索引 | ✅ |
| 语义搜索 | 向量相似度搜索、混合搜索 | ✅ |
| 文本生成 | 基于检索上下文的 LLM 智能问答 | ✅ |

## 技术栈

**后端**
- Python 3.11 + FastAPI
- SQLAlchemy + SQLite/PostgreSQL
- LangChain + OpenAI
- Milvus / FAISS

**前端**
- Vue 3 + Vite
- TDesign + TailwindCSS
- Pinia + Vue Router

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- Docker（用于 Milvus）

### 1. 克隆项目

```bash
git clone https://github.com/qingni/rag-framework-spec.git
cd rag-framework-spec
```

### 2. 配置环境变量

```bash
# 后端
cp backend/.env.example backend/.env
# 编辑 backend/.env，配置 OPENAI_API_KEY 等

# 前端
cp frontend/.env.example frontend/.env
```

### 3. 启动 Milvus（向量数据库）

```bash
./start_milvus.sh
```

### 4. 启动后端

```bash
./start_backend.sh
```

后端 API: http://localhost:8000  
API 文档: http://localhost:8000/docs

### 5. 启动前端

```bash
./start_frontend.sh
```

前端界面: http://localhost:5173

## 项目结构

```
rag-framework-spec/
├── backend/                 # FastAPI 后端
│   ├── src/
│   │   ├── api/            # API 路由
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   ├── schemas/        # Pydantic 模式
│   │   └── providers/      # 外部服务适配器
│   ├── results/            # 处理结果 JSON
│   └── requirements.txt
├── frontend/               # Vue 3 前端
│   ├── src/
│   │   ├── views/          # 页面视图
│   │   ├── components/     # UI 组件
│   │   ├── stores/         # Pinia 状态管理
│   │   └── services/       # API 服务
│   └── package.json
├── documents/              # 功能说明文档
├── specs/                  # 功能规范
├── migrations/             # 数据库迁移
└── uploads/                # 上传文件存储
```

## 核心模块

### 1. 文档处理 (Document Processing)

支持多种文档格式的上传、加载和解析：

- **加载器**: PyMuPDF、PyPDF、Unstructured、python-docx
- **解析模式**: 全文解析、分页解析、按标题解析、混合解析
- **输出格式**: 统一的 JSON 结构

### 2. 文档分块 (Document Chunking)

将文档切分为适合向量化的文本块：

- **分块策略**: 固定大小、语义分块、递归分块、按标题分块
- **参数配置**: chunk_size、chunk_overlap
- **元数据保留**: 来源文件、位置信息

### 3. 向量嵌入 (Vector Embedding)

将文本块转换为向量表示：

- **模型支持**: OpenAI text-embedding-3-small/large、HuggingFace 模型
- **批量处理**: 支持大规模文档的批量向量化
- **维度**: 可配置的向量维度

### 4. 向量索引 (Vector Index)

高效的向量存储与检索：

- **Milvus**: 分布式向量数据库，支持大规模数据
- **FAISS**: 本地向量索引，适合开发测试
- **索引类型**: IVF_FLAT、HNSW 等

### 5. 语义搜索 (Semantic Search)

基于向量相似度的智能搜索：

- **搜索类型**: 向量搜索、混合搜索
- **相似度算法**: 余弦相似度、欧氏距离、内积
- **结果排序**: Top-K 检索、相似度阈值过滤

### 6. 文本生成 (Text Generation)

基于检索上下文的 LLM 问答：

- **模型支持**: GPT-4、GPT-3.5-turbo 等 OpenAI 模型
- **流式输出**: 支持 SSE 流式响应
- **引用标注**: 自动标注回答的来源引用
- **历史记录**: 保存生成历史，支持查询和管理

## API 概览

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/documents` | POST | 上传文档 |
| `/api/documents/{id}/load` | POST | 加载文档 |
| `/api/documents/{id}/chunk` | POST | 分块文档 |
| `/api/embeddings/embed` | POST | 向量化文本块 |
| `/api/vector-index/index` | POST | 创建向量索引 |
| `/api/search` | POST | 语义搜索 |
| `/api/generation/generate` | POST | 文本生成 |
| `/api/generation/generate/stream` | POST | 流式文本生成 |

完整 API 文档请访问: http://localhost:8000/docs

## 文档

详细的功能说明文档位于 `documents/` 目录：

- [文档加载](documents/load/README.md)
- [文档分块](documents/chunk/README.md)
- [向量嵌入](documents/embedding/README.md)
- [向量索引](documents/vector-index/README.md)
- [语义搜索](documents/search/README.md)
- [文本生成](documents/generation/README.md)

## 版本历史

| 版本 | 功能 | 日期 |
|------|------|------|
| v0.6.0 | 文本生成 (Text Generation) | 2024-12 |
| v0.5.0 | 语义搜索 (Search Query) | 2024-12 |
| v0.4.0 | 向量索引 (Vector Index) | 2024-12 |
| v0.3.0 | 向量嵌入 (Vector Embedding) | 2024-12 |
| v0.2.0 | 文档分块 (Document Chunking) | 2024-12 |
| v0.1.0 | 文档处理 (Document Processing) | 2024-12 |

## 开发

### 运行测试

```bash
# 后端测试
cd backend
pytest

# 前端构建
cd frontend
npm run build
```

### 停止服务

```bash
# 停止 Milvus
./stop_milvus.sh

# 释放端口
lsof -ti:8000 | xargs kill -9  # 后端
lsof -ti:5173 | xargs kill -9  # 前端
```

## 许可证

[Apache License 2.0](LICENSE)
