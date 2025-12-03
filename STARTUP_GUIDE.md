# 🚀 服务启动指南

## 📋 目录
- [快速启动](#快速启动)
- [后端启动详解](#后端启动详解)
- [前端启动详解](#前端启动详解)
- [验证服务](#验证服务)
- [常见问题](#常见问题)

---

## ⚡ 快速启动

### 后端（终端1）
```bash
cd backend
python -m src.main
```
➡️ 访问: http://localhost:8000

### 前端（终端2）
```bash
cd frontend
npm run dev
```
➡️ 访问: http://localhost:5173

---

## 🔧 后端启动详解

### 方式1: 直接启动（最简单）

```bash
# 1. 进入后端目录
cd backend

# 2. 安装依赖（首次运行）
pip install -r requirements.txt

# 3. 启动服务
python -m src.main
```

### 方式2: 使用虚拟环境（推荐）

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境（首次）
python3 -m venv venv

# 3. 激活虚拟环境
source venv/bin/activate          # macOS/Linux
# 或
venv\Scripts\activate              # Windows

# 4. 安装依赖
pip install -r requirements.txt

# 5. 配置环境变量（首次）
cp .env.example .env
# 编辑 .env 文件（可选，默认配置已可用）

# 6. 启动服务
python -m src.main
```

### 方式3: 使用 Uvicorn 直接启动

```bash
cd backend
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 后端启动成功标志

看到以下输出表示启动成功：
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 后端访问地址

- **API文档**: http://localhost:8000/docs （Swagger UI）
- **ReDoc文档**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health
- **根路径**: http://localhost:8000/

### 后端环境变量说明

编辑 `backend/.env` 文件配置：

```bash
# 数据库配置
DATABASE_URL=sqlite:///./app.db          # 开发环境用SQLite
# DATABASE_URL=postgresql://...          # 生产环境用PostgreSQL

# 文件存储
UPLOAD_DIR=../uploads                    # 上传文件目录
RESULTS_DIR=../results                   # 处理结果目录
MAX_UPLOAD_SIZE=52428800                 # 50MB

# 服务器配置
HOST=0.0.0.0                             # 监听所有网卡
PORT=8000                                # 端口
RELOAD=true                              # 自动重载（开发模式）
LOG_LEVEL=info                           # 日志级别

# AI服务配置（可选，User Story 2-4需要）
OPENAI_API_KEY=sk-...                    # OpenAI API密钥
HUGGINGFACE_API_KEY=hf_...               # HuggingFace API密钥
OLLAMA_BASE_URL=http://localhost:11434   # Ollama本地服务
```

**注意**: User Story 1只需要基础配置，AI相关配置可以暂时留空。

---

## 🎨 前端启动详解

### 方式1: 开发模式启动（推荐）

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖（首次运行）
npm install
# 或使用yarn
yarn install

# 3. 配置环境变量（首次）
cp .env.example .env
# 编辑 .env 文件（可选，默认配置已可用）

# 4. 启动开发服务器
npm run dev
# 或使用yarn
yarn dev
```

### 方式2: 预览生产构建

```bash
cd frontend

# 1. 构建生产版本
npm run build

# 2. 预览构建结果
npm run preview
```

### 前端启动成功标志

看到以下输出表示启动成功：
```
  VITE v5.0.0  ready in 500 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.1.100:5173/
  ➜  press h + enter to show help
```

### 前端访问地址

- **主页**: http://localhost:5173/
- **文档加载**: http://localhost:5173/document-load
- **文档解析**: http://localhost:5173/document-parse

### 前端环境变量说明

编辑 `frontend/.env` 文件配置：

```bash
# API配置
VITE_API_BASE_URL=http://localhost:8000/api/v1

# 上传限制
VITE_UPLOAD_MAX_SIZE=52428800           # 50MB

# 功能开关
VITE_ENABLE_OLLAMA=true                 # 启用Ollama
VITE_ENABLE_HUGGINGFACE=true            # 启用HuggingFace
```

### 前端可用命令

```bash
npm run dev         # 启动开发服务器
npm run build       # 构建生产版本
npm run preview     # 预览生产构建
npm run lint        # 代码检查
```

---

## ✅ 验证服务

### 1. 验证后端

**命令行验证**:
```bash
# 健康检查
curl http://localhost:8000/health

# 预期输出
{
  "success": true,
  "status": "healthy",
  "service": "document-processing-api"
}
```

**浏览器验证**:
- 打开 http://localhost:8000/docs
- 应该看到 Swagger API 文档界面

### 2. 验证前端

**浏览器验证**:
- 打开 http://localhost:5173
- 应该看到应用主界面
- 左侧导航栏可见
- 可以访问各个功能页面

### 3. 验证前后端连接

**方式1: 使用集成测试**
```bash
./run_integration_test.sh
```

**方式2: 手动验证**
1. 访问前端 http://localhost:5173
2. 进入"文档加载"页面
3. 尝试上传一个PDF文件
4. 查看是否成功上传并显示在列表中

---

## 🐛 常见问题

### 后端问题

#### Q1: ModuleNotFoundError: No module named 'xxx'
**原因**: 依赖未安装  
**解决**:
```bash
cd backend
pip install -r requirements.txt
```

#### Q2: Address already in use (端口8000被占用)
**原因**: 端口已被其他程序占用  
**解决方案1**: 修改端口
```bash
# 编辑 backend/.env
PORT=8001

# 或直接指定
uvicorn src.main:app --port 8001
```

**解决方案2**: 杀掉占用进程
```bash
# macOS/Linux
lsof -i :8000
kill -9 <PID>

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

#### Q3: SQLite database is locked
**原因**: 数据库被其他进程占用  
**解决**:
```bash
# 删除数据库文件重新初始化
rm backend/app.db
python -m src.main
```

#### Q4: Permission denied: './uploads' or './results'
**原因**: 目录权限问题  
**解决**:
```bash
mkdir -p uploads results
chmod 755 uploads results
```

### 前端问题

#### Q1: npm install 失败
**原因**: 网络问题或npm源慢  
**解决**:
```bash
# 使用国内镜像
npm config set registry https://registry.npmmirror.com
npm install

# 或使用 yarn
yarn install
```

#### Q2: Module not found 或构建错误
**原因**: node_modules损坏  
**解决**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

#### Q3: 端口5173被占用
**原因**: 端口冲突  
**解决**: Vite会自动尝试下一个可用端口（5174, 5175...）
或手动指定:
```bash
npm run dev -- --port 5174
```

#### Q4: 前端无法连接后端
**原因**: 后端未启动或CORS配置问题  
**解决**:
1. 确认后端已启动: `curl http://localhost:8000/health`
2. 检查 `frontend/.env` 中的 `VITE_API_BASE_URL`
3. 查看浏览器控制台是否有CORS错误

### 其他问题

#### Q5: Python版本不兼容
**要求**: Python 3.11+  
**检查**:
```bash
python --version
# 或
python3 --version
```

**解决**: 升级Python或使用pyenv管理多版本

#### Q6: Node.js版本不兼容
**要求**: Node.js 18+  
**检查**:
```bash
node --version
```

**解决**: 使用nvm管理Node.js版本
```bash
# 安装nvm后
nvm install 18
nvm use 18
```

---

## 🔄 重启服务

### 重启后端
```bash
# 停止: Ctrl+C

# 重启
cd backend
python -m src.main
```

### 重启前端
```bash
# 停止: Ctrl+C

# 重启
cd frontend
npm run dev
```

---

## 🌟 推荐工作流

### 开发模式（最常用）

**终端1 - 后端**:
```bash
cd backend
source venv/bin/activate  # 如果使用虚拟环境
python -m src.main
```

**终端2 - 前端**:
```bash
cd frontend
npm run dev
```

**终端3 - 测试/命令**:
```bash
# 用于运行测试或其他命令
./run_integration_test.sh
# 或
./demo_us1.sh
```

### 后台运行（生产环境）

**后端**:
```bash
cd backend
nohup python -m src.main > ../logs/backend.log 2>&1 &
```

**前端**（需先构建）:
```bash
cd frontend
npm run build
# 使用nginx或其他web服务器托管 dist/ 目录
```

---

## 📊 服务状态检查

创建一个快速检查脚本：

```bash
#!/bin/bash
echo "=== 服务状态检查 ==="

# 检查后端
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 后端服务运行正常 (http://localhost:8000)"
else
    echo "❌ 后端服务未运行"
fi

# 检查前端
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "✅ 前端服务运行正常 (http://localhost:5173)"
else
    echo "❌ 前端服务未运行"
fi
```

保存为 `check_services.sh` 并执行：
```bash
chmod +x check_services.sh
./check_services.sh
```

---

## 📝 总结

### 最简启动步骤

**首次运行**:
```bash
# 后端
cd backend && pip install -r requirements.txt && python -m src.main

# 前端（新终端）
cd frontend && npm install && npm run dev
```

**日常启动**:
```bash
# 后端
cd backend && python -m src.main

# 前端（新终端）
cd frontend && npm run dev
```

### 访问地址
- 🔙 **后端API**: http://localhost:8000
- 🔙 **API文档**: http://localhost:8000/docs
- 🎨 **前端界面**: http://localhost:5173

### 环境要求
- ✅ Python 3.11+
- ✅ Node.js 18+
- ✅ pip 和 npm

---

**快速参考**: 遇到问题先检查：
1. 依赖是否安装完整
2. 端口是否被占用
3. 环境变量是否配置
4. Python/Node版本是否符合要求
