#!/bin/bash
# 前端停止脚本

echo "🛑 正在停止前端服务..."

# 释放 5173 端口
lsof -ti:5173 | xargs kill -9 2>/dev/null && echo "✅ 前端服务已停止 (端口 5173 已释放)" || echo "ℹ️ 前端服务未运行"
