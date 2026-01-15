#!/bin/bash
# 后端停止脚本

echo "🛑 正在停止后端服务..."

# 释放 8000 端口
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✅ 后端服务已停止 (端口 8000 已释放)" || echo "ℹ️ 后端服务未运行"
