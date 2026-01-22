"""ChunkingRecommendation data class for strategy recommendation."""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from .chunking_task import StrategyType


@dataclass
class ChunkingRecommendation:
    """Recommendation for a chunking strategy.
    
    This class represents a single strategy recommendation with
    its rationale and suggested parameters.
    """
    
    # Strategy information
    strategy: StrategyType
    strategy_name: str
    
    # Recommendation details
    reason: str  # Human-readable explanation
    confidence: float  # 0.0 to 1.0
    
    # Estimation
    estimated_chunks: int = 0
    estimated_avg_chunk_size: int = 0
    
    # Ranking
    is_top: bool = False  # Whether this is the top recommendation
    rank: int = 0  # Position in recommendation list
    
    # Suggested parameters
    suggested_params: Dict[str, Any] = field(default_factory=dict)
    
    # Additional context
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "strategy": self.strategy.value,
            "strategy_name": self.strategy_name,
            "reason": self.reason,
            "confidence": self.confidence,
            "estimated_chunks": self.estimated_chunks,
            "estimated_avg_chunk_size": self.estimated_avg_chunk_size,
            "is_top": self.is_top,
            "rank": self.rank,
            "suggested_params": self.suggested_params,
            "pros": self.pros,
            "cons": self.cons
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChunkingRecommendation":
        """Create from dictionary."""
        strategy = data.get("strategy")
        if isinstance(strategy, str):
            strategy = StrategyType(strategy)
        return cls(
            strategy=strategy,
            strategy_name=data.get("strategy_name", ""),
            reason=data.get("reason", ""),
            confidence=data.get("confidence", 0.0),
            estimated_chunks=data.get("estimated_chunks", 0),
            estimated_avg_chunk_size=data.get("estimated_avg_chunk_size", 0),
            is_top=data.get("is_top", False),
            rank=data.get("rank", 0),
            suggested_params=data.get("suggested_params", {}),
            pros=data.get("pros", []),
            cons=data.get("cons", [])
        )


@dataclass 
class RecommendationResult:
    """Complete recommendation result including features and recommendations."""
    
    document_id: str
    features: Dict[str, Any]  # DocumentFeatures as dict
    recommendations: List[ChunkingRecommendation] = field(default_factory=list)
    analysis_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "document_id": self.document_id,
            "features": self.features,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "analysis_time_ms": self.analysis_time_ms
        }
    
    def get_top_recommendation(self) -> Optional[ChunkingRecommendation]:
        """Get the top recommendation."""
        for rec in self.recommendations:
            if rec.is_top:
                return rec
        return self.recommendations[0] if self.recommendations else None


# Strategy display names mapping
STRATEGY_DISPLAY_NAMES = {
    StrategyType.CHARACTER: "按字数分块",
    StrategyType.PARAGRAPH: "按段落分块",
    StrategyType.HEADING: "按标题分块",
    StrategyType.SEMANTIC: "语义分块",
    StrategyType.PARENT_CHILD: "父子文档分块",
    StrategyType.HYBRID: "混合分块策略",
    StrategyType.MULTIMODAL: "多模态分块"
}


def get_strategy_display_name(strategy: StrategyType) -> str:
    """Get display name for a strategy type."""
    return STRATEGY_DISPLAY_NAMES.get(strategy, strategy.value)
