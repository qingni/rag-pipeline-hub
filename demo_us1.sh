#!/bin/bash
# User Story 1 演示脚本
# 快速展示文档上传、加载、解析功能

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

API_URL="http://localhost:8000"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  User Story 1 - 功能演示${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# 检查服务器
echo -e "${YELLOW}检查后端服务器...${NC}"
if ! curl -s "$API_URL/health" > /dev/null 2>&1; then
    echo "❌ 后端服务器未运行"
    echo "请先启动: cd backend && python -m src.main"
    exit 1
fi
echo -e "${GREEN}✓ 后端服务器运行正常${NC}"
echo ""

# 检查是否有测试文件
TEST_PDF="backend/tests/fixtures/sample.pdf"
if [ ! -f "$TEST_PDF" ]; then
    echo -e "${YELLOW}创建测试PDF...${NC}"
    python3 -c "
import sys
sys.path.insert(0, 'backend')
from tests.test_integration_us1 import IntegrationTestUS1
test = IntegrationTestUS1()
test.create_test_pdf()
" 2>/dev/null || echo "使用已有PDF"
fi

echo -e "${BLUE}=== 演示1: 文档上传 ===${NC}"
echo "上传测试PDF文档..."
UPLOAD_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/documents" \
  -F "file=@$TEST_PDF" \
  -H "accept: application/json")

if echo "$UPLOAD_RESPONSE" | grep -q '"success":true'; then
    DOC_ID=$(echo "$UPLOAD_RESPONSE" | grep -o '"id":[0-9]*' | grep -o '[0-9]*' | head -1)
    echo -e "${GREEN}✓ 文档上传成功！${NC}"
    echo "  文档ID: $DOC_ID"
    echo "  响应: $(echo "$UPLOAD_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$UPLOAD_RESPONSE")"
else
    echo "❌ 上传失败"
    echo "$UPLOAD_RESPONSE"
    exit 1
fi
echo ""

sleep 1

echo -e "${BLUE}=== 演示2: 文档列表 ===${NC}"
echo "获取所有文档..."
curl -s "$API_URL/api/v1/documents" | python3 -m json.tool 2>/dev/null || curl -s "$API_URL/api/v1/documents"
echo ""
echo ""

sleep 1

echo -e "${BLUE}=== 演示3: PyMuPDF加载 ===${NC}"
echo "使用PyMuPDF加载文档..."
LOAD_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/processing/load" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\": $DOC_ID, \"loader_type\": \"pymupdf\"}")

if echo "$LOAD_RESPONSE" | grep -q '"success":true'; then
    LOAD_RESULT_ID=$(echo "$LOAD_RESPONSE" | grep -o '"id":[0-9]*' | grep -o '[0-9]*' | head -1)
    echo -e "${GREEN}✓ 文档加载成功！${NC}"
    echo "  结果ID: $LOAD_RESULT_ID"
    echo "  响应: $(echo "$LOAD_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$LOAD_RESPONSE")"
else
    echo "❌ 加载失败"
    echo "$LOAD_RESPONSE"
    exit 1
fi
echo ""

sleep 1

echo -e "${BLUE}=== 演示4: 全文解析 ===${NC}"
echo "解析文档为全文..."
PARSE_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/processing/parse" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\": $DOC_ID, \"parse_mode\": \"full_text\", \"include_tables\": false}")

if echo "$PARSE_RESPONSE" | grep -q '"success":true'; then
    PARSE_RESULT_ID=$(echo "$PARSE_RESPONSE" | grep -o '"id":[0-9]*' | grep -o '[0-9]*' | head -1)
    echo -e "${GREEN}✓ 文档解析成功！${NC}"
    echo "  结果ID: $PARSE_RESULT_ID"
    echo "  响应: $(echo "$PARSE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$PARSE_RESPONSE")"
else
    echo "❌ 解析失败"
    echo "$PARSE_RESPONSE"
    exit 1
fi
echo ""

sleep 1

echo -e "${BLUE}=== 演示5: 查看处理结果 ===${NC}"
echo "获取文档的所有处理结果..."
RESULTS_RESPONSE=$(curl -s "$API_URL/api/v1/processing/results/$DOC_ID")
echo "$RESULTS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESULTS_RESPONSE"
echo ""

sleep 1

echo -e "${BLUE}=== 演示6: 查看解析结果详情 ===${NC}"
echo "获取解析结果的详细内容..."
DETAIL_RESPONSE=$(curl -s "$API_URL/api/v1/processing/results/detail/$PARSE_RESULT_ID")
echo "$DETAIL_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$DETAIL_RESPONSE"
echo ""

# 提示查看前端
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✓ 演示完成！${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "📝 已演示功能:"
echo "  1. ✅ 文档上传"
echo "  2. ✅ 文档列表查询"
echo "  3. ✅ PyMuPDF加载"
echo "  4. ✅ 全文解析"
echo "  5. ✅ 处理结果查询"
echo "  6. ✅ 结果详情查看"
echo ""
echo "🌐 查看完整功能:"
echo "  - API文档: http://localhost:8000/docs"
echo "  - 前端界面: http://localhost:5173 (需先启动前端)"
echo ""
echo "🧹 清理测试数据:"
echo "  curl -X DELETE $API_URL/api/v1/documents/$DOC_ID"
echo ""
echo "📖 详细文档:"
echo "  - TEST_US1.md - 测试指南"
echo "  - QUICKSTART_US1.md - 快速启动"
echo "  - US1_COMPLETION_SUMMARY.md - 完成总结"
echo ""
