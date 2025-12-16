#!/bin/bash
# 测试所有嵌入模型的实际维度

echo "🧪 测试嵌入模型实际维度..."
echo ""

models=("bge-m3" "qwen3-embedding-8b" "hunyuan-embedding" "jina-embeddings-v4")

for model in "${models[@]}"; do
    echo "测试模型: $model"
    response=$(curl -s -X POST http://localhost:8000/api/v1/embedding/single \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"测试文本\", \"model\": \"$model\"}")
    
    dimension=$(echo "$response" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    if 'vector' in d and 'vector' in d['vector']:
        print(len(d['vector']['vector']))
    else:
        print('ERROR')
except:
    print('ERROR')
" 2>/dev/null)
    
    if [ "$dimension" == "ERROR" ]; then
        echo "  ❌ 错误: 模型不可用或返回无效数据"
        echo "$response" | python3 -m json.tool 2>/dev/null | head -10
    else
        echo "  ✅ 维度: $dimension"
    fi
    echo ""
done

echo "✅ 测试完成"
