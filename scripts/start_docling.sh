#!/bin/bash
# Docling Serve 启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker/docling/docker-compose.yml"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Docling Serve 启动脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查 Docker 是否运行
echo -e "\n${YELLOW}[1/4] 检查 Docker 状态...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker 未运行，请先启动 Docker 或 Colima${NC}"
    echo -e "   运行: ${YELLOW}colima start${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker 正在运行${NC}"

# 检查 docker-compose 文件是否存在
echo -e "\n${YELLOW}[2/4] 检查配置文件...${NC}"
if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
    echo -e "${RED}❌ docker-compose.yml 不存在: $DOCKER_COMPOSE_FILE${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 配置文件存在${NC}"

# 启动 Docling Serve
echo -e "\n${YELLOW}[3/4] 启动 Docling Serve...${NC}"
if command -v docker-compose &> /dev/null; then
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
else
    docker compose -f "$DOCKER_COMPOSE_FILE" up -d
fi

# 等待服务就绪
echo -e "\n${YELLOW}[4/4] 等待服务就绪...${NC}"
echo -e "   首次启动需要下载模型，可能需要 2-5 分钟"

MAX_RETRIES=60
RETRY_INTERVAL=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:5001/health > /dev/null 2>&1; then
        echo -e "\n${GREEN}✅ Docling Serve 已就绪!${NC}"
        echo -e "\n${GREEN}========================================${NC}"
        echo -e "  服务地址: ${YELLOW}http://localhost:5001${NC}"
        echo -e "  API 文档: ${YELLOW}http://localhost:5001/docs${NC}"
        echo -e "  Web UI:   ${YELLOW}http://localhost:5001/ui${NC}"
        echo -e "${GREEN}========================================${NC}"
        exit 0
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "   等待中... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep $RETRY_INTERVAL
done

echo -e "${YELLOW}⚠️  服务启动超时，请检查日志:${NC}"
echo -e "   docker logs docling-serve"
exit 1
