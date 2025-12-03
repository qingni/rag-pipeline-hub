#!/bin/bash
# 后端快速启动脚本

cd backend

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
echo "💡 启动方式:"
echo "   1. uvicorn 命令启动 (推荐)"
echo "   2. python 模块启动"
echo ""

# 默认使用 uvicorn 命令启动
# 如果想使用 python 方式,请注释掉下面这行,取消注释最后一行
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --log-level info

# 备用启动方式: python 模块
# python -m src.main
