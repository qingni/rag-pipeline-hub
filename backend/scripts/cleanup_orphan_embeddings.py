#!/usr/bin/env python3
"""
清理孤立的向量化记录脚本

功能：
1. 查找 document_id 对应的文档不存在的向量化记录（"未知文档"）
2. 支持预览模式（dry-run）和删除模式
3. 可选择是否删除对应的 JSON 文件

使用方法：
    # 预览模式（只显示要删除的记录，不实际删除）
    python scripts/cleanup_orphan_embeddings.py --preview
    
    # 删除数据库记录（保留JSON文件）
    python scripts/cleanup_orphan_embeddings.py --delete
    
    # 删除数据库记录和JSON文件
    python scripts/cleanup_orphan_embeddings.py --delete --remove-files
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 将backend目录添加到Python路径
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from src.storage.database import SessionLocal, engine


def get_orphan_embeddings(session) -> list:
    """
    获取孤立的向量化记录（document_id 对应的文档不存在）
    """
    query = text("""
        SELECT 
            e.result_id,
            e.document_id,
            e.model,
            e.successful_count,
            e.failed_count,
            e.status,
            e.json_file_path,
            e.created_at
        FROM embedding_results e
        LEFT JOIN documents d ON e.document_id = d.id
        WHERE d.id IS NULL
        ORDER BY e.created_at DESC
    """)
    
    result = session.execute(query)
    return result.fetchall()


def delete_embedding_record(session, result_id: str) -> bool:
    """
    删除单条向量化记录
    """
    query = text("DELETE FROM embedding_results WHERE result_id = :result_id")
    result = session.execute(query, {"result_id": result_id})
    return result.rowcount > 0


def delete_json_file(json_file_path: str, results_dir: Path) -> bool:
    """
    删除对应的JSON文件
    """
    if not json_file_path:
        return False
    
    full_path = results_dir / json_file_path
    if full_path.exists():
        try:
            full_path.unlink()
            return True
        except Exception as e:
            print(f"  ⚠️  删除文件失败: {e}")
            return False
    return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="清理孤立的向量化记录")
    parser.add_argument(
        "--preview", 
        action="store_true", 
        help="预览模式：只显示要删除的记录，不实际删除"
    )
    parser.add_argument(
        "--delete", 
        action="store_true", 
        help="删除模式：删除数据库记录"
    )
    parser.add_argument(
        "--remove-files", 
        action="store_true", 
        help="同时删除对应的JSON文件"
    )
    
    args = parser.parse_args()
    
    # 如果没有指定任何操作，默认预览模式
    if not args.preview and not args.delete:
        args.preview = True
    
    # results目录路径
    results_dir = backend_dir / "results"
    
    print("=" * 60)
    print("🔍 清理孤立的向量化记录（未知文档）")
    print("=" * 60)
    
    session = SessionLocal()
    
    try:
        # 获取孤立记录
        orphans = get_orphan_embeddings(session)
        
        if not orphans:
            print("\n✅ 没有找到孤立的向量化记录，数据库很干净！")
            return
        
        print(f"\n📋 找到 {len(orphans)} 条孤立的向量化记录：\n")
        
        # 显示记录详情
        for i, record in enumerate(orphans, 1):
            result_id, document_id, model, successful_count, failed_count, status, json_file_path, created_at = record
            
            # 检查JSON文件是否存在
            json_exists = False
            if json_file_path:
                full_path = results_dir / json_file_path
                json_exists = full_path.exists()
            
            print(f"  [{i}] 记录ID: {result_id[:20]}...")
            print(f"      文档ID: {document_id}")
            print(f"      模型: {model}")
            print(f"      向量数量: {successful_count}")
            print(f"      状态: {status}")
            print(f"      创建时间: {created_at}")
            print(f"      JSON文件: {json_file_path or '无'}")
            print(f"      文件存在: {'是' if json_exists else '否'}")
            print()
        
        if args.preview:
            print("-" * 60)
            print("📝 预览模式 - 未进行任何删除操作")
            print("\n使用以下命令执行删除：")
            print("  python scripts/cleanup_orphan_embeddings.py --delete")
            print("  python scripts/cleanup_orphan_embeddings.py --delete --remove-files")
            return
        
        if args.delete:
            print("-" * 60)
            confirm = input(f"\n⚠️  确认删除 {len(orphans)} 条记录？(yes/no): ")
            
            if confirm.lower() != "yes":
                print("❌ 操作已取消")
                return
            
            deleted_db = 0
            deleted_files = 0
            
            for record in orphans:
                result_id, document_id, model, successful_count, failed_count, status, json_file_path, created_at = record
                
                # 删除数据库记录
                if delete_embedding_record(session, result_id):
                    deleted_db += 1
                    print(f"  ✅ 已删除数据库记录: {result_id[:20]}...")
                    
                    # 如果指定了删除文件
                    if args.remove_files and json_file_path:
                        if delete_json_file(json_file_path, results_dir):
                            deleted_files += 1
                            print(f"     📁 已删除文件: {json_file_path}")
                else:
                    print(f"  ❌ 删除失败: {result_id[:20]}...")
            
            # 提交事务
            session.commit()
            
            print("\n" + "=" * 60)
            print(f"🎉 清理完成！")
            print(f"   删除数据库记录: {deleted_db} 条")
            if args.remove_files:
                print(f"   删除JSON文件: {deleted_files} 个")
            print("=" * 60)
            
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
