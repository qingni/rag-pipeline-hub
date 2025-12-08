"""Fix semantic strategy default parameters in database."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.storage.database import SessionLocal
from src.models.chunking_strategy import ChunkingStrategy
from src.models.chunking_task import StrategyType


def fix_semantic_strategy():
    """Update semantic strategy default parameters."""
    
    print("=" * 60)
    print("Fixing Semantic Strategy Parameters")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Find semantic strategy
        strategy = db.query(ChunkingStrategy).filter(
            ChunkingStrategy.strategy_type == StrategyType.SEMANTIC
        ).first()
        
        if not strategy:
            print("❌ Semantic strategy not found in database")
            print("   Run: python src/utils/init_strategies.py")
            return False
        
        print(f"\n✓ Found semantic strategy: {strategy.strategy_name}")
        print(f"  Current parameters: {strategy.default_params}")
        
        # Update parameters
        old_threshold = strategy.default_params.get('similarity_threshold', 0.6)
        new_params = {
            "similarity_threshold": 0.3,
            "min_chunk_size": 300,
            "max_chunk_size": 1200
        }
        
        strategy.default_params = new_params
        db.commit()
        
        print(f"\n✅ Updated parameters:")
        print(f"   similarity_threshold: {old_threshold} → 0.3")
        print(f"   min_chunk_size: 300")
        print(f"   max_chunk_size: 1200")
        
        print("\n" + "=" * 60)
        print("✅ Fix completed successfully!")
        print("=" * 60)
        print("\nChanges:")
        print("  • Lowered similarity_threshold from 0.6 to 0.3")
        print("    (More aggressive chunking, prevents single-chunk results)")
        print("\nNext steps:")
        print("  1. Restart your backend service")
        print("  2. Re-chunk documents with semantic strategy")
        print("  3. Verify multiple chunks are generated")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = fix_semantic_strategy()
    sys.exit(0 if success else 1)
