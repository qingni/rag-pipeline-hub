"""
Vector Index Data Models Package
"""

from .vector_index import (
    VectorIndex,
    VectorIndexSchema,
    CreateIndexRequest,
    IndexListResponse,
    IndexResponse,
    IndexProvider,
    IndexStatus,
    MetricType
)
from .index_statistics import (
    IndexStatistics,
    IndexStatisticsSchema,
    StatisticsResponse
)
from .query_history import (
    QueryHistory,
    QueryHistorySchema,
    QueryHistoryListResponse
)
from .search import (
    SearchHistory,
    SearchConfig
)
from .chunk import Chunk, ChunkType
from .chunking_task import ChunkingTask, TaskStatus, StrategyType
from .chunking_result import ChunkingResult, ResultStatus
from .parent_chunk import ParentChunk
from .hybrid_chunking_config import HybridChunkingConfig
from .chunk_metadata import (
    ChunkTypeEnum,
    TextChunkMetadata,
    TableChunkMetadata,
    ImageChunkMetadata,
    CodeChunkMetadata,
    create_chunk_metadata,
    validate_multimodal_metadata
)

__all__ = [
    # Vector Index models
    "VectorIndex",
    "VectorIndexSchema",
    "CreateIndexRequest",
    "IndexListResponse",
    "IndexResponse",
    "IndexProvider",
    "IndexStatus",
    "MetricType",
    
    # Statistics models
    "IndexStatistics",
    "IndexStatisticsSchema",
    "StatisticsResponse",
    
    # Query history models
    "QueryHistory",
    "QueryHistorySchema",
    "QueryHistoryListResponse",
    
    # Search models
    "SearchHistory",
    "SearchConfig",
    
    # Chunk models
    "Chunk",
    "ChunkType",
    "ChunkingTask",
    "TaskStatus",
    "StrategyType",
    "ChunkingResult",
    "ResultStatus",
    "ParentChunk",
    "HybridChunkingConfig",
    
    # Chunk metadata models
    "ChunkTypeEnum",
    "TextChunkMetadata",
    "TableChunkMetadata",
    "ImageChunkMetadata",
    "CodeChunkMetadata",
    "create_chunk_metadata",
    "validate_multimodal_metadata",
]
