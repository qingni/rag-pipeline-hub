# 文档处理和检索系统 - 后端

FastAPI 后端服务，提供文档处理、向量化和搜索功能。

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并配置必要的参数：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置API密钥等配置。

### 3. 初始化数据库

```bash
python -m src.storage.database init
```

### 4. 启动服务

```bash
# 开发模式（自动重载）
python -m src.main

# 或使用 uvicorn
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

服务将在 `http://localhost:8000` 启动。

### 5. 访问API文档

浏览器打开 `http://localhost:8000/docs` 查看交互式API文档。

## 项目结构

```
backend/
├── src/
│   ├── main.py              # FastAPI应用入口
│   ├── config.py            # 配置管理
│   ├── models/              # 数据模型
│   ├── services/            # 业务逻辑
│   ├── providers/           # 第三方提供商适配器
│   ├── api/                 # API路由
│   ├── storage/             # 存储管理
│   └── utils/               # 工具函数
├── results/                 # 处理结果存储
│   ├── load/                # 文档加载结果
│   ├── parse/               # 文档解析结果
│   └── chunking/            # 文档分块结果
├── tests/                   # 测试
├── requirements.txt         # Python依赖
└── .env.example            # 环境变量示例
```

## 主要功能

- ✅ 文档上传和管理
- ✅ 多种文档加载器（PyMuPDF, PyPDF, Unstructured）
- ✅ 文档解析（全文、分页、按标题等）
- 🚧 文档分块
- 🚧 向量嵌入
- 🚧 向量索引
- 🚧 语义搜索
- 🚧 文本生成

## 开发命令

```bash
# 运行测试
pytest

# 代码格式化
black src/

# 类型检查
mypy src/

# 清空数据库
python -m src.storage.database drop
```

## 环境要求

- Python 3.11+
- SQLite (开发) / PostgreSQL (生产)
