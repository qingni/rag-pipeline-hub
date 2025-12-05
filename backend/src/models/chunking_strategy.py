"""ChunkingStrategy model."""
from sqlalchemy import Column, String, Boolean, JSON, Enum as SQLEnum
from .chunking_task import StrategyType
from ..storage.database import Base


class ChunkingStrategy(Base):
    """ChunkingStrategy entity defining available chunking strategies."""
    
    __tablename__ = "chunking_strategies"
    
    # Primary key
    strategy_id = Column(String(50), primary_key=True)
    
    # Strategy metadata
    strategy_name = Column(String(50), nullable=False)
    strategy_type = Column(SQLEnum(StrategyType), nullable=False)
    description = Column(String(500), nullable=False)
    
    # Configuration
    default_params = Column(JSON, nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True)
    requires_structure = Column(Boolean, nullable=False, default=False)
    
    def __repr__(self):
        return f"<ChunkingStrategy(strategy_id={self.strategy_id}, type={self.strategy_type.value}, enabled={self.is_enabled})>"
