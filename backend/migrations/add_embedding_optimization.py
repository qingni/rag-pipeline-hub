"""
Migration: Add embedding optimization fields.

This migration adds new fields and tables for:
- EmbeddingTask: config, progress fields
- EmbeddingResult: is_active field, statistics expansion
- VectorCache: new table for LRU caching

Date: 2026-02-02
Feature: 003-vector-embedding-opt
"""
import sqlite3
import os
from datetime import datetime


def get_db_path():
    """Get the database file path."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(backend_dir, 'app.db')


def run_migration():
    """Execute the migration."""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Skipping migration.")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # ============================================================
        # 1. Extend embedding_results table
        # ============================================================
        print("Checking embedding_results table...")
        
        # Check if is_active column exists
        cursor.execute("PRAGMA table_info(embedding_results)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if 'is_active' not in columns:
            print("Adding is_active column to embedding_results...")
            cursor.execute("""
                ALTER TABLE embedding_results 
                ADD COLUMN is_active BOOLEAN DEFAULT 0
            """)
            print("✓ Added is_active column")
        else:
            print("✓ is_active column already exists")
        
        # Create index for is_active
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_result_is_active'
        """)
        if not cursor.fetchone():
            print("Creating index idx_result_is_active...")
            cursor.execute("""
                CREATE INDEX idx_result_is_active 
                ON embedding_results(is_active)
            """)
            print("✓ Created idx_result_is_active index")
        
        # Create index for document_id + model
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_result_document_model'
        """)
        if not cursor.fetchone():
            print("Creating index idx_result_document_model...")
            cursor.execute("""
                CREATE INDEX idx_result_document_model 
                ON embedding_results(document_id, model)
            """)
            print("✓ Created idx_result_document_model index")
        
        # ============================================================
        # 2. Create vector_cache table
        # ============================================================
        print("\nChecking vector_cache table...")
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='vector_cache'
        """)
        
        if not cursor.fetchone():
            print("Creating vector_cache table...")
            cursor.execute("""
                CREATE TABLE vector_cache (
                    cache_key VARCHAR(100) PRIMARY KEY,
                    content_hash VARCHAR(64) NOT NULL,
                    model VARCHAR(50) NOT NULL,
                    vector BLOB NOT NULL,
                    dimension INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    access_count INTEGER DEFAULT 1
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX idx_cache_model ON vector_cache(model)
            """)
            cursor.execute("""
                CREATE INDEX idx_cache_last_accessed ON vector_cache(last_accessed_at)
            """)
            print("✓ Created vector_cache table with indexes")
        else:
            print("✓ vector_cache table already exists")
        
        # ============================================================
        # 3. Create embedding_tasks table (if not exists)
        # ============================================================
        print("\nChecking embedding_tasks table...")
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='embedding_tasks'
        """)
        
        if not cursor.fetchone():
            print("Creating embedding_tasks table...")
            cursor.execute("""
                CREATE TABLE embedding_tasks (
                    task_id VARCHAR(36) PRIMARY KEY,
                    document_id VARCHAR(36) NOT NULL,
                    chunking_result_id VARCHAR(36) NOT NULL,
                    model VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    config TEXT DEFAULT '{}',
                    progress TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX idx_task_document ON embedding_tasks(document_id)
            """)
            cursor.execute("""
                CREATE INDEX idx_task_status ON embedding_tasks(status)
            """)
            cursor.execute("""
                CREATE INDEX idx_task_created ON embedding_tasks(created_at DESC)
            """)
            print("✓ Created embedding_tasks table with indexes")
        else:
            # Check and add config/progress columns if missing
            cursor.execute("PRAGMA table_info(embedding_tasks)")
            columns = {row[1] for row in cursor.fetchall()}
            
            if 'config' not in columns:
                print("Adding config column to embedding_tasks...")
                cursor.execute("""
                    ALTER TABLE embedding_tasks 
                    ADD COLUMN config TEXT DEFAULT '{}'
                """)
                print("✓ Added config column")
            
            if 'progress' not in columns:
                print("Adding progress column to embedding_tasks...")
                cursor.execute("""
                    ALTER TABLE embedding_tasks 
                    ADD COLUMN progress TEXT
                """)
                print("✓ Added progress column")
            
            if 'updated_at' not in columns:
                print("Adding updated_at column to embedding_tasks...")
                cursor.execute("""
                    ALTER TABLE embedding_tasks 
                    ADD COLUMN updated_at TIMESTAMP
                """)
                print("✓ Added updated_at column")
            
            if 'completed_at' not in columns:
                print("Adding completed_at column to embedding_tasks...")
                cursor.execute("""
                    ALTER TABLE embedding_tasks 
                    ADD COLUMN completed_at TIMESTAMP
                """)
                print("✓ Added completed_at column")
            
            print("✓ embedding_tasks table updated")
        
        # ============================================================
        # 4. Create model_capabilities table (for admin customization)
        # ============================================================
        print("\nChecking model_capabilities table...")
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='model_capabilities'
        """)
        
        if not cursor.fetchone():
            print("Creating model_capabilities table...")
            cursor.execute("""
                CREATE TABLE model_capabilities (
                    model_name VARCHAR(50) PRIMARY KEY,
                    display_name VARCHAR(100) NOT NULL,
                    provider VARCHAR(50) NOT NULL,
                    dimension INTEGER NOT NULL,
                    model_type VARCHAR(20) NOT NULL DEFAULT 'text',
                    language_scores TEXT NOT NULL,
                    domain_scores TEXT NOT NULL,
                    multimodal_score REAL DEFAULT 0.0,
                    performance_scores TEXT,
                    description TEXT,
                    is_enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP
                )
            """)
            print("✓ Created model_capabilities table")
        else:
            print("✓ model_capabilities table already exists")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


def rollback_migration():
    """Rollback the migration (for development/testing)."""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Nothing to rollback.")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Drop tables in reverse order
        tables_to_drop = ['model_capabilities', 'vector_cache']
        
        for table in tables_to_drop:
            cursor.execute(f"""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='{table}'
            """)
            if cursor.fetchone():
                print(f"Dropping table {table}...")
                cursor.execute(f"DROP TABLE {table}")
                print(f"✓ Dropped {table}")
        
        conn.commit()
        print("\n✅ Rollback completed successfully!")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Rollback failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback_migration()
    else:
        run_migration()
