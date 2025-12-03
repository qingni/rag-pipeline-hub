# Quick Start: 文档处理和检索系统

**Version**: 1.0.0  
**Last Updated**: 2025-12-01

## 系统概述

文档处理和检索系统是一个完整的文档智能处理平台，支持文档上传、多方式加载、智能分块、向量嵌入、语义搜索和AI文本生成。系统采用前后端分离架构，前端使用 Vue3，后端使用 FastAPI。

## 系统架构

```
┌─────────────────┐
│   Vue3 前端     │  Port 5173
│  (Vite + Tailwind)│
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│  FastAPI 后端   │  Port 8000
│    (Python)      │
└────────┬────────┘
         │
    ┌────┴─────┬──────────┬──────────┐
    ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ SQLite │ │文件存储│ │向量数据│ │AI 模型 │
│/PostgreSQL│ │(JSON) │ │Milvus/ │ │Ollama/ │
│        │ │        │ │Pinecone│ │HuggingFace│
└────────┘ └────────┘ └────────┘ └────────┘
```

## 前置要求

### 后端环境
- Python 3.11+
- pip 或 poetry（包管理）
- SQLite（开发）或 PostgreSQL（生产）

### 前端环境
- Node.js 18+
- npm 或 pnpm（包管理）

### 可选服务
- Milvus（向量数据库，Docker部署）
- Ollama（本地AI模型）

## 安装步骤

### 1. 克隆仓库

```bash
git clone <repository-url>
cd <project-directory>
```

### 2. 后端设置

#### 创建虚拟环境

```bash
cd backend
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

#### 安装依赖

```bash
pip install -r requirements.txt
```

#### 配置环境变量

创建 `.env` 文件：

```bash
# 数据库配置
DATABASE_URL=sqlite:///./app.db  # 开发环境
# DATABASE_URL=postgresql://user:password@localhost/dbname  # 生产环境

# 文件存储路径
UPLOAD_DIR=../uploads
RESULTS_DIR=../results

# API 密钥（可选）
OPENAI_API_KEY=your_openai_api_key
HUGGINGFACE_API_KEY=your_huggingface_api_key
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# 向量数据库配置
MILVUS_HOST=localhost
MILVUS_PORT=19530
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=us-west1-gcp

# Ollama 配置
OLLAMA_BASE_URL=http://localhost:11434
```

#### 初始化数据库

```bash
python -m src.storage.database init
```

#### 启动后端服务

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

后端API将运行在 `http://localhost:8000`

API文档访问：`http://localhost:8000/docs`

### 3. 前端设置

#### 安装依赖

```bash
cd frontend
npm install
# 或
pnpm install
```

#### 配置环境变量

创建 `.env` 文件：

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_UPLOAD_MAX_SIZE=52428800  # 50MB in bytes
```

#### 启动开发服务器

```bash
npm run dev
# 或
pnpm dev
```

前端应用将运行在 `http://localhost:5173`

### 4. 可选服务设置

#### Milvus 向量数据库（Docker）

```bash
# 下载 docker-compose.yml
wget https://github.com/milvus-io/milvus/releases/download/v2.3.0/milvus-standalone-docker-compose.yml -O docker-compose.yml

# 启动 Milvus
docker-compose up -d
```

Milvus将运行在 `localhost:19530`

#### Ollama 本地模型

```bash
# 安装 Ollama
curl https://ollama.ai/install.sh | sh

# 下载模型
ollama pull llama2
ollama pull mistral
```

Ollama将运行在 `localhost:11434`

## 基本使用流程

### 1. 上传文档

通过前端界面或API上传文档：

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -F "file=@/path/to/document.pdf"
```

### 2. 加载文档

```bash
curl -X POST http://localhost:8000/api/v1/processing/load \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "your-document-id",
    "loader_type": "pymupdf"
  }'
```

### 3. 解析文档

```bash
curl -X POST http://localhost:8000/api/v1/processing/parse \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "your-document-id",
    "parse_option": "full_text",
    "include_tables": true
  }'
```

### 4. 分块文档

```bash
curl -X POST http://localhost:8000/api/v1/processing/chunk \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "your-document-id",
    "strategy": "paragraph",
    "chunk_size": 1000,
    "chunk_overlap": 200
  }'
```

### 5. 生成向量嵌入

```bash
curl -X POST http://localhost:8000/api/v1/processing/embed \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "your-document-id",
    "provider": "openai",
    "model_name": "text-embedding-ada-002"
  }'
```

### 6. 创建向量索引

```bash
curl -X POST http://localhost:8000/api/v1/processing/index \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "your-document-id",
    "vector_store": "milvus",
    "collection_name": "documents"
  }'
```

### 7. 执行搜索

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "人工智能应用",
    "search_type": "similarity",
    "top_k": 10
  }'
```

### 8. 生成文本

```bash
curl -X POST http://localhost:8000/api/v1/generation/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "context_chunks": ["chunk-id-1", "chunk-id-2"],
    "prompt": "请基于上下文生成摘要",
    "model_provider": "ollama",
    "model_name": "llama2"
  }'
```

## 前端使用

### 访问前端应用

浏览器打开 `http://localhost:5173`

### 主要功能页面

1. **文档加载** (`/documents/load`)
   - 上传文档
   - 选择加载方式
   - 查看文档预览

2. **文档解析** (`/documents/parse`)
   - 选择解析选项
   - 查看解析结果

3. **文档分块** (`/documents/chunk`)
   - 配置分块策略
   - 预览分块结果

4. **向量嵌入** (`/embeddings`)
   - 选择嵌入提供商
   - 配置嵌入模型
   - 查看嵌入可视化

5. **向量索引** (`/index`)
   - 配置向量数据库
   - 创建索引
   - 管理集合

6. **搜索** (`/search`)
   - 输入查询文本
   - 设置搜索参数
   - 查看排序结果
   - 导出搜索结果

7. **文本生成** (`/generation`)
   - 选择上下文
   - 配置生成参数
   - 查看生成结果

## 常见问题

### 1. 文件上传失败：文件过大

**问题**: 上传文件超过50MB限制

**解决**: 
- 检查文件大小：`ls -lh filename`
- 压缩或分割大文件
- 调整限制（不推荐）：修改 `.env` 中的 `VITE_UPLOAD_MAX_SIZE`

### 2. 向量嵌入失败：API密钥无效

**问题**: OpenAI或HuggingFace API调用失败

**解决**:
- 检查 `.env` 文件中的API密钥配置
- 验证密钥有效性
- 切换到本地HuggingFace模型（无需API密钥）

### 3. Milvus连接失败

**问题**: 无法连接到向量数据库

**解决**:
```bash
# 检查Milvus是否运行
docker ps | grep milvus

# 重启Milvus
docker-compose restart

# 查看日志
docker-compose logs milvus-standalone
```

### 4. 搜索响应慢

**问题**: 搜索时间超过2秒

**解决**:
- 检查向量索引是否正确创建
- 减少 `top_k` 参数值
- 优化向量数据库配置
- 检查网络延迟

## 开发工具

### API 测试

使用 Swagger UI: `http://localhost:8000/docs`

或使用 Postman 导入 OpenAPI 规范：
- `/specs/001-document-processing/contracts/documents.yaml`
- `/specs/001-document-processing/contracts/processing.yaml`
- `/specs/001-document-processing/contracts/search.yaml`

### 日志查看

```bash
# 后端日志
tail -f logs/app.log

# 前端开发服务器日志
# 直接在终端查看
```

### 数据库管理

```bash
# SQLite (开发环境)
sqlite3 app.db

# PostgreSQL (生产环境)
psql -d dbname -U username
```

## 性能指标

根据成功标准（Success Criteria），系统应达到以下性能指标：

- ✅ 文档上传到解析完成：< 3分钟 (SC-001)
- ✅ 并发文档处理：10个文档 (SC-002)
- ✅ 分块和向量化准确率：95%+ (SC-003)
- ✅ 搜索响应时间：< 2秒 (SC-004)
- ✅ 首次使用成功率：90%+ (SC-005)
- ✅ 系统可用性：99%+ (SC-006)
- ✅ 生成质量满意度：80%+ (SC-007)
- ✅ 数据完整性：100% (SC-008)

## 下一步

- 阅读详细的 [API 文档](./contracts/)
- 查看 [数据模型定义](./data-model.md)
- 了解 [技术研究](./research.md)
- 参与开发：查看 [任务列表](./tasks.md)（待生成）

## 技术支持

遇到问题请查看：
- API文档：`http://localhost:8000/docs`
- 日志文件：`logs/app.log`
- 错误追踪：前端控制台或后端日志

## 许可证

[待定]
