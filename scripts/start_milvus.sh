#!/bin/bash
# Milvus 服务启动脚本
# 前置条件：需要先启动 Colima (colima start)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MILVUS_DIR="$PROJECT_ROOT/docker/milvus"

# Milvus 完整服务需要的三个容器
REQUIRED_CONTAINERS=("milvus-etcd" "milvus-minio" "milvus-standalone")

echo "🚀 正在启动 Milvus 服务..."
echo ""

# ====== 第一步：检查 Docker 是否可用 ======
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Colima："
    echo "   colima start"
    exit 1
fi
echo "✅ Docker 环境正常"

# ====== 第二步：检查端口是否被非 Docker 进程占用 ======
check_port() {
    local port=$1
    local name=$2
    if lsof -ti:$port > /dev/null 2>&1; then
        local pid=$(lsof -ti:$port | head -1)
        local proc=$(ps -p $pid -o comm= 2>/dev/null)
        local full_cmd=$(ps -p $pid -o args= 2>/dev/null)
        # 如果是 docker/colima 相关进程则跳过（可能是之前的 Milvus 容器端口转发）
        if [[ "$proc" == *"docker"* ]] || [[ "$proc" == *"com.docker"* ]] || \
           [[ "$full_cmd" == *"colima"* ]] || [[ "$full_cmd" == *"lima"* ]]; then
            return 0
        fi
        echo "⚠️  端口 $port ($name) 被进程 $proc (PID: $pid) 占用"
        return 1
    fi
    return 0
}

PORT_OK=true
check_port 19530 "Milvus API" || PORT_OK=false
check_port 9091 "Milvus Health" || PORT_OK=false
check_port 9000 "MinIO API" || PORT_OK=false
check_port 9001 "MinIO Console" || PORT_OK=false

if [ "$PORT_OK" = false ]; then
    echo ""
    echo "❌ 存在端口冲突，请先释放相关端口"
    echo "   释放端口命令: lsof -ti:<PORT> | xargs kill -9"
    exit 1
fi

# ====== 第三步：清理残留容器，确保干净启动 ======
echo ""
echo "🧹 清理残留容器..."
cd "$MILVUS_DIR"

# 停止并移除已有容器（包括异常退出的）
docker-compose down > /dev/null 2>&1

# 再次确认清理干净（处理孤儿容器）
for container in "${REQUIRED_CONTAINERS[@]}"; do
    if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
        echo "   移除残留容器: $container"
        docker rm -f "$container" > /dev/null 2>&1
    fi
done
echo "✅ 清理完成"

# ====== 第四步：启动所有服务 ======
echo ""
echo "🔄 启动 Milvus 服务组件（etcd + minio + standalone）..."
docker-compose up -d 2>&1

if [ $? -ne 0 ]; then
    echo "❌ docker-compose up 失败，请检查上方错误信息"
    exit 1
fi

# ====== 第五步：逐个检查容器是否正常运行 ======
echo ""
echo "🔍 检查容器运行状态..."
sleep 5  # 给容器一点启动时间

ALL_RUNNING=true
for container in "${REQUIRED_CONTAINERS[@]}"; do
    status=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null)
    if [ "$status" = "running" ]; then
        echo "   ✅ $container: 运行中"
    elif [ "$status" = "exited" ] || [ "$status" = "dead" ]; then
        echo "   ❌ $container: 已退出 (status=$status)"
        echo "      最近日志:"
        docker logs --tail 10 "$container" 2>&1 | sed 's/^/      /'
        ALL_RUNNING=false
    elif [ -z "$status" ]; then
        echo "   ❌ $container: 未找到"
        ALL_RUNNING=false
    else
        echo "   ⚠️  $container: $status"
        ALL_RUNNING=false
    fi
done

if [ "$ALL_RUNNING" = false ]; then
    echo ""
    echo "❌ 部分容器未正常运行，请根据上方日志排查问题"
    echo "   查看完整日志: docker logs <容器名>"
    exit 1
fi

# ====== 第六步：等待 Milvus 健康检查通过 ======
echo ""
echo "⏳ 等待 Milvus 服务就绪（最多 60 秒）..."

MAX_RETRIES=12
RETRY_INTERVAL=5
HEALTHY=false

for i in $(seq 1 $MAX_RETRIES); do
    # 先检查 standalone 容器是否还在运行
    status=$(docker inspect -f '{{.State.Status}}' "milvus-standalone" 2>/dev/null)
    if [ "$status" != "running" ]; then
        echo ""
        echo "   ❌ milvus-standalone 容器已退出！"
        echo "      容器日志:"
        docker logs --tail 20 milvus-standalone 2>&1 | sed 's/^/      /'
        exit 1
    fi

    # 健康检查
    if curl -sf http://localhost:9091/healthz > /dev/null 2>&1; then
        HEALTHY=true
        break
    fi
    echo "   等待中... ($((i * RETRY_INTERVAL))/60 秒)"
    sleep $RETRY_INTERVAL
done

echo ""
if [ "$HEALTHY" = true ]; then
    echo "============================================"
    echo "  ✅ Milvus 服务启动成功！"
    echo "============================================"
    echo ""
    echo "📌 服务信息："
    echo "   - Milvus API:   localhost:19530"
    echo "   - 健康检查:     http://localhost:9091/healthz"
    echo "   - MinIO 控制台: http://localhost:9001 (minioadmin/minioadmin)"
    echo ""
    echo "📌 容器管理："
    echo "   - 查看状态: docker ps | grep milvus"
    echo "   - 停止服务: cd $MILVUS_DIR && docker-compose down"
    echo "   - 查看日志: docker logs -f milvus-standalone"
else
    echo "============================================"
    echo "  ⚠️  Milvus 服务未能在 60 秒内就绪"
    echo "============================================"
    echo ""
    echo "可能仍在启动中（Milvus 首次启动较慢），请稍后手动检查："
    echo "   curl http://localhost:9091/healthz"
    echo ""
    echo "如果持续无法访问，请查看日志："
    echo "   docker logs milvus-standalone"
    echo "   docker logs milvus-etcd"
    exit 1
fi
