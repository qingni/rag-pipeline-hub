"""Chunker factory and exports."""
from .base_chunker import BaseChunker
from .character_chunker import CharacterChunker
from .paragraph_chunker import ParagraphChunker
from .heading_chunker import HeadingChunker
from .semantic_chunker import SemanticChunker
from .parent_child_chunker import ParentChildChunker
from .multimodal_chunker import MultimodalChunker
from .hybrid_chunker import HybridChunker
from .image_extractor import ImageExtractor


# Chunker registry
CHUNKER_REGISTRY = {
    'character': CharacterChunker,
    'paragraph': ParagraphChunker,
    'heading': HeadingChunker,
    'semantic': SemanticChunker,
    'parent_child': ParentChildChunker,
    'multimodal': MultimodalChunker,
    'hybrid': HybridChunker
}


def get_chunker(strategy_type: str, **params) -> BaseChunker:
    """
    Get chunker instance for strategy type.
    
    Args:
        strategy_type: Strategy type identifier
        **params: Chunking parameters
    
    Returns:
        Chunker instance
    
    Raises:
        ValueError: If strategy type unknown
    """
    chunker_class = CHUNKER_REGISTRY.get(strategy_type)
    if not chunker_class:
        raise ValueError(f"Unknown chunking strategy: {strategy_type}")
    
    return chunker_class(**params)


__all__ = [
    'BaseChunker',
    'CharacterChunker',
    'ParagraphChunker',
    'HeadingChunker',
    'SemanticChunker',
    'ParentChildChunker',
    'MultimodalChunker',
    'HybridChunker',
    'ImageExtractor',
    'get_chunker',
    'CHUNKER_REGISTRY'
]
