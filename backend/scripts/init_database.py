#!/usr/bin/env python3
"""
Database Initialization Script for Vector Index Module

This script initializes the PostgreSQL database with all necessary tables
for the vector index functionality.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_db_config():
    """Get database configuration from environment"""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "database": os.getenv("DB_NAME", "rag_framework"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "password")
    }


def create_database_if_not_exists(config: dict):
    """Create database if it doesn't exist"""
    # Connect to default postgres database
    conn = psycopg2.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        database="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    cursor = conn.cursor()
    
    # Check if database exists
    cursor.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (config["database"],)
    )
    exists = cursor.fetchone()
    
    if not exists:
        print(f"Creating database '{config['database']}'...")
        cursor.execute(f"CREATE DATABASE {config['database']}")
        print(f"✓ Database '{config['database']}' created successfully")
    else:
        print(f"✓ Database '{config['database']}' already exists")
    
    cursor.close()
    conn.close()


def run_migration_script(config: dict, script_path: Path):
    """Run a SQL migration script"""
    conn = psycopg2.connect(**config)
    cursor = conn.cursor()
    
    try:
        with open(script_path, 'r') as f:
            sql = f.read()
        
        cursor.execute(sql)
        conn.commit()
        print(f"✓ Executed {script_path.name}")
    
    except Exception as e:
        conn.rollback()
        print(f"✗ Error executing {script_path.name}: {e}")
        raise
    
    finally:
        cursor.close()
        conn.close()


def run_all_migrations(config: dict):
    """Run all vector index migration scripts"""
    # Get migrations directory
    migrations_dir = Path(__file__).parent.parent.parent / "migrations" / "vector_index"
    
    if not migrations_dir.exists():
        print(f"Error: Migrations directory not found: {migrations_dir}")
        return False
    
    # Get all SQL files sorted by name
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        print(f"Warning: No migration files found in {migrations_dir}")
        return True
    
    print(f"\nRunning {len(migration_files)} migration(s)...")
    print("=" * 60)
    
    for migration_file in migration_files:
        try:
            run_migration_script(config, migration_file)
        except Exception as e:
            print(f"\n✗ Migration failed: {migration_file.name}")
            print(f"Error: {e}")
            return False
    
    print("=" * 60)
    print(f"✓ All migrations completed successfully\n")
    return True


def verify_tables(config: dict):
    """Verify that all required tables were created"""
    required_tables = [
        "vector_indexes",
        "index_statistics",
        "vector_metadata",
        "query_history"
    ]
    
    conn = psycopg2.connect(**config)
    cursor = conn.cursor()
    
    print("Verifying tables...")
    print("=" * 60)
    
    all_found = True
    for table in required_tables:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, (table,))
        
        exists = cursor.fetchone()[0]
        status = "✓" if exists else "✗"
        print(f"{status} {table}")
        
        if not exists:
            all_found = False
    
    print("=" * 60)
    
    cursor.close()
    conn.close()
    
    return all_found


def main():
    """Main initialization routine"""
    print("\n" + "=" * 60)
    print(" Vector Index Module - Database Initialization")
    print("=" * 60 + "\n")
    
    # Get database configuration
    config = get_db_config()
    print(f"Database: {config['user']}@{config['host']}:{config['port']}/{config['database']}\n")
    
    try:
        # Step 1: Create database
        print("Step 1: Database Creation")
        print("-" * 60)
        create_database_if_not_exists(config)
        
        # Step 2: Run migrations
        print("\nStep 2: Running Migrations")
        print("-" * 60)
        success = run_all_migrations(config)
        
        if not success:
            print("\n✗ Database initialization failed")
            return 1
        
        # Step 3: Verify tables
        print("Step 3: Verification")
        print("-" * 60)
        all_tables_exist = verify_tables(config)
        
        if not all_tables_exist:
            print("\n⚠ Warning: Some tables are missing")
            return 1
        
        # Success
        print("\n" + "=" * 60)
        print(" ✓ Database initialization completed successfully!")
        print("=" * 60 + "\n")
        
        print("Next steps:")
        print("  1. Start Milvus: cd docker/milvus && docker-compose up -d")
        print("  2. Start backend: cd backend && python -m uvicorn main:app --reload")
        print("  3. Test connection: python backend/scripts/test_milvus_connection.py")
        print()
        
        return 0
    
    except psycopg2.Error as e:
        print(f"\n✗ Database error: {e}")
        print("\nTroubleshooting:")
        print("  - Ensure PostgreSQL is running")
        print("  - Check database credentials in .env file")
        print("  - Verify network connectivity")
        return 1
    
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
