#!/bin/bash
# 后端启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT/backend"

# 检查虚拟环境
if [ -d ".venv" ]; then
    echo "🔄 激活虚拟环境..."
    source .venv/bin/activate
fi

# 检查依赖
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 安装依赖..."
    pip install -r requirements.txt
fi

# 检查环境变量
if [ ! -f ".env" ]; then
    echo "⚙️  创建环境配置..."
    cp .env.example .env
fi

# 启动服务
echo "🚀 启动后端服务..."
echo "📍 API文档: http://localhost:8000/docs"
echo "📍 健康检查: http://localhost:8000/health"
echo ""

uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
