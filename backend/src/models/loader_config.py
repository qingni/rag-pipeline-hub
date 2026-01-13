"""Loader configuration models.

This module defines the configuration structures for document loaders,
used for intelligent selection and fallback strategies.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

from .loading_result import ExtractionQuality


@dataclass
class LoaderConfig:
    """Loader configuration."""
    name: str
    display_name: str
    supported_formats: List[str]
    priority: int  # Lower number = higher priority
    
    # Performance characteristics
    avg_speed: str  # "fast", "medium", "slow"
    quality_level: ExtractionQuality
    
    # Dependency information
    requires_installation: bool = False
    installation_command: Optional[str] = None
    
    # Capability flags
    supports_tables: bool = False
    supports_images: bool = False
    supports_formulas: bool = False
    supports_ocr: bool = False
    
    # Availability status (set at runtime)
    is_available: bool = True
    unavailable_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'supported_formats': self.supported_formats,
            'priority': self.priority,
            'avg_speed': self.avg_speed,
            'quality_level': self.quality_level.value,
            'requires_installation': self.requires_installation,
            'installation_command': self.installation_command,
            'supports_tables': self.supports_tables,
            'supports_images': self.supports_images,
            'supports_formulas': self.supports_formulas,
            'supports_ocr': self.supports_ocr,
            'is_available': self.is_available,
            'unavailable_reason': self.unavailable_reason
        }


@dataclass
class FormatStrategy:
    """Format parsing strategy."""
    format: str
    primary_loader: str
    fallback_loaders: List[str] = field(default_factory=list)
    
    # Intelligent selection thresholds
    size_threshold_mb: float = 20.0  # Use fast loader above this size
    fast_loader: Optional[str] = None  # Fast loader for large files
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'format': self.format,
            'primary_loader': self.primary_loader,
            'fallback_loaders': self.fallback_loaders,
            'size_threshold_mb': self.size_threshold_mb,
            'fast_loader': self.fast_loader
        }
    
    def get_loader_chain(self, file_size_mb: float = 0) -> List[str]:
        """
        Get the ordered list of loaders to try.
        
        Args:
            file_size_mb: File size in MB for intelligent selection
            
        Returns:
            Ordered list of loader names to try
        """
        loaders = []
        
        # For large files, prefer fast loader if available
        if file_size_mb > self.size_threshold_mb and self.fast_loader:
            loaders.append(self.fast_loader)
            # Add primary if different
            if self.primary_loader != self.fast_loader:
                loaders.append(self.primary_loader)
        else:
            loaders.append(self.primary_loader)
        
        # Add fallback loaders
        for loader in self.fallback_loaders:
            if loader not in loaders:
                loaders.append(loader)
        
        return loaders
