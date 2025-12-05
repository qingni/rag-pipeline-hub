"""Initialize default chunking strategies in database."""
from sqlalchemy.orm import Session
from ..storage.database import SessionLocal, init_db
from ..models.chunking_strategy import ChunkingStrategy
from ..models.chunking_task import StrategyType


def init_default_strategies(db: Session):
    """Initialize default chunking strategies."""
    
    strategies = [
        {
            "strategy_id": "character",
            "strategy_name": "按字数分块",
            "strategy_type": StrategyType.CHARACTER,
            "description": "按固定字符数切分文档，适合一般文本",
            "default_params": {
                "chunk_size": 500,
                "overlap": 50
            },
            "is_enabled": True,
            "requires_structure": False
        },
        {
            "strategy_id": "paragraph",
            "strategy_name": "按段落分块",
            "strategy_type": StrategyType.PARAGRAPH,
            "description": "以自然段落为基本单位分块，保持语义完整性",
            "default_params": {
                "min_chunk_size": 200,
                "max_chunk_size": 800
            },
            "is_enabled": True,
            "requires_structure": False
        },
        {
            "strategy_id": "heading",
            "strategy_name": "按标题分块",
            "strategy_type": StrategyType.HEADING,
            "description": "按标题层级分块，适合结构化文档",
            "default_params": {
                "min_heading_level": 1,
                "max_heading_level": 3
            },
            "is_enabled": True,
            "requires_structure": True
        },
        {
            "strategy_id": "semantic",
            "strategy_name": "按语义分块",
            "strategy_type": StrategyType.SEMANTIC,
            "description": "使用语义相似度算法识别语义边界进行分块",
            "default_params": {
                "similarity_threshold": 0.6,
                "min_chunk_size": 300,
                "max_chunk_size": 1200
            },
            "is_enabled": True,
            "requires_structure": False
        }
    ]
    
    for strategy_data in strategies:
        # Check if strategy already exists
        existing = db.query(ChunkingStrategy).filter(
            ChunkingStrategy.strategy_id == strategy_data["strategy_id"]
        ).first()
        
        if not existing:
            strategy = ChunkingStrategy(**strategy_data)
            db.add(strategy)
            print(f"Created strategy: {strategy_data['strategy_name']}")
        else:
            print(f"Strategy already exists: {strategy_data['strategy_name']}")
    
    db.commit()
    print("Default strategies initialized successfully")


if __name__ == "__main__":
    # Initialize database tables first
    print("Initializing database tables...")
    init_db()
    
    # Initialize strategies
    print("\nInitializing default strategies...")
    db = SessionLocal()
    try:
        init_default_strategies(db)
    finally:
        db.close()
