#!/bin/bash
# 前端启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT/frontend"

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo "📦 安装依赖..."
    npm install
fi

# 检查环境变量
if [ ! -f ".env" ]; then
    echo "⚙️  创建环境配置..."
    cp .env.example .env
fi

# 启动服务
echo "🚀 启动前端服务..."
echo "📍 访问地址: http://localhost:5173"
echo ""
npm run dev
