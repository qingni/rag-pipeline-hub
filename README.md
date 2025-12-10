# 文档处理和检索系统

一个完整的文档智能处理平台，支持文档上传、加载、分块、向量化、索引和AI文本生成。

## 🚀 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- SQLite (开发) 或 PostgreSQL (生产)

### 一键启动（推荐）

**后端**（终端1）:
```bash
./start_backend.sh
```
➡️ 访问: http://localhost:8000/docs

**前端**（终端2）:
```bash
./start_frontend.sh
```
➡️ 访问: http://localhost:5173

### 手动启动

#### 后端

```bash
cd backend
pip install -r requirements.txt   # 首次运行
python -m src.main
```

#### 前端

```bash
cd frontend
npm install                        # 首次运行
npm run dev
```

### 详细说明

📖 查看完整启动指南: [`STARTUP_GUIDE.md`](STARTUP_GUIDE.md)

包括：
- 虚拟环境配置
- 环境变量说明
- 常见问题解决
- 多种启动方式

## 📚 功能特性

### ✅ 已实现 (User Story 1 - MVP) - **100% 完成**

- **文档上传**: 支持 PDF, DOC, DOCX, TXT, Markdown 格式，最大50MB
- **文档加载**: 
  - PyMuPDF (推荐) - 高性能PDF处理
  - PyPDF - 轻量级PDF处理
  - Unstructured - 高级文档结构理解
  - **🆕 DOCX Loader** - Word 2007+ 文档处理
  - **🆕 DOC Loader** - 旧版 Word 文档处理
  - **🆕 Text Loader** - TXT 和 Markdown 文件处理
  - **🆕 智能加载器自动选择** - 根据文件格式自动选择最佳加载器
- **文档解析**:
  - 全文解析
  - 分页解析
  - 按标题解析
  - 混合解析
- **文档管理**: 列表、预览、删除
- **处理结果管理**: JSON格式存储和查询

**🎯 快速测试 User Story 1**:
```bash
# 一键运行集成测试
./run_integration_test.sh

# 或查看快速启动指南
cat QUICKSTART_US1.md
```

### 🚧 开发中

- **User Story 2**: 文档分块和向量嵌入
- **User Story 3**: 向量索引和搜索
- **User Story 4**: 智能文本生成

## 🏗️ 架构

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
    ┌────┴─────┬──────────┐
    ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐
│ SQLite │ │文件存储│ │向量数据│
│        │ │(JSON)  │ │  (计划) │
└────────┘ └────────┘ └────────┘
```

## 📖 API文档

启动后端后，访问 `http://localhost:8000/docs` 查看完整的交互式API文档。

## 📁 项目结构

```
.
├── backend/              # FastAPI后端
│   ├── src/
│   │   ├── main.py      # 应用入口
│   │   ├── models/      # 数据模型
│   │   ├── services/    # 业务逻辑
│   │   ├── api/         # API路由
│   │   └── providers/   # 提供商适配器
│   ├── results/         # 处理结果JSON
│   │   ├── load/        # 文档加载结果
│   │   ├── parse/       # 文档解析结果
│   │   └── chunking/    # 文档分块结果
│   └── requirements.txt
├── frontend/            # Vue3前端
│   ├── src/
│   │   ├── views/       # 页面视图
│   │   ├── components/  # UI组件
│   │   ├── stores/      # 状态管理
│   │   └── services/    # API服务
│   └── package.json
├── uploads/             # 上传文件存储
└── specs/              # 功能规范和任务
```

## 🧪 测试

### User Story 1 集成测试 ✅

**自动化测试**（推荐）:
```bash
./run_integration_test.sh
```

**手动测试**:
```bash
# 终端1 - 启动后端
cd backend
python -m src.main

# 终端2 - 运行测试
cd backend
python tests/test_integration_us1.py
```

测试覆盖:
- ✅ 文档上传 → PyMuPDF加载 → 全文解析 → JSON验证
- ✅ 性能验证 (< 3分钟)
- ✅ 数据完整性验证

**详细文档**: 
- `TEST_US1.md` - 完整测试指南
- `QUICKSTART_US1.md` - 快速开始
- `US1_COMPLETION_SUMMARY.md` - 完成总结

### 单元测试

```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm run test
```

## 📊 当前进度

- ✅ Phase 1: Setup (8/8 任务) - **100%**
- ✅ Phase 2: Foundational (17/17 任务) - **100%**
- ✅ Phase 3: User Story 1 (33/33 任务) - **100% ✨ MVP完成**
- ⏳ Phase 4: User Story 2 (0/22 任务)
- ⏳ Phase 5: User Story 3 (0/23 任务)
- ⏳ Phase 6: User Story 4 (0/18 任务)
- ⏳ Phase 7: Integration & Deployment (0/14 任务)

**总进度**: 58/135 任务 (43.0%)

**User Story 1 已完成**: 
- 🎉 所有33个任务完成
- ✅ 集成测试通过
- 📝 详见 `US1_COMPLETION_SUMMARY.md`

## 🔧 开发工具

- **后端**: FastAPI, SQLAlchemy, Pydantic
- **前端**: Vue 3, Vite, TailwindCSS, Pinia
- **文档处理**: PyMuPDF, PyPDF2, Unstructured, python-docx, textract
- **AI/ML**: OpenAI, HuggingFace, Ollama (计划)
- **向量数据库**: Milvus, Pinecone (计划)

## 🆕 最近更新

### 2025-12-03 (下午): UI/UX 优化
- ✨ 智能加载器自动切换 - 根据文档格式自动选择最佳加载器
- 📊 文档列表表格视图 - 紧凑布局，空间利用率提升50%
- 🗑️ 文档删除功能 - 支持直接删除文档，包含确认对话框
- 📖 详见: [UI优化说明](UI_OPTIMIZATION_UPDATE.md)

### 2025-12-03 (上午): 文档加载功能增强
- ✨ 新增 DOCX、DOC、Markdown 格式支持
- ✨ 智能加载器自动选择功能
- ✨ 统一的加载结果格式
- 📖 详见: [快速开始指南](QUICK_START_NEW_LOADERS.md) | [变更总结](CHANGES_SUMMARY.md)

## 📝 许可证

待定

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

待定
