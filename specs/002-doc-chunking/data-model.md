# Data Model: 文档分块功能

**Feature**: 002-doc-chunking  
**Date**: 2025-12-05  
**Source**: Extracted from [spec.md](./spec.md) Key Entities section

## Entity Relationship Overview

```
Document (from load/parse)
    ↓ (reads from JSON)
ChunkingTask
    ↓ (executes using)
ChunkingStrategy
    ↓ (produces)
ChunkingResult
    ↓ (contains)
DocumentChunk[]
```

---

## Entity Definitions

### 1. ChunkingTask

**Purpose**: Represents a chunking task instance with its execution state and configuration.

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| task_id | UUID | Yes | Unique identifier for the task | Auto-generated |
| source_document_id | String | Yes | Reference to source document | Must exist in documents table |
| source_file_path | String | Yes | Path to load/parse JSON file | Must be valid path in results/load or results/parse |
| chunking_strategy | Enum | Yes | Selected chunking strategy | One of: character, paragraph, heading, semantic |
| chunking_params | JSON | Yes | Strategy-specific parameters | See ChunkingParams schema |
| status | Enum | Yes | Current task status | One of: pending, running, completed, partial, failed |
| queue_position | Integer | No | Position in queue (if pending) | >= 0, null if not queued |
| created_at | DateTime | Yes | Task creation timestamp | ISO 8601 format |
| started_at | DateTime | No | Task execution start time | Null if not started |
| completed_at | DateTime | No | Task completion time | Null if not completed |
| error_message | String | No | Error description if failed | Max 1000 characters |

**State Transitions**:
```
pending → running → completed
         ↓         ↘ partial
         ↓           ↘ failed
         → cancelled
```

**Validation Rules**:
- `source_file_path` must point to existing JSON file
- `chunking_params.chunk_size` must be 50-5000
- `chunking_params.chunk_overlap` must be 0-500
- `chunk_overlap` must be < `chunk_size`
- `completed_at` must be >= `started_at`
- Only tasks in `pending` state can be cancelled

**Indexes**:
- Primary: task_id
- Index: source_document_id
- Index: status, created_at (for queue management)

---

### 2. ChunkingStrategy

**Purpose**: Defines available chunking strategies and their default configurations.

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| strategy_id | String | Yes | Unique strategy identifier | Primary key, one of: character, paragraph, heading, semantic |
| strategy_name | String | Yes | Human-readable name | Max 50 characters |
| strategy_type | Enum | Yes | Strategy category | Same as strategy_id |
| description | String | Yes | Strategy description | Max 500 characters |
| default_params | JSON | Yes | Default parameter values | See ChunkingParams schema |
| is_enabled | Boolean | Yes | Whether strategy is available | Default: true |
| requires_structure | Boolean | Yes | Whether requires document structure | true for heading strategy |

**Pre-defined Strategies**:

```json
[
  {
    "strategy_id": "character",
    "strategy_name": "按字数分块",
    "strategy_type": "character",
    "description": "按固定字符数切分文档，支持块之间的重叠",
    "default_params": {
      "chunk_size": 1000,
      "chunk_overlap": 100,
      "separators": ["\n\n", "\n", " ", ""]
    },
    "is_enabled": true,
    "requires_structure": false
  },
  {
    "strategy_id": "paragraph",
    "strategy_name": "按段落分块",
    "strategy_type": "paragraph",
    "description": "以自然段落为基本单位分块，当段落过长时进一步切分",
    "default_params": {
      "chunk_size": 800,
      "paragraph_separator": "\n\n",
      "max_chunk_size": 5000
    },
    "is_enabled": true,
    "requires_structure": false
  },
  {
    "strategy_id": "heading",
    "strategy_name": "按标题分块",
    "strategy_type": "heading",
    "description": "按标题层级分块，每个块包含标题及其下的所有内容",
    "default_params": {
      "heading_formats": ["markdown", "html"],
      "min_headings": 2
    },
    "is_enabled": true,
    "requires_structure": true
  },
  {
    "strategy_id": "semantic",
    "strategy_name": "按语义分块",
    "strategy_type": "semantic",
    "description": "使用语义相似度算法识别语义边界，在保持语义完整性的前提下进行分块",
    "default_params": {
      "min_chunk_size": 300,
      "max_chunk_size": 1200,
      "similarity_threshold": 0.3,
      "fallback_strategy": "paragraph"
    },
    "is_enabled": true,
    "requires_structure": false
  }
]
```

**Validation Rules**:
- `strategy_id` must be unique
- `default_params` must conform to parameter constraints

---

### 3. DocumentChunk

**Purpose**: Represents a single chunk of text extracted from a document.

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| chunk_id | UUID | Yes | Unique chunk identifier | Auto-generated |
| result_id | UUID | Yes | Reference to ChunkingResult | Foreign key |
| chunk_index | Integer | Yes | Sequential chunk number | >= 0 |
| content | Text | Yes | Chunk text content | Max 10000 characters |
| **metadata** | **JSON** | **Yes** | **Chunk metadata** | **See Metadata schema below** |

**Metadata Schema**:
```json
{
  "char_count": "integer (required)",
  "word_count": "integer (required)",
  "page_number": "integer (optional)",
  "start_position": "integer (required, >= 0)",
  "end_position": "integer (required, > start_position)",
  "headings": ["string"] (optional, for heading strategy),
  "paragraph_count": "integer (optional)",
  "is_fallback": "boolean (optional, for semantic strategy)"
}
```

**Validation Rules**:
- `chunk_index` must be unique within a result
- `content` cannot be empty
- `char_count` must match actual content length
- `word_count` must be > 0
- `end_position` must be > `start_position`
- Chunks must be ordered by `chunk_index`

**Indexes**:
- Primary: chunk_id
- Index: result_id, chunk_index (composite)
- Index: result_id (for efficient bulk loading)

---

### 4. ChunkingResult

**Purpose**: Aggregates all chunks and metadata for a completed chunking operation.

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| result_id | UUID | Yes | Unique result identifier | Primary key |
| task_id | UUID | Yes | Reference to ChunkingTask | Foreign key |
| document_id | String | Yes | Original document identifier | From source JSON |
| document_name | String | Yes | Document filename | Max 255 characters |
| source_file | String | Yes | Path to source JSON | Valid file path |
| total_chunks | Integer | Yes | Number of chunks produced | >= 0 |
| chunking_strategy | Enum | Yes | Applied strategy | Same as ChunkingTask |
| chunking_params | JSON | Yes | Actual parameters used | ChunkingParams schema |
| status | Enum | Yes | Result status | completed, partial, failed |
| created_at | DateTime | Yes | Result creation time | ISO 8601 |
| processing_time | Float | Yes | Time in seconds | >= 0 |
| error_info | JSON | No | Error details if applicable | See ErrorInfo schema |
| statistics | JSON | Yes | Aggregated statistics | See Statistics schema |
| json_file_path | String | Yes | Path to result JSON file | results/chunking/*.json |
| file_size | Integer | Yes | JSON file size in bytes | > 0 |

**Statistics Schema**:
```json
{
  "avg_chunk_size": "float (required)",
  "max_chunk_size": "integer (required)",
  "min_chunk_size": "integer (required)",
  "total_characters": "integer (required)"
}
```

**ErrorInfo Schema** (when status = partial or failed):
```json
{
  "error_position": "integer (character position where error occurred)",
  "error_message": "string (error description)",
  "affected_chunks": "integer (number of chunks not processed)"
}
```

**Validation Rules**:
- `total_chunks` must match actual DocumentChunk count
- `processing_time` should be reasonable (< 300 seconds for 50MB doc)
- `status` must be `completed` if `total_chunks` > 0 and no errors
- `status` must be `partial` if `error_info` exists and `total_chunks` > 0
- `status` must be `failed` if `total_chunks` == 0 and `error_info` exists
- `json_file_path` must follow naming convention: `{document_name}_chunk_{timestamp}.json`

**Indexes**:
- Primary: result_id
- Index: task_id (unique)
- Index: document_id
- Index: document_name, chunking_strategy, created_at (composite, for history queries)
- Index: created_at (for pagination)

---

## Database Schema (SQLAlchemy)

```python
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, JSON, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

Base = declarative_base()

class TaskStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StrategyType(enum.Enum):
    CHARACTER = "character"
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    SEMANTIC = "semantic"

class ResultStatus(enum.Enum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"

class ChunkingTask(Base):
    __tablename__ = "chunking_tasks"
    
    task_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_document_id = Column(String(255), nullable=False, index=True)
    source_file_path = Column(String(500), nullable=False)
    chunking_strategy = Column(SQLEnum(StrategyType), nullable=False)
    chunking_params = Column(JSON, nullable=False)
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    queue_position = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String(1000), nullable=True)
    
    # Relationship
    result = relationship("ChunkingResult", back_populates="task", uselist=False)
    
    __table_args__ = (
        Index('idx_status_created', 'status', 'created_at'),
    )

class ChunkingStrategy(Base):
    __tablename__ = "chunking_strategies"
    
    strategy_id = Column(String(50), primary_key=True)
    strategy_name = Column(String(50), nullable=False)
    strategy_type = Column(SQLEnum(StrategyType), nullable=False)
    description = Column(String(500), nullable=False)
    default_params = Column(JSON, nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True)
    requires_structure = Column(Boolean, nullable=False, default=False)

class ChunkingResult(Base):
    __tablename__ = "chunking_results"
    
    result_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey('chunking_tasks.task_id'), nullable=False, unique=True)
    document_id = Column(String(255), nullable=False, index=True)
    document_name = Column(String(255), nullable=False, index=True)
    source_file = Column(String(500), nullable=False)
    total_chunks = Column(Integer, nullable=False)
    chunking_strategy = Column(SQLEnum(StrategyType), nullable=False, index=True)
    chunking_params = Column(JSON, nullable=False)
    status = Column(SQLEnum(ResultStatus), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    processing_time = Column(Float, nullable=False)
    error_info = Column(JSON, nullable=True)
    statistics = Column(JSON, nullable=False)
    json_file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    
    # Relationships
    task = relationship("ChunkingTask", back_populates="result")
    chunks = relationship("DocumentChunk", back_populates="result", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_doc_strategy_time', 'document_name', 'chunking_strategy', 'created_at'),
    )

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    chunk_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    result_id = Column(String(36), ForeignKey('chunking_results.result_id'), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=False)
    
    # Relationship
    result = relationship("ChunkingResult", back_populates="chunks")
    
    __table_args__ = (
        Index('idx_result_index', 'result_id', 'chunk_index', unique=True),
    )
```

---

## JSON File Schema

**File Location**: `results/chunking/{document_name}_chunk_{timestamp}.json`

**Schema**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["document_id", "document_name", "source_file", "total_chunks", "chunking_strategy", "chunking_params", "status", "created_at", "processing_time", "statistics", "chunks"],
  "properties": {
    "document_id": {"type": "string"},
    "document_name": {"type": "string"},
    "source_file": {"type": "string"},
    "total_chunks": {"type": "integer", "minimum": 0},
    "chunking_strategy": {
      "type": "string",
      "enum": ["character", "paragraph", "heading", "semantic"]
    },
    "chunking_params": {
      "type": "object",
      "properties": {
        "chunk_size": {"type": "integer", "minimum": 50, "maximum": 5000},
        "chunk_overlap": {"type": "integer", "minimum": 0, "maximum": 500}
      }
    },
    "status": {
      "type": "string",
      "enum": ["completed", "partial", "failed"]
    },
    "created_at": {"type": "string", "format": "date-time"},
    "processing_time": {"type": "number", "minimum": 0},
    "error_info": {
      "type": "object",
      "properties": {
        "error_position": {"type": "integer"},
        "error_message": {"type": "string"},
        "affected_chunks": {"type": "integer"}
      }
    },
    "statistics": {
      "type": "object",
      "required": ["avg_chunk_size", "max_chunk_size", "min_chunk_size", "total_characters"],
      "properties": {
        "avg_chunk_size": {"type": "number"},
        "max_chunk_size": {"type": "integer"},
        "min_chunk_size": {"type": "integer"},
        "total_characters": {"type": "integer"}
      }
    },
    "chunks": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["content", "metadata"],
        "properties": {
          "content": {"type": "string"},
          "metadata": {
            "type": "object",
            "required": ["chunk_id", "chunk_index", "char_count", "word_count", "start_position", "end_position"],
            "properties": {
              "chunk_id": {"type": "string", "format": "uuid"},
              "chunk_index": {"type": "integer", "minimum": 0},
              "char_count": {"type": "integer", "minimum": 1},
              "word_count": {"type": "integer", "minimum": 1},
              "page_number": {"type": "integer", "minimum": 1},
              "start_position": {"type": "integer", "minimum": 0},
              "end_position": {"type": "integer"},
              "headings": {"type": "array", "items": {"type": "string"}},
              "paragraph_count": {"type": "integer", "minimum": 0},
              "is_fallback": {"type": "boolean"}
            }
          }
        }
      }
    }
  }
}
```

---

## Data Flow

```
1. User selects document (from results/load or results/parse)
   ↓
2. Frontend loads document list from /api/documents/parsed
   ↓
3. User configures strategy and parameters
   ↓
4. POST /api/chunking/chunk → Creates ChunkingTask (status: pending)
   ↓
5. Queue manager picks up task → Updates status to running
   ↓
6. ChunkingService executes:
   - Loads source JSON
   - Applies selected strategy
   - Generates DocumentChunks
   - Calculates statistics
   ↓
7. Saves results:
   - JSON file to results/chunking/
   - ChunkingResult + DocumentChunks to database
   ↓
8. Updates task status to completed/partial/failed
   ↓
9. Frontend polls /api/chunking/task/{task_id} for status
   ↓
10. Displays results in UI
```

---

## Summary

- **4 Core Entities**: ChunkingTask, ChunkingStrategy, DocumentChunk, ChunkingResult
- **3 Database Tables** (+ 1 strategy config table): Fully indexed for performance
- **1 JSON Schema**: Standardized output format for downstream processing
- **State Machine**: Clear task lifecycle with 6 states
- **Validation**: Comprehensive field-level and cross-field validation rules
- **Performance**: Optimized indexes for common query patterns (pagination, filtering, sorting)
