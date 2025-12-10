"""
Database migration script to add version management fields to chunking_results table.

Usage:
    python migrations/add_version_management.py

This script adds the following columns:
- version: Version number (default 1)
- previous_version_id: Link to previous version
- is_active: Whether this version is active (default True)
- replacement_reason: Reason for replacing previous version
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text, inspect
from src.storage.database import engine, SessionLocal


def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def add_version_management_columns():
    """Add version management columns to chunking_results table."""
    
    print("=" * 60)
    print("Starting database migration: Add version management")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Check if table exists
        inspector = inspect(engine)
        if 'chunking_results' not in inspector.get_table_names():
            print("❌ Error: chunking_results table does not exist")
            return False
        
        print("✓ Found chunking_results table")
        
        # Add version column
        if not check_column_exists('chunking_results', 'version'):
            print("Adding 'version' column...")
            conn.execute(text("""
                ALTER TABLE chunking_results 
                ADD COLUMN version INTEGER DEFAULT 1 NOT NULL
            """))
            conn.commit()
            print("✓ Added 'version' column")
        else:
            print("⚠ Column 'version' already exists, skipping")
        
        # Add previous_version_id column
        if not check_column_exists('chunking_results', 'previous_version_id'):
            print("Adding 'previous_version_id' column...")
            conn.execute(text("""
                ALTER TABLE chunking_results 
                ADD COLUMN previous_version_id VARCHAR(36)
            """))
            conn.commit()
            print("✓ Added 'previous_version_id' column")
        else:
            print("⚠ Column 'previous_version_id' already exists, skipping")
        
        # Add is_active column
        if not check_column_exists('chunking_results', 'is_active'):
            print("Adding 'is_active' column...")
            conn.execute(text("""
                ALTER TABLE chunking_results 
                ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL
            """))
            conn.commit()
            print("✓ Added 'is_active' column")
        else:
            print("⚠ Column 'is_active' already exists, skipping")
        
        # Add replacement_reason column
        if not check_column_exists('chunking_results', 'replacement_reason'):
            print("Adding 'replacement_reason' column...")
            conn.execute(text("""
                ALTER TABLE chunking_results 
                ADD COLUMN replacement_reason VARCHAR(200)
            """))
            conn.commit()
            print("✓ Added 'replacement_reason' column")
        else:
            print("⚠ Column 'replacement_reason' already exists, skipping")
        
        # Create index on is_active
        print("Creating index on (document_id, chunking_strategy, is_active)...")
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_doc_strategy_active 
                ON chunking_results(document_id, chunking_strategy, is_active)
            """))
            conn.commit()
            print("✓ Created index idx_doc_strategy_active")
        except Exception as e:
            print(f"⚠ Index creation warning (may already exist): {e}")
        
        # Update existing records
        print("\nUpdating existing records...")
        result = conn.execute(text("""
            UPDATE chunking_results 
            SET version = 1, is_active = TRUE 
            WHERE version IS NULL OR is_active IS NULL
        """))
        conn.commit()
        print(f"✓ Updated {result.rowcount} existing records")
    
    print("\n" + "=" * 60)
    print("✅ Migration completed successfully!")
    print("=" * 60)
    print("\nNew columns added:")
    print("  • version (INTEGER, default: 1)")
    print("  • previous_version_id (VARCHAR(36), nullable)")
    print("  • is_active (BOOLEAN, default: True)")
    print("  • replacement_reason (VARCHAR(200), nullable)")
    print("\nNew index created:")
    print("  • idx_doc_strategy_active (document_id, chunking_strategy, is_active)")
    
    return True


def verify_migration():
    """Verify that migration was successful."""
    print("\n" + "=" * 60)
    print("Verifying migration...")
    print("=" * 60)
    
    inspector = inspect(engine)
    columns = {col['name']: col for col in inspector.get_columns('chunking_results')}
    
    required_columns = ['version', 'previous_version_id', 'is_active', 'replacement_reason']
    all_present = True
    
    for col_name in required_columns:
        if col_name in columns:
            col_info = columns[col_name]
            print(f"✓ {col_name}: {col_info['type']}")
        else:
            print(f"❌ {col_name}: NOT FOUND")
            all_present = False
    
    # Check indexes
    indexes = inspector.get_indexes('chunking_results')
    index_names = [idx['name'] for idx in indexes]
    
    if 'idx_doc_strategy_active' in index_names:
        print("✓ Index idx_doc_strategy_active: EXISTS")
    else:
        print("⚠ Index idx_doc_strategy_active: NOT FOUND (may not be critical)")
    
    print("=" * 60)
    
    return all_present


if __name__ == "__main__":
    try:
        success = add_version_management_columns()
        if success:
            verify_migration()
            print("\n✅ All done! Your database is ready for version management.")
        else:
            print("\n❌ Migration failed. Please check the errors above.")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
