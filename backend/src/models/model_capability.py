"""
ModelCapability model for storing model capability configurations.

Implements:
- Model capability scoring (language, domain, multimodal)
- Admin customization support
- Performance metrics
"""
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, Index
from sqlalchemy.sql import func

from ..storage.database import Base


@dataclass
class LanguageScores:
    """Language support scores for a model."""
    zh: float = 0.5    # 中文
    en: float = 0.5    # 英文
    ja: float = 0.3    # 日语
    ko: float = 0.3    # 韩语
    default: float = 0.3  # 其他语言
    
    def get_score(self, language: str) -> float:
        """Get score for a specific language."""
        return getattr(self, language.lower(), self.default)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "LanguageScores":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class DomainScores:
    """Domain expertise scores for a model."""
    general: float = 0.5      # 通用领域
    technical: float = 0.5    # 技术文档
    legal: float = 0.5        # 法律合同
    medical: float = 0.5      # 医疗健康
    financial: float = 0.5    # 金融财经
    academic: float = 0.5     # 学术论文
    news: float = 0.5         # 新闻资讯
    default: float = 0.5      # 其他领域
    
    def get_score(self, domain: str) -> float:
        """Get score for a specific domain."""
        return getattr(self, domain.lower(), self.default)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "DomainScores":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class PerformanceScores:
    """Performance metrics for a model."""
    throughput: float = 0.5   # 吞吐量
    latency: float = 0.5      # 延迟表现
    cost: float = 0.5         # 成本效益
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "PerformanceScores":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ModelCapability(Base):
    """
    Database model for storing model capability configurations.
    
    Allows admin customization of model scores for recommendation.
    """
    
    __tablename__ = "model_capabilities"
    
    # Model identifier (primary key)
    model_name = Column(
        String(50), 
        primary_key=True,
        comment="Model identifier (e.g., bge-m3)"
    )
    
    # Display name
    display_name = Column(
        String(100), 
        nullable=False,
        comment="Human-readable model name"
    )
    
    # Provider
    provider = Column(
        String(50), 
        nullable=False,
        comment="Model provider (e.g., bge, qwen)"
    )
    
    # Technical specs
    dimension = Column(
        Integer, 
        nullable=False,
        comment="Vector dimension"
    )
    model_type = Column(
        String(20), 
        nullable=False,
        default="text",
        comment="Model type: text or multimodal"
    )
    
    # Capability scores (JSON)
    language_scores = Column(
        Text, 
        nullable=False,
        comment="Language support scores (JSON)"
    )
    domain_scores = Column(
        Text, 
        nullable=False,
        comment="Domain expertise scores (JSON)"
    )
    multimodal_score = Column(
        Float, 
        default=0.0,
        comment="Multimodal capability score (0-1)"
    )
    performance_scores = Column(
        Text, 
        nullable=True,
        comment="Performance metrics (JSON)"
    )
    
    # Description
    description = Column(
        Text, 
        nullable=True,
        comment="Model description"
    )
    
    # Enabled flag
    is_enabled = Column(
        Boolean, 
        default=True,
        comment="Whether model is available for recommendation"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    def __repr__(self):
        return (
            f"<ModelCapability("
            f"name={self.model_name}, "
            f"type={self.model_type}, "
            f"enabled={self.is_enabled}"
            f")>"
        )
    
    def get_language_scores(self) -> LanguageScores:
        """Get language scores as LanguageScores object."""
        import json
        try:
            data = json.loads(self.language_scores) if self.language_scores else {}
            return LanguageScores.from_dict(data)
        except (json.JSONDecodeError, TypeError):
            return LanguageScores()
    
    def set_language_scores(self, scores: LanguageScores) -> None:
        """Set language scores from LanguageScores object."""
        import json
        self.language_scores = json.dumps(scores.to_dict())
    
    def get_domain_scores(self) -> DomainScores:
        """Get domain scores as DomainScores object."""
        import json
        try:
            data = json.loads(self.domain_scores) if self.domain_scores else {}
            return DomainScores.from_dict(data)
        except (json.JSONDecodeError, TypeError):
            return DomainScores()
    
    def set_domain_scores(self, scores: DomainScores) -> None:
        """Set domain scores from DomainScores object."""
        import json
        self.domain_scores = json.dumps(scores.to_dict())
    
    def get_performance_scores(self) -> Optional[PerformanceScores]:
        """Get performance scores as PerformanceScores object."""
        import json
        if not self.performance_scores:
            return None
        try:
            data = json.loads(self.performance_scores)
            return PerformanceScores.from_dict(data)
        except (json.JSONDecodeError, TypeError):
            return None
    
    def set_performance_scores(self, scores: PerformanceScores) -> None:
        """Set performance scores from PerformanceScores object."""
        import json
        self.performance_scores = json.dumps(scores.to_dict())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "model_name": self.model_name,
            "display_name": self.display_name,
            "provider": self.provider,
            "dimension": self.dimension,
            "model_type": self.model_type,
            "language_scores": self.get_language_scores().to_dict(),
            "domain_scores": self.get_domain_scores().to_dict(),
            "multimodal_score": self.multimodal_score,
            "performance_scores": self.get_performance_scores().to_dict() if self.get_performance_scores() else None,
            "description": self.description,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
