#!/bin/bash
# Milvus 服务停止脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MILVUS_DIR="$PROJECT_ROOT/docker/milvus"

echo "🛑 正在停止 Milvus 服务..."

cd "$MILVUS_DIR"
if command -v docker-compose &> /dev/null; then
    docker-compose down
else
    docker compose down
fi

echo "✅ Milvus 服务已停止"
