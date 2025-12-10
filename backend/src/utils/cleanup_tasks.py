"""Utility script to clean up chunking tasks."""
from sqlalchemy.orm import Session
from ..models.chunking_task import ChunkingTask, TaskStatus
from ..models.chunking_result import ChunkingResult, ResultStatus
from ..storage.database import get_db
import json


def cleanup_duplicate_tasks(db: Session, dry_run: bool = True) -> dict:
    """
    Clean up duplicate chunking tasks for the same document + strategy combination.
    Keeps only the most recent successful task.
    
    Args:
        db: Database session
        dry_run: If True, only report what would be deleted without actually deleting
        
    Returns:
        Dictionary with cleanup statistics
    """
    stats = {
        "duplicates_found": 0,
        "tasks_to_delete": 0,
        "tasks_deleted": 0
    }
    
    # Find all document + strategy combinations with multiple completed tasks
    from sqlalchemy import func
    
    duplicates = db.query(
        ChunkingTask.source_document_id,
        ChunkingTask.chunking_strategy,
        ChunkingTask.chunking_params,
        func.count(ChunkingTask.task_id).label('count')
    ).join(
        ChunkingResult,
        ChunkingTask.task_id == ChunkingResult.task_id
    ).filter(
        ChunkingResult.status == ResultStatus.COMPLETED
    ).group_by(
        ChunkingTask.source_document_id,
        ChunkingTask.chunking_strategy,
        ChunkingTask.chunking_params
    ).having(
        func.count(ChunkingTask.task_id) > 1
    ).all()
    
    stats["duplicates_found"] = len(duplicates)
    
    for dup in duplicates:
        doc_id = dup.source_document_id
        strategy = dup.chunking_strategy
        params = dup.chunking_params
        
        # Get all tasks for this combination, ordered by creation date (newest first)
        tasks = db.query(ChunkingTask).join(
            ChunkingResult,
            ChunkingTask.task_id == ChunkingResult.task_id
        ).filter(
            ChunkingTask.source_document_id == doc_id,
            ChunkingTask.chunking_strategy == strategy,
            ChunkingTask.chunking_params == params,
            ChunkingResult.status == ResultStatus.COMPLETED
        ).order_by(
            ChunkingTask.created_at.desc()
        ).all()
        
        # Keep the first (newest), mark others for deletion
        tasks_to_delete = tasks[1:]
        stats["tasks_to_delete"] += len(tasks_to_delete)
        
        if not dry_run:
            for task in tasks_to_delete:
                # Delete associated result first (cascade should handle this, but be explicit)
                result = db.query(ChunkingResult).filter(
                    ChunkingResult.task_id == task.task_id
                ).first()
                if result:
                    db.delete(result)
                db.delete(task)
                stats["tasks_deleted"] += 1
    
    if not dry_run:
        db.commit()
    
    return stats


def cleanup_failed_tasks(db: Session, dry_run: bool = True) -> dict:
    """
    Clean up failed chunking tasks that have no successful result.
    
    Args:
        db: Database session
        dry_run: If True, only report what would be deleted without actually deleting
        
    Returns:
        Dictionary with cleanup statistics
    """
    stats = {
        "failed_tasks_found": 0,
        "tasks_deleted": 0
    }
    
    # Find all failed tasks
    failed_tasks = db.query(ChunkingTask).filter(
        ChunkingTask.status == TaskStatus.FAILED
    ).all()
    
    stats["failed_tasks_found"] = len(failed_tasks)
    
    if not dry_run:
        for task in failed_tasks:
            db.delete(task)
            stats["tasks_deleted"] += 1
        db.commit()
    
    return stats


def cleanup_all(db: Session, dry_run: bool = True) -> dict:
    """
    Run all cleanup operations.
    
    Args:
        db: Database session
        dry_run: If True, only report what would be deleted without actually deleting
        
    Returns:
        Dictionary with all cleanup statistics
    """
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Starting cleanup operations...\n")
    
    # Cleanup duplicates
    print("1. Cleaning up duplicate tasks...")
    dup_stats = cleanup_duplicate_tasks(db, dry_run)
    print(f"   - Found {dup_stats['duplicates_found']} duplicate document+strategy combinations")
    print(f"   - Tasks to delete: {dup_stats['tasks_to_delete']}")
    if not dry_run:
        print(f"   - Tasks deleted: {dup_stats['tasks_deleted']}")
    
    # Cleanup failed tasks
    print("\n2. Cleaning up failed tasks...")
    failed_stats = cleanup_failed_tasks(db, dry_run)
    print(f"   - Found {failed_stats['failed_tasks_found']} failed tasks")
    if not dry_run:
        print(f"   - Tasks deleted: {failed_stats['tasks_deleted']}")
    
    total_stats = {
        "duplicate_cleanup": dup_stats,
        "failed_cleanup": failed_stats,
        "total_tasks_deleted": dup_stats.get("tasks_deleted", 0) + failed_stats.get("tasks_deleted", 0)
    }
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Cleanup completed!")
    if not dry_run:
        print(f"Total tasks deleted: {total_stats['total_tasks_deleted']}")
    
    return total_stats


if __name__ == "__main__":
    import sys
    from ..storage.database import SessionLocal
    
    # Parse command line arguments
    dry_run = "--execute" not in sys.argv
    
    if dry_run:
        print("\n" + "="*60)
        print("DRY RUN MODE - No data will be deleted")
        print("Use --execute flag to actually delete data")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("EXECUTE MODE - Data will be deleted!")
        print("="*60)
        confirm = input("\nAre you sure you want to delete data? (yes/no): ")
        if confirm.lower() != "yes":
            print("Cleanup cancelled.")
            sys.exit(0)
    
    # Run cleanup
    db = SessionLocal()
    try:
        stats = cleanup_all(db, dry_run)
        print("\nCleanup statistics:")
        print(json.dumps(stats, indent=2))
    finally:
        db.close()
