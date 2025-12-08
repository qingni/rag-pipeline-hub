#!/bin/bash

# 清理未使用的 document_chunks 表
# 用途：删除遗留的、未使用的 document_chunks 表和相关代码

set -e  # 遇到错误立即退出

echo "=========================================="
echo "清理 document_chunks 表和相关代码"
echo "=========================================="
echo ""

# 检查是否在正确的目录
if [ ! -f "app.db" ]; then
    echo "❌ 错误：找不到 app.db 文件"
    echo "   请在 backend 目录下运行此脚本"
    exit 1
fi

# 1. 检查表是否存在
echo "1. 检查 document_chunks 表..."
table_exists=$(sqlite3 app.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='document_chunks';")

if [ "$table_exists" -eq 0 ]; then
    echo "   ✅ document_chunks 表不存在"
else
    # 检查表中的数据
    record_count=$(sqlite3 app.db "SELECT COUNT(*) FROM document_chunks;" 2>/dev/null || echo "0")
    echo "   📊 表中记录数：$record_count"
    
    if [ "$record_count" -gt 0 ]; then
        echo "   ⚠️  警告：表中有数据！"
        if [ "$1" != "--force" ]; then
            echo "   请使用 --force 参数强制删除"
            exit 1
        fi
    fi
    
    # 删除表
    echo "   🗑️  删除表..."
    sqlite3 app.db "DROP TABLE IF EXISTS document_chunks;"
    echo "   ✅ 表已删除"
fi
echo ""

# 2. 检查并删除模型文件
echo "2. 检查模型文件..."
if [ -f "src/models/document_chunk.py" ]; then
    echo "   📁 发现文件：src/models/document_chunk.py"
    if [ "$1" == "--dry-run" ]; then
        echo "   [DRY RUN] 将删除此文件"
    else
        rm "src/models/document_chunk.py"
        echo "   ✅ 文件已删除"
    fi
else
    echo "   ✅ 模型文件不存在"
fi
echo ""

# 3. 更新 __init__.py
echo "3. 更新 src/models/__init__.py..."
if grep -q "DocumentChunk" src/models/__init__.py 2>/dev/null; then
    echo "   📝 发现 DocumentChunk 引用"
    if [ "$1" == "--dry-run" ]; then
        echo "   [DRY RUN] 将删除以下行："
        grep "DocumentChunk" src/models/__init__.py
    else
        # 备份原文件
        cp src/models/__init__.py src/models/__init__.py.bak
        # 删除 DocumentChunk 相关行
        sed -i '' '/DocumentChunk/d' src/models/__init__.py
        echo "   ✅ 引用已删除（备份保存为 __init__.py.bak）"
    fi
else
    echo "   ✅ 没有发现 DocumentChunk 引用"
fi
echo ""

# 4. 检查 Document 模型中的关系
echo "4. 检查 Document 模型..."
if grep -q '"DocumentChunk"' src/models/document.py 2>/dev/null; then
    echo "   📝 发现 DocumentChunk 关系定义"
    echo "   ⚠️  需要手动编辑 src/models/document.py"
    echo "   删除以下代码块："
    echo "   ---"
    grep -A 5 '"DocumentChunk"' src/models/document.py || true
    echo "   ---"
else
    echo "   ✅ Document 模型中没有 DocumentChunk 引用"
fi
echo ""

# 5. 验证清理结果
echo "5. 验证清理结果..."
echo "   数据库表检查："
sqlite3 app.db "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%chunk%';"
echo ""

# 6. 总结
echo "=========================================="
echo "清理完成！"
echo "=========================================="
echo ""
echo "✅ 已完成："
if [ "$table_exists" -ne 0 ]; then
    echo "   - 删除数据库表 document_chunks"
fi
if [ -f "src/models/document_chunk.py" ] && [ "$1" != "--dry-run" ]; then
    echo "   - 删除模型文件 document_chunk.py"
fi
echo ""
echo "📋 后续操作（如需要）："
if grep -q '"DocumentChunk"' src/models/document.py 2>/dev/null; then
    echo "   1. 手动编辑 src/models/document.py"
    echo "      删除 chunks = relationship(\"DocumentChunk\", ...) 代码块"
fi
echo "   2. 重启后端服务"
echo "   3. 运行测试验证功能正常"
echo ""
echo "📚 详细分析报告："
echo "   查看 DOCUMENT_CHUNKS_ANALYSIS.md"
