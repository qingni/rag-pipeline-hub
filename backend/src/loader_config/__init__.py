"""Loader configuration package for document processing.

This package contains format strategies and loader configurations.
"""
from .format_strategies import (
    LOADER_REGISTRY,
    FORMAT_STRATEGIES,
    get_loader_config,
    get_format_strategy,
    get_supported_formats,
    get_available_loaders,
    is_format_supported
)

__all__ = [
    'LOADER_REGISTRY',
    'FORMAT_STRATEGIES',
    'get_loader_config',
    'get_format_strategy',
    'get_supported_formats',
    'get_available_loaders',
    'is_format_supported'
]
