#!/bin/bash

# 文档分块功能优化演示脚本
# 用途: 验证三项优化功能是否正常工作

echo "======================================"
echo "  文档分块功能优化 - 演示验证"
echo "======================================"
echo ""

# 检查服务状态
echo "1. 检查服务状态..."
echo "-----------------------------------"

# 检查后端
BACKEND_PID=$(ps aux | grep -E "python.*src.main|uvicorn" | grep -v grep | awk '{print $2}' | head -1)
if [ -n "$BACKEND_PID" ]; then
    echo "✅ 后端服务运行中 (PID: $BACKEND_PID)"
else
    echo "❌ 后端服务未运行"
    echo "   启动命令: cd backend && python -m src.main"
    exit 1
fi

# 检查前端
FRONTEND_PID=$(ps aux | grep -E "vite|npm.*dev" | grep -v grep | awk '{print $2}' | head -1)
if [ -n "$FRONTEND_PID" ]; then
    echo "✅ 前端服务运行中 (PID: $FRONTEND_PID)"
else
    echo "❌ 前端服务未运行"
    echo "   启动命令: cd frontend && npm run dev"
    exit 1
fi

echo ""

# 测试新增API端点
echo "2. 测试新增API端点..."
echo "-----------------------------------"

# 先获取一个文档ID
echo "2.1 获取文档列表..."
DOC_RESPONSE=$(curl -s "http://localhost:8000/api/chunking/documents/parsed?page=1&page_size=5")
DOC_COUNT=$(echo $DOC_RESPONSE | grep -o '"total":[0-9]*' | grep -o '[0-9]*')

if [ -n "$DOC_COUNT" ] && [ "$DOC_COUNT" -gt 0 ]; then
    echo "✅ 找到 $DOC_COUNT 个已解析文档"
    
    # 提取第一个文档ID
    DOC_ID=$(echo $DOC_RESPONSE | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "   文档ID: $DOC_ID"
    
    echo ""
    echo "2.2 测试获取最近分块结果API..."
    LATEST_RESPONSE=$(curl -s "http://localhost:8000/api/chunking/result/latest/$DOC_ID")
    
    if echo $LATEST_RESPONSE | grep -q '"success":true'; then
        HAS_DATA=$(echo $LATEST_RESPONSE | grep -o '"data":[^}]*' | wc -l)
        if [ "$HAS_DATA" -gt 0 ]; then
            RESULT_ID=$(echo $LATEST_RESPONSE | grep -o '"result_id":"[^"]*"' | cut -d'"' -f4)
            STRATEGY=$(echo $LATEST_RESPONSE | grep -o '"strategy_type":"[^"]*"' | cut -d'"' -f4)
            CHUNKS=$(echo $LATEST_RESPONSE | grep -o '"total_chunks":[0-9]*' | grep -o '[0-9]*')
            
            if [ -n "$RESULT_ID" ]; then
                echo "✅ API端点正常工作"
                echo "   结果ID: $RESULT_ID"
                echo "   策略: $STRATEGY"
                echo "   分块数: $CHUNKS"
            else
                echo "⚠️  该文档暂无分块结果"
            fi
        else
            echo "⚠️  该文档暂无分块结果 (正常情况)"
        fi
    else
        echo "❌ API调用失败"
        echo "   响应: $LATEST_RESPONSE"
    fi
else
    echo "⚠️  没有找到已解析的文档"
    echo "   建议: 先上传并解析一些文档"
fi

echo ""

# 前端功能验证指引
echo "3. 前端功能验证指引"
echo "-----------------------------------"
echo "请在浏览器中打开前端页面进行验证:"
echo ""
echo "🌐 前端地址: http://localhost:5173/chunking"
echo ""
echo "验证步骤:"
echo ""
echo "✓ 优化1: 默认选择第一个文档"
echo "  1. 打开分块页面"
echo "  2. 观察左侧文档列表"
echo "  3. 第一个文档应该自动被选中(高亮显示)"
echo ""
echo "✓ 优化2: 展示最近分块结果"
echo "  1. 选择一个已分块过的文档"
echo "  2. 右侧应立即显示该文档的最近分块结果"
echo "  3. 包括分块列表、统计信息等"
echo ""
echo "✓ 优化3: 智能匹配策略和参数"
echo "  1. 选择一个文档"
echo "  2. 切换不同的分块策略"
echo "  3. 右侧结果应自动切换到对应策略的结果"
echo "  4. 修改参数配置"
echo "  5. 如果存在匹配的历史结果,应自动展示"
echo ""

# 性能测试
echo "4. 性能测试"
echo "-----------------------------------"
if [ -n "$DOC_ID" ]; then
    echo "测试API响应时间..."
    
    START_TIME=$(date +%s%N)
    curl -s "http://localhost:8000/api/chunking/result/latest/$DOC_ID" > /dev/null
    END_TIME=$(date +%s%N)
    
    DURATION=$((($END_TIME - $START_TIME) / 1000000))
    echo "API响应时间: ${DURATION}ms"
    
    if [ "$DURATION" -lt 100 ]; then
        echo "✅ 性能达标 (目标: < 100ms)"
    else
        echo "⚠️  性能需优化 (当前: ${DURATION}ms, 目标: < 100ms)"
    fi
fi

echo ""

# 代码检查
echo "5. 代码变更检查"
echo "-----------------------------------"
echo "已修改的关键文件:"
git diff --name-only HEAD~2 HEAD | grep -E "(DocumentSelector|chunkingStore|chunkingService|chunking.py)" | while read file; do
    echo "  ✓ $file"
done

echo ""

# 总结
echo "======================================"
echo "  验证完成"
echo "======================================"
echo ""
echo "📋 下一步操作:"
echo "  1. 在浏览器中手动验证前端功能"
echo "  2. 测试不同场景的用户操作流程"
echo "  3. 确认性能指标符合要求"
echo "  4. 收集用户反馈"
echo ""
echo "📚 相关文档:"
echo "  - 实施总结: OPTIMIZATION_SUMMARY.md"
echo "  - 使用指南: OPTIMIZATION_USAGE_GUIDE.md"
echo "  - 技术细节: OPTIMIZATION_IMPLEMENTATION.md"
echo ""
