"""Chunker factory and exports."""
from .base_chunker import BaseChunker
from .character_chunker import CharacterChunker
from .paragraph_chunker import ParagraphChunker
from .heading_chunker import HeadingChunker
from .semantic_chunker import SemanticChunker


# Chunker registry
CHUNKER_REGISTRY = {
    'character': CharacterChunker,
    'paragraph': ParagraphChunker,
    'heading': HeadingChunker,
    'semantic': SemanticChunker
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
    'get_chunker',
    'CHUNKER_REGISTRY'
]
