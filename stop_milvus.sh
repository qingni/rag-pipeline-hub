#!/bin/bash

# Milvus 服务停止脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MILVUS_DIR="$SCRIPT_DIR/docker/milvus"

echo "🛑 正在停止 Milvus 服务..."

cd "$MILVUS_DIR"
docker-compose down

echo "✅ Milvus 服务已停止"
