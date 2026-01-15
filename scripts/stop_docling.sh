#!/bin/bash
# Docling Serve 停止脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker/docling/docker-compose.yml"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Docling Serve 停止脚本${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${YELLOW}正在停止 Docling Serve...${NC}"

if [ -f "$DOCKER_COMPOSE_FILE" ]; then
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" down
    else
        docker compose -f "$DOCKER_COMPOSE_FILE" down
    fi
    echo -e "${GREEN}✅ Docling Serve 已停止${NC}"
else
    echo -e "${YELLOW}⚠️  配置文件不存在，尝试直接停止容器...${NC}"
    docker stop docling-serve 2>/dev/null || true
    docker rm docling-serve 2>/dev/null || true
    echo -e "${GREEN}✅ 清理完成${NC}"
fi
