"""
Model capability management service.

Manages model capability configurations:
- Load from YAML config file
- Store customizations in database
- Provide model capability queries
"""
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import yaml

from ..models.model_capability import (
    ModelCapability,
    LanguageScores,
    DomainScores,
    PerformanceScores,
)


@dataclass
class ModelCapabilityInfo:
    """Model capability information for recommendation."""
    model_name: str
    display_name: str
    provider: str
    dimension: int
    model_type: str
    language_scores: LanguageScores
    domain_scores: DomainScores
    multimodal_score: float
    performance_scores: Optional[PerformanceScores]
    description: str
    is_enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_name": self.model_name,
            "display_name": self.display_name,
            "provider": self.provider,
            "dimension": self.dimension,
            "model_type": self.model_type,
            "language_scores": self.language_scores.to_dict(),
            "domain_scores": self.domain_scores.to_dict(),
            "multimodal_score": self.multimodal_score,
            "performance_scores": self.performance_scores.to_dict() if self.performance_scores else None,
            "description": self.description,
            "is_enabled": self.is_enabled,
        }


class ModelCapabilityService:
    """
    Service for managing model capability configurations.
    
    Loads default configurations from YAML and supports database overrides.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize service.
        
        Args:
            config_path: Path to model_capabilities.yaml
        """
        if config_path is None:
            # Default to src/config/model_capabilities.yaml
            src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(src_dir, 'config', 'model_capabilities.yaml')
        
        self.config_path = config_path
        self._models: Dict[str, ModelCapabilityInfo] = {}
        self._recommendation_weights: Dict[str, float] = {}
        self._outlier_config: Dict[str, float] = {}
        self._default_model: str = "bge-m3"
        self._default_multimodal_model: str = "qwen3-vl-embedding-8b"
        
        # Load configuration
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            # Use hardcoded defaults if config doesn't exist
            self._load_default_config()
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Load models
            models_config = config.get('models', {})
            for model_name, model_data in models_config.items():
                self._models[model_name] = self._parse_model_config(model_name, model_data)
            
            # Load recommendation weights
            self._recommendation_weights = config.get('recommendation_weights', {
                'language_match': 0.40,
                'domain_match': 0.35,
                'multimodal_support': 0.25,
            })
            
            # Load outlier config
            self._outlier_config = config.get('outlier_detection', {
                'default_threshold': 0.3,
                'min_threshold': 0.1,
                'max_threshold': 0.5,
            })
            
            # Load defaults
            self._default_model = config.get('default_model', 'bge-m3')
            self._default_multimodal_model = config.get('default_multimodal_model', 'qwen3-vl-embedding-8b')
            
        except Exception as e:
            print(f"Warning: Failed to load config from {self.config_path}: {e}")
            self._load_default_config()
    
    def _load_default_config(self) -> None:
        """Load hardcoded default configuration."""
        # BGE-M3
        self._models['bge-m3'] = ModelCapabilityInfo(
            model_name='bge-m3',
            display_name='BGE-M3',
            provider='bge',
            dimension=1024,
            model_type='text',
            language_scores=LanguageScores(zh=0.95, en=0.90, ja=0.80, ko=0.80, default=0.70),
            domain_scores=DomainScores(general=0.85, technical=0.80, legal=0.75, medical=0.70, 
                                       financial=0.75, academic=0.80, news=0.80, default=0.75),
            multimodal_score=0.0,
            performance_scores=PerformanceScores(throughput=0.85, latency=0.80, cost=0.90),
            description='BGE-M3 多语言模型',
        )
        
        # Qwen3-Embedding-8B
        self._models['qwen3-embedding-8b'] = ModelCapabilityInfo(
            model_name='qwen3-embedding-8b',
            display_name='Qwen3-Embedding-8B',
            provider='qwen',
            dimension=4096,
            model_type='text',
            language_scores=LanguageScores(zh=0.98, en=0.92, ja=0.75, ko=0.75, default=0.65),
            domain_scores=DomainScores(general=0.90, technical=0.95, legal=0.85, medical=0.80,
                                       financial=0.85, academic=0.90, news=0.85, default=0.80),
            multimodal_score=0.0,
            performance_scores=PerformanceScores(throughput=0.75, latency=0.70, cost=0.70),
            description='通义千问 Embedding 8B',
        )
        
        # Qwen3-VL-Embedding-8B (multimodal)
        self._models['qwen3-vl-embedding-8b'] = ModelCapabilityInfo(
            model_name='qwen3-vl-embedding-8b',
            display_name='Qwen3-VL-Embedding-8B',
            provider='qwen',
            dimension=4096,
            model_type='multimodal',
            language_scores=LanguageScores(zh=0.95, en=0.90, ja=0.70, ko=0.70, default=0.60),
            domain_scores=DomainScores(general=0.90, technical=0.90, legal=0.75, medical=0.85,
                                       financial=0.80, academic=0.85, news=0.85, default=0.80),
            multimodal_score=0.95,
            performance_scores=PerformanceScores(throughput=0.65, latency=0.60, cost=0.55),
            description='通义千问多模态 Embedding 8B',
        )
        
        self._recommendation_weights = {
            'language_match': 0.40,
            'domain_match': 0.35,
            'multimodal_support': 0.25,
        }
        
        self._outlier_config = {
            'default_threshold': 0.3,
            'min_threshold': 0.1,
            'max_threshold': 0.5,
        }
    
    def _parse_model_config(self, model_name: str, data: Dict) -> ModelCapabilityInfo:
        """Parse model configuration from YAML data."""
        # Parse language scores
        lang_data = data.get('language_scores', {})
        language_scores = LanguageScores(
            zh=lang_data.get('zh', 0.5),
            en=lang_data.get('en', 0.5),
            ja=lang_data.get('ja', 0.3),
            ko=lang_data.get('ko', 0.3),
            default=lang_data.get('default', 0.3),
        )
        
        # Parse domain scores
        domain_data = data.get('domain_scores', {})
        domain_scores = DomainScores(
            general=domain_data.get('general', 0.5),
            technical=domain_data.get('technical', 0.5),
            legal=domain_data.get('legal', 0.5),
            medical=domain_data.get('medical', 0.5),
            financial=domain_data.get('financial', 0.5),
            academic=domain_data.get('academic', 0.5),
            news=domain_data.get('news', 0.5),
            default=domain_data.get('default', 0.5),
        )
        
        # Parse performance scores
        perf_data = data.get('performance', {})
        performance_scores = PerformanceScores(
            throughput=perf_data.get('throughput', 0.5),
            latency=perf_data.get('latency', 0.5),
            cost=perf_data.get('cost', 0.5),
        ) if perf_data else None
        
        return ModelCapabilityInfo(
            model_name=model_name,
            display_name=data.get('name', model_name),
            provider=data.get('provider', 'unknown'),
            dimension=data.get('dimension', 1024),
            model_type=data.get('model_type', 'text'),
            language_scores=language_scores,
            domain_scores=domain_scores,
            multimodal_score=data.get('multimodal_score', 0.0),
            performance_scores=performance_scores,
            description=data.get('description', ''),
        )
    
    def get_model(self, model_name: str) -> Optional[ModelCapabilityInfo]:
        """Get model capability info by name."""
        return self._models.get(model_name)
    
    def get_all_models(self, enabled_only: bool = True) -> List[ModelCapabilityInfo]:
        """Get all model capabilities."""
        models = list(self._models.values())
        if enabled_only:
            models = [m for m in models if m.is_enabled]
        return models
    
    def get_text_models(self, enabled_only: bool = True) -> List[ModelCapabilityInfo]:
        """Get text-only models."""
        models = self.get_all_models(enabled_only)
        return [m for m in models if m.model_type == 'text']
    
    def get_multimodal_models(self, enabled_only: bool = True) -> List[ModelCapabilityInfo]:
        """Get multimodal models."""
        models = self.get_all_models(enabled_only)
        return [m for m in models if m.model_type == 'multimodal']
    
    def get_recommendation_weights(self) -> Dict[str, float]:
        """Get recommendation algorithm weights."""
        return self._recommendation_weights.copy()
    
    def get_outlier_threshold(self) -> float:
        """Get default outlier detection threshold."""
        return self._outlier_config.get('default_threshold', 0.3)
    
    def get_default_model(self, has_multimodal: bool = False) -> str:
        """Get default model name."""
        if has_multimodal:
            return self._default_multimodal_model
        return self._default_model
    
    def update_model(self, model_name: str, updates: Dict[str, Any]) -> bool:
        """
        Update model capability (for admin customization).
        
        Args:
            model_name: Model to update
            updates: Dict of fields to update
            
        Returns:
            True if successful
        """
        if model_name not in self._models:
            return False
        
        model = self._models[model_name]
        
        # Update language scores
        if 'language_scores' in updates:
            model.language_scores = LanguageScores.from_dict(updates['language_scores'])
        
        # Update domain scores
        if 'domain_scores' in updates:
            model.domain_scores = DomainScores.from_dict(updates['domain_scores'])
        
        # Update other fields
        if 'multimodal_score' in updates:
            model.multimodal_score = updates['multimodal_score']
        if 'is_enabled' in updates:
            model.is_enabled = updates['is_enabled']
        if 'description' in updates:
            model.description = updates['description']
        
        return True
    
    def reload_config(self) -> None:
        """Reload configuration from file."""
        self._models.clear()
        self._load_config()


# Global instance
_default_service = None


def get_model_capability_service() -> ModelCapabilityService:
    """Get default model capability service instance."""
    global _default_service
    if _default_service is None:
        _default_service = ModelCapabilityService()
    return _default_service
