"""
BM25 词表全量重建脚本

用于修复因增量构建缺失导致的 BM25 词表不完整问题。
本脚本会收集指定 Collection 下所有文档的 source_text，
从零开始全量构建 BM25 统计信息（词表、IDF、avgdl 等）。

使用方法:
    cd backend
    python scripts/rebuild_bm25_stats.py [collection_name]

示例:
    python scripts/rebuild_bm25_stats.py default_kb_qwen3_embedding_8b_dim4096
    python scripts/rebuild_bm25_stats.py  # 不指定则重建所有 Collection
"""
import json
import os
import sys
import glob
from collections import defaultdict

# 确保能导入项目模块
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from src.services.bm25_service import BM25SparseGenerator


def find_embedding_files(results_dir: str) -> list:
    """查找所有 embedding 结果 JSON 文件"""
    pattern = os.path.join(results_dir, "embedding", "**", "*.json")
    return glob.glob(pattern, recursive=True)


def load_source_texts_from_file(filepath: str) -> list:
    """从单个 embedding 结果文件中提取 source_text"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        texts = []
        for vec_item in data.get("vectors", []):
            source_text = vec_item.get("source_text", "")
            if source_text and source_text.strip():
                texts.append(source_text[:500])  # 与入库时一致的截断
        return texts
    except Exception as e:
        print(f"  ⚠️ 读取文件失败 {os.path.basename(filepath)}: {e}")
        return []


def find_bm25_stats_files(stats_dir: str) -> dict:
    """查找所有已有的 BM25 统计文件，返回 {index_id: filepath}"""
    result = {}
    if not os.path.exists(stats_dir):
        return result
    for f in os.listdir(stats_dir):
        if f.endswith("_bm25_stats.json"):
            index_id = f.replace("_bm25_stats.json", "")
            result[index_id] = os.path.join(stats_dir, f)
    return result


def load_index_to_embedding_mapping(db_path: str) -> dict:
    """
    从 SQLite 数据库加载索引 → embedding_result_id 的映射
    返回 {provider_index_id: [embedding_result_id_1, ...]}
    """
    import sqlite3
    mapping = defaultdict(list)
    
    if not os.path.exists(db_path):
        print(f"  ⚠️ 数据库文件不存在: {db_path}")
        return mapping
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 查询所有已就绪的索引及其关联的 embedding_result_id
        cursor.execute("""
            SELECT vi.provider_index_id, vi.embedding_result_id 
            FROM vector_indexes vi
            WHERE vi.status = 'READY' 
            AND vi.provider_index_id IS NOT NULL
        """)
        
        for row in cursor.fetchall():
            provider_index_id = row[0]
            embedding_result_id = row[1]
            if provider_index_id and embedding_result_id:
                mapping[provider_index_id].append(embedding_result_id)
    except Exception as e:
        print(f"  ⚠️ 数据库查询失败: {e}")
    finally:
        conn.close()
    
    return mapping


def rebuild_stats_for_collection(
    collection_name: str,
    embedding_result_ids: list,
    results_dir: str,
    stats_dir: str
):
    """为单个 Collection 全量重建 BM25 统计信息"""
    print(f"\n{'='*60}")
    print(f"重建 Collection: {collection_name}")
    print(f"关联 Embedding 文件数: {len(embedding_result_ids)}")
    print(f"{'='*60}")
    
    # 收集所有 source_text
    all_texts = []
    for eid in embedding_result_ids:
        pattern = os.path.join(results_dir, "embedding", "**", f"*{eid}*.json")
        files = glob.glob(pattern, recursive=True)
        if files:
            texts = load_source_texts_from_file(files[0])
            all_texts.extend(texts)
            print(f"  ✅ {eid}: {len(texts)} 个 chunks")
        else:
            print(f"  ⚠️ {eid}: 未找到对应的 embedding 文件")
    
    if not all_texts:
        print(f"  ❌ 没有可用的文本数据，跳过重建")
        return
    
    print(f"\n  总计: {len(all_texts)} 个 chunks")
    
    # 全量构建 BM25 统计
    generator = BM25SparseGenerator()
    generator.fit(all_texts)
    
    # 保存
    stats_path = os.path.join(stats_dir, f"{collection_name}_bm25_stats.json")
    generator.save_stats(stats_path)
    
    print(f"\n  📊 重建结果:")
    print(f"     文档数: {generator.doc_count}")
    print(f"     词表大小: {len(generator.vocab)}")
    print(f"     平均文档长度: {generator.avgdl:.1f} tokens")
    print(f"     统计文件: {stats_path}")
    
    # 输出词表前 30 个词（按字母排序）
    vocab_preview = sorted(generator.vocab.keys())[:30]
    print(f"     词表预览 (前30): {vocab_preview}")


def main():
    results_dir = os.path.join(backend_dir, "results")
    stats_dir = os.path.join(results_dir, "bm25_stats")
    db_path = os.path.join(backend_dir, "app.db")
    
    # 检查目标 Collection
    target_collection = sys.argv[1] if len(sys.argv) > 1 else None
    
    print("=" * 60)
    print("BM25 词表全量重建工具")
    print("=" * 60)
    print(f"结果目录: {results_dir}")
    print(f"统计目录: {stats_dir}")
    print(f"数据库: {db_path}")
    if target_collection:
        print(f"目标 Collection: {target_collection}")
    else:
        print("目标: 所有 Collection")
    
    # 从数据库加载映射
    mapping = load_index_to_embedding_mapping(db_path)
    
    if not mapping:
        print("\n⚠️ 未找到任何索引映射，请确认数据库路径正确")
        return
    
    print(f"\n发现 {len(mapping)} 个 Collection:")
    for coll, eids in mapping.items():
        print(f"  - {coll}: {len(eids)} 个文档")
    
    # 过滤目标
    if target_collection:
        if target_collection in mapping:
            collections_to_rebuild = {target_collection: mapping[target_collection]}
        else:
            print(f"\n❌ 未找到 Collection: {target_collection}")
            print(f"可用的 Collection: {list(mapping.keys())}")
            return
    else:
        collections_to_rebuild = mapping
    
    # 执行重建
    for coll_name, eids in collections_to_rebuild.items():
        rebuild_stats_for_collection(coll_name, eids, results_dir, stats_dir)
    
    print(f"\n{'='*60}")
    print("✅ BM25 词表重建完成!")
    print("='*60")


if __name__ == "__main__":
    main()
