"""Add missing idx_status index to embedding_results table."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import Index, text
from src.storage.database import engine
from src.models.embedding_models import EmbeddingResult

# Create the index using SQLAlchemy
idx = Index('idx_status', EmbeddingResult.status)

print("Adding idx_status index to embedding_results table...")
try:
    idx.create(engine)
    print("✅ Index idx_status created successfully!")
except Exception as e:
    if "already exists" in str(e).lower():
        print("ℹ️  Index idx_status already exists")
    else:
        print(f"❌ Error: {e}")
        raise

# Verify
with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='embedding_results'"
    ))
    indexes = [row[0] for row in result]
    print(f"\nCurrent indexes: {', '.join(indexes)}")
