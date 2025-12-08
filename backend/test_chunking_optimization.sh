#!/bin/bash

# 测试脚本：验证文档分块优化效果

echo "=========================================="
echo "文档分块优化测试"
echo "=========================================="
echo ""

# 配置
API_BASE="http://localhost:8000/api/v1"
DOCUMENT_ID="f1a8b9ae-223f-45db-ad14-3c3f5be708e5"  # 需要替换为实际的文档ID

echo "1. 检查当前任务状态"
echo "------------------------------------------"
sqlite3 app.db "SELECT status, COUNT(*) as count FROM chunking_tasks GROUP BY status;"
echo ""

echo "2. 第一次创建分块任务（应该成功创建）"
echo "------------------------------------------"
response1=$(curl -s -X POST "$API_BASE/chunking/chunk" \
  -H "Content-Type: application/json" \
  -d "{
    \"document_id\": \"$DOCUMENT_ID\",
    \"strategy_type\": \"heading\",
    \"parameters\": {\"heading_formats\": [\"markdown\", \"html\"]}
  }")

echo "$response1" | python3 -m json.tool
task_id_1=$(echo "$response1" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['task_id'])" 2>/dev/null)
echo "任务ID: $task_id_1"
echo ""

sleep 3

echo "3. 第二次创建相同的分块任务（应该返回已有结果）"
echo "------------------------------------------"
response2=$(curl -s -X POST "$API_BASE/chunking/chunk" \
  -H "Content-Type: application/json" \
  -d "{
    \"document_id\": \"$DOCUMENT_ID\",
    \"strategy_type\": \"heading\",
    \"parameters\": {\"heading_formats\": [\"markdown\", \"html\"]}
  }")

echo "$response2" | python3 -m json.tool
task_id_2=$(echo "$response2" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['task_id'])" 2>/dev/null)
echo "任务ID: $task_id_2"
echo ""

echo "4. 验证是否返回了相同的任务ID"
echo "------------------------------------------"
if [ "$task_id_1" == "$task_id_2" ]; then
    echo "✅ 测试通过：返回了相同的任务ID（幂等性验证成功）"
else
    echo "❌ 测试失败：返回了不同的任务ID"
fi
echo ""

echo "5. 检查数据库中的任务记录数量"
echo "------------------------------------------"
task_count=$(sqlite3 app.db "SELECT COUNT(*) FROM chunking_tasks WHERE source_document_id='$DOCUMENT_ID' AND chunking_strategy='HEADING';")
echo "任务记录数量: $task_count"
if [ "$task_count" -eq 1 ]; then
    echo "✅ 测试通过：没有创建重复任务"
else
    echo "⚠️  任务记录数量不为1，可能存在重复"
fi
echo ""

echo "6. 测试失败任务不入库（使用错误参数）"
echo "------------------------------------------"
failed_count_before=$(sqlite3 app.db "SELECT COUNT(*) FROM chunking_tasks WHERE status='FAILED';")
echo "失败任务数（测试前）: $failed_count_before"

# 尝试创建一个会失败的任务
curl -s -X POST "$API_BASE/chunking/chunk" \
  -H "Content-Type: application/json" \
  -d "{
    \"document_id\": \"non-existent-id\",
    \"strategy_type\": \"heading\",
    \"parameters\": {\"heading_formats\": [\"markdown\"]}
  }" > /dev/null 2>&1

sleep 2

failed_count_after=$(sqlite3 app.db "SELECT COUNT(*) FROM chunking_tasks WHERE status='FAILED';")
echo "失败任务数（测试后）: $failed_count_after"

if [ "$failed_count_before" -eq "$failed_count_after" ]; then
    echo "✅ 测试通过：失败任务未入库"
else
    echo "❌ 测试失败：失败任务被保存到数据库"
fi
echo ""

echo "7. 查看所有任务状态统计"
echo "------------------------------------------"
sqlite3 app.db "SELECT status, COUNT(*) as count FROM chunking_tasks GROUP BY status;"
echo ""

echo "=========================================="
echo "测试完成"
echo "=========================================="
