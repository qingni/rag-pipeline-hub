"""
Database migration: Create embedding_results table.

This migration creates the embedding_results table with all required
fields, constraints, and indexes as specified in data-model.md.

Run: python migrations/create_embedding_results_table.py
"""
import sys
import os

# Add parent directory to path to import models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.storage.database import engine, Base
from src.models.embedding_models import EmbeddingResult
from sqlalchemy import inspect


def create_embedding_results_table():
    """Create embedding_results table if it doesn't exist."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if "embedding_results" in existing_tables:
        print("⚠️  Table 'embedding_results' already exists. Skipping creation.")
        print("    To recreate, first drop the table manually.")
        return False
    
    print("Creating 'embedding_results' table...")
    
    # Create only the embedding_results table
    EmbeddingResult.__table__.create(engine, checkfirst=True)
    
    print("✅ Table 'embedding_results' created successfully!")
    print()
    print("Table structure:")
    print("  - result_id (PK): UUID identifier")
    print("  - document_id: Source document reference")
    print("  - chunking_result_id: Chunking result reference (nullable)")
    print("  - model: Embedding model name")
    print("  - status: SUCCESS/FAILED/PARTIAL_SUCCESS")
    print("  - successful_count: Number of successful vectors")
    print("  - failed_count: Number of failed chunks")
    print("  - vector_dimension: Dimension of vectors")
    print("  - json_file_path: Relative path to JSON file")
    print("  - processing_time_ms: Total processing time")
    print("  - created_at: Creation timestamp")
    print("  - error_message: Error details (nullable)")
    print()
    print("Indexes created:")
    print("  - idx_doc_model (document_id, model): For latest-by-document queries")
    print("  - idx_created_at (created_at): For timestamp-based sorting")
    print("  - idx_status (status): For status filtering")
    print()
    print("Constraints:")
    print("  - Check: status IN ('SUCCESS', 'FAILED', 'PARTIAL_SUCCESS')")
    print("  - Check: model IN ('bge-m3', 'qwen3-embedding-8b', 'hunyuan-embedding', 'qwen3-vl-embedding-8b')")
    print("  - Check: successful_count >= 0")
    print("  - Check: failed_count >= 0")
    print("  - Check: vector_dimension > 0")
    
    return True


def verify_table_structure():
    """Verify table was created with correct structure."""
    inspector = inspect(engine)
    
    if "embedding_results" not in inspector.get_table_names():
        print("❌ Verification failed: Table not found")
        return False
    
    columns = {col['name']: col for col in inspector.get_columns('embedding_results')}
    indexes = inspector.get_indexes('embedding_results')
    
    print()
    print("Verification:")
    
    # Check required columns
    required_columns = [
        'result_id', 'document_id', 'chunking_result_id', 'model', 
        'status', 'successful_count', 'failed_count', 'vector_dimension',
        'json_file_path', 'processing_time_ms', 'created_at', 'error_message'
    ]
    
    missing_columns = [col for col in required_columns if col not in columns]
    if missing_columns:
        print(f"  ❌ Missing columns: {', '.join(missing_columns)}")
        return False
    
    print(f"  ✅ All {len(required_columns)} required columns present")
    
    # Check indexes
    index_names = [idx['name'] for idx in indexes]
    required_indexes = ['idx_doc_model', 'idx_created_at', 'idx_status']
    
    missing_indexes = [idx for idx in required_indexes if idx not in index_names]
    if missing_indexes:
        print(f"  ❌ Missing indexes: {', '.join(missing_indexes)}")
        return False
    
    print(f"  ✅ All {len(required_indexes)} required indexes present")
    
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("Embedding Results Table Migration")
    print("=" * 70)
    print()
    
    try:
        created = create_embedding_results_table()
        
        if created:
            # Verify structure
            if verify_table_structure():
                print()
                print("=" * 70)
                print("✅ Migration completed successfully!")
                print("=" * 70)
            else:
                print()
                print("=" * 70)
                print("⚠️  Migration completed with warnings")
                print("=" * 70)
                sys.exit(1)
        else:
            print()
            print("=" * 70)
            print("ℹ️  No changes made")
            print("=" * 70)
            
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ Migration failed: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
