"""
ModelRecommendation models for intelligent model selection.

Implements:
- Recommendation result data structures
- Confidence scoring
- Batch recommendation with outlier detection
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from enum import Enum


class RecommendationConfidence(str, Enum):
    """Confidence level of a recommendation."""
    HIGH = "high"       # 置信度 > 0.8
    MEDIUM = "medium"   # 置信度 0.5-0.8
    LOW = "low"         # 置信度 < 0.5


@dataclass
class DimensionScore:
    """Score for a single dimension of model capability."""
    dimension: str
    score: float
    weight: float
    weighted_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ModelScore:
    """Detailed scoring for a model recommendation."""
    model_name: str
    display_name: str
    total_score: float
    dimension_scores: List[DimensionScore] = field(default_factory=list)
    
    # Individual dimension scores for radar chart
    language_score: float = 0.0
    domain_score: float = 0.0
    multimodal_score: float = 0.0
    
    # Model metadata
    model_type: str = "text"
    dimension: int = 1024
    provider: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_name": self.model_name,
            "display_name": self.display_name,
            "total_score": self.total_score,
            "dimension_scores": [d.to_dict() for d in self.dimension_scores],
            "language_score": self.language_score,
            "domain_score": self.domain_score,
            "multimodal_score": self.multimodal_score,
            "model_type": self.model_type,
            "dimension": self.dimension,
            "provider": self.provider,
        }


@dataclass
class RecommendationReason:
    """Explanation for why a model was recommended."""
    key: str
    description: str
    impact: str  # positive, negative, neutral
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ModelRecommendation:
    """Single model recommendation result."""
    rank: int
    model: ModelScore
    confidence: RecommendationConfidence
    reasons: List[RecommendationReason] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rank": self.rank,
            "model": self.model.to_dict(),
            "confidence": self.confidence.value,
            "reasons": [r.to_dict() for r in self.reasons],
        }


@dataclass
class DocumentAnalysis:
    """Analysis result for a single document."""
    document_id: str
    document_name: str
    
    # Detected features
    primary_language: str
    language_confidence: float
    detected_domain: str
    domain_confidence: float
    multimodal_ratio: float  # 0.0 - 1.0
    
    # Content statistics
    total_chunks: int = 0
    text_chunks: int = 0
    image_chunks: int = 0
    table_chunks: int = 0
    code_chunks: int = 0
    
    # Feature vector for comparison
    feature_vector: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document_id": self.document_id,
            "document_name": self.document_name,
            "primary_language": self.primary_language,
            "language_confidence": self.language_confidence,
            "detected_domain": self.detected_domain,
            "domain_confidence": self.domain_confidence,
            "multimodal_ratio": self.multimodal_ratio,
            "total_chunks": self.total_chunks,
            "text_chunks": self.text_chunks,
            "image_chunks": self.image_chunks,
            "table_chunks": self.table_chunks,
            "code_chunks": self.code_chunks,
        }


@dataclass
class SingleRecommendationResult:
    """Result for single document recommendation."""
    document_analysis: DocumentAnalysis
    recommendations: List[ModelRecommendation]
    top_recommendation: Optional[ModelRecommendation] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document_analysis": self.document_analysis.to_dict(),
            "recommendations": [r.to_dict() for r in self.recommendations],
            "top_recommendation": self.top_recommendation.to_dict() if self.top_recommendation else None,
        }


@dataclass
class OutlierDocument:
    """Document flagged as outlier in batch recommendation."""
    document_id: str
    document_name: str
    deviation_score: float  # 偏离度分数
    deviation_reason: str
    suggested_action: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class BatchFeatureSummary:
    """Summary of features across all documents in batch."""
    document_count: int
    
    # Language distribution
    language_distribution: Dict[str, int] = field(default_factory=dict)
    primary_language: str = "zh"
    language_uniformity: float = 0.0  # 0-1, 越高越统一
    
    # Domain distribution
    domain_distribution: Dict[str, int] = field(default_factory=dict)
    primary_domain: str = "general"
    domain_uniformity: float = 0.0
    
    # Multimodal statistics
    avg_multimodal_ratio: float = 0.0
    total_chunks: int = 0
    total_image_chunks: int = 0
    total_table_chunks: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document_count": self.document_count,
            "language_distribution": self.language_distribution,
            "primary_language": self.primary_language,
            "language_uniformity": self.language_uniformity,
            "domain_distribution": self.domain_distribution,
            "primary_domain": self.primary_domain,
            "domain_uniformity": self.domain_uniformity,
            "avg_multimodal_ratio": self.avg_multimodal_ratio,
            "total_chunks": self.total_chunks,
            "total_image_chunks": self.total_image_chunks,
            "total_table_chunks": self.total_table_chunks,
        }


@dataclass
class BatchRecommendationResult:
    """Result for batch document recommendation."""
    feature_summary: BatchFeatureSummary
    unified_recommendation: List[ModelRecommendation]
    outlier_documents: List[OutlierDocument] = field(default_factory=list)
    document_analyses: List[DocumentAnalysis] = field(default_factory=list)
    outlier_threshold: float = 0.3
    
    @property
    def has_outliers(self) -> bool:
        """Check if there are outlier documents."""
        return len(self.outlier_documents) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "feature_summary": self.feature_summary.to_dict(),
            "unified_recommendation": [r.to_dict() for r in self.unified_recommendation],
            "outlier_documents": [o.to_dict() for o in self.outlier_documents],
            "document_analyses": [d.to_dict() for d in self.document_analyses],
            "has_outliers": self.has_outliers,
            "outlier_threshold": self.outlier_threshold,
        }
