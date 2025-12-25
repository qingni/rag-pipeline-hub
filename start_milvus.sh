#!/bin/bash

# Milvus 服务启动脚本
# 前置条件：需要先启动 Colima (colima start)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MILVUS_DIR="$SCRIPT_DIR/docker/milvus"

echo "🚀 正在启动 Milvus 服务..."

# 检查 Docker 是否可用
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Colima: colima start"
    exit 1
fi

# 启动 Milvus
cd "$MILVUS_DIR"
docker-compose up -d

# 等待服务启动
echo "⏳ 等待 Milvus 服务启动..."
sleep 10

# 检查健康状态
if curl -s http://localhost:9091/healthz > /dev/null 2>&1; then
    echo "✅ Milvus 服务启动成功！"
    echo ""
    echo "📌 服务信息："
    echo "   - Milvus API: localhost:19530"
    echo "   - 健康检查: localhost:9091/healthz"
    echo "   - MinIO 控制台: localhost:9001 (minioadmin/minioadmin)"
    echo ""
    echo "📋 常用命令："
    echo "   - 查看状态: docker ps"
    echo "   - 停止服务: docker-compose -f $MILVUS_DIR/docker-compose.yml down"
    echo "   - 查看日志: docker logs milvus-standalone"
else
    echo "⚠️  Milvus 服务可能还在启动中，请稍后检查: curl http://localhost:9091/healthz"
fi
