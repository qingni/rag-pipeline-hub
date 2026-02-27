# Data Model: Vector Embedding Module

**Feature**: 003-vector-embedding  
**Date**: 2025-12-17  
**Status**: Complete

## Overview

This document defines the data entities, relationships, validation rules, and state transitions for the vector embedding module.

## Entity Definitions

### 1. EmbeddingResult (Database Entity)

**Purpose**: Store metadata about embedding operations

**Table**: `embedding_results`

**Fields**:

| Field | Type | Nullable | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| result_id | TEXT | NO | UUID | PRIMARY KEY | Unique identifier for embedding result |
| document_id | TEXT | NO | - | FOREIGN KEY → documents.document_id | Source document reference |
| chunking_result_id | TEXT | NO | - | FOREIGN KEY → chunking_results.result_id | Source chunking result reference |
| model | TEXT | NO | - | IN ('bge-m3', 'qwen3-embedding-8b', 'qwen3-vl-embedding-8b') | Embedding model used |
| status | TEXT | NO | - | IN ('SUCCESS', 'FAILED', 'PARTIAL_SUCCESS') | Processing status |
| successful_count | INTEGER | NO | - | >= 0 | Number of successfully vectorized chunks |
| failed_count | INTEGER | NO | - | >= 0 | Number of failed chunks |
| vector_dimension | INTEGER | NO | - | IN (1024, 4096) or custom (64-4096 for multimodal) | Dimension size of generated vectors |
| json_file_path | TEXT | NO | - | LENGTH > 0 | Relative path to JSON file containing vectors |
| processing_time_ms | REAL | NO | - | >= 0.0 | Total processing time in milliseconds |
| created_at | TIMESTAMP | NO | CURRENT_TIMESTAMP | - | Record creation timestamp |
| error_message | TEXT | YES | NULL | - | Error details for FAILED/PARTIAL_SUCCESS status |

**Indexes**:
- PRIMARY KEY on `result_id`
- COMPOSITE INDEX on `(document_id, model)` - for "get latest by document+model" queries
- INDEX on `created_at DESC` - for "get latest" queries and date range filtering
- INDEX on `status` - for status-based filtering

**Validation Rules**:
- `successful_count + failed_count > 0` (at least one chunk processed)
- `status = 'SUCCESS'` implies `failed_count = 0`
- `status = 'FAILED'` implies `successful_count = 0`
- `status = 'PARTIAL_SUCCESS'` implies `successful_count > 0 AND failed_count > 0`
- `error_message` must be set when `status IN ('FAILED', 'PARTIAL_SUCCESS')`
- `json_file_path` must be relative path (no leading `/`)
- `model` must match one of the supported models

**Example**:
```json
{
  "result_id": "emb_550e8400-e29b-41d4-a716-446655440000",
  "document_id": "doc_123",
  "chunking_result_id": "chunk_456",
  "model": "qwen3-embedding-8b",
  "status": "SUCCESS",
  "successful_count": 50,
  "failed_count": 0,
  "vector_dimension": 4096,
  "json_file_path": "embedding/doc_123_20251217_103045.json",
  "processing_time_ms": 12450.5,
  "created_at": "2025-12-17T10:30:45Z",
  "error_message": null
}
```

---

### 2. EmbeddingVectorFile (JSON File Entity)

**Purpose**: Store actual vector values and chunk metadata

**File Location**: `{EMBEDDING_RESULTS_DIR}/{document_id}_{timestamp}.json`

**Schema**:
```json
{
  "result_id": "string",
  "document_id": "string",
  "chunking_result_id": "string",
  "model": "string",
  "vector_dimension": "integer",
  "created_at": "ISO8601 timestamp",
  "vectors": [
    {
      "chunk_index": "integer",
      "chunk_id": "string (optional)",
      "text_hash": "string (sha256:...)",
      "text_length": "integer",
      "vector": [0.123, -0.456, ...],
      "processing_time_ms": "float"
    }
  ]
}
```

**Validation Rules**:
- All vectors must have same length (`vector_dimension`)
- `vectors` array length must equal `successful_count` from database record
- Each `vector` array must contain only finite floating-point numbers
- `text_hash` must start with `sha256:`
- File must be valid JSON (reject malformed files)

**Example**:
```json
{
  "result_id": "emb_550e8400-e29b-41d4-a716-446655440000",
  "document_id": "doc_123",
  "chunking_result_id": "chunk_456",
  "model": "qwen3-embedding-8b",
  "vector_dimension": 4096,
  "created_at": "2025-12-17T10:30:45Z",
  "vectors": [
    {
      "chunk_index": 0,
      "chunk_id": "chunk_456_0",
      "text_hash": "sha256:abc123...",
      "text_length": 512,
      "vector": [0.0234, -0.0156, 0.0789, ...],  // 4096 floats
      "processing_time_ms": 245.3
    },
    {
      "chunk_index": 1,
      "chunk_id": "chunk_456_1",
      "text_hash": "sha256:def456...",
      "text_length": 487,
      "vector": [0.0123, -0.0245, 0.0567, ...],  // 4096 floats
      "processing_time_ms": 238.7
    }
  ]
}
```

---

### 3. EmbeddingModel (Configuration Entity)

**Purpose**: Define supported embedding model configurations

**Storage**: In-memory constant (`EMBEDDING_MODELS` dict in `embedding_service.py`)

**Schema**:
```python
{
  "model_name": {
    "name": str,
    "dimension": int,
    "description": str,
    "provider": str,
    "supports_multilingual": bool,
    "max_batch_size": int
  }
}
```

**Supported Models**:

| Name | Dimension | Provider | Multilingual | Max Batch | Type | Description |
|------|-----------|----------|--------------|-----------|------|-------------|
| bge-m3 | 1024 | bge | Yes | 1000 | text | BGE-M3 多语言模型，支持密集检索、多向量检索和稀疏检索 |
| qwen3-embedding-8b | 4096 | qwen | Yes | 1000 | text | 通义千问 Embedding 8B，高精度、长文本支持、动态维度输出 |
| qwen3-vl-embedding-8b | 64-4096 | qwen | Yes | 1000 | multimodal | 通义千问多模态 Embedding 8B，支持文本、图像、视频及任意多模态组合输入 |

**Validation Rules**:
- Model name must be alphanumeric with hyphens only
- Dimension must be power of 2 (for optimization)
- Max batch size must be <= 1000 (global limit)

---

### 4. EmbeddingRequest (API Request Entity)

**Purpose**: Represent incoming vectorization requests

**Variants**:

#### 4a. FromChunkingResultRequest
```python
{
  "result_id": str,        # Chunking result ID (required)
  "model": str,            # Embedding model name (required)
  "request_id": str | None # Optional request tracking ID
}
```

#### 4b. FromDocumentRequest
```python
{
  "document_id": str,        # Document ID (required)
  "model": str,              # Embedding model name (required)
  "strategy_type": str | None,  # Optional filter (fixed_size, semantic, etc.)
  "request_id": str | None   # Optional request tracking ID
}
```

**Validation Rules**:
- `result_id` must exist in `chunking_results` table with `status = 'COMPLETED'`
- `document_id` must exist in `documents` table
- `model` must be one of the supported models
- `strategy_type` (if provided) must be valid ChunkingStrategy enum value
- Request body must be valid JSON

---

### 5. EmbeddingResponse (API Response Entity)

**Purpose**: Return vectorization operation results

**Schema**:
```python
{
  "result_id": str,
  "document_id": str,
  "chunking_result_id": str,
  "model": str,
  "status": "SUCCESS" | "FAILED" | "PARTIAL_SUCCESS",
  "successful_count": int,
  "failed_count": int,
  "vector_dimension": int,
  "json_file_path": str,
  "processing_time_ms": float,
  "created_at": str,  # ISO8601
  "error_message": str | null,
  "failures": [        # Only present for PARTIAL_SUCCESS
    {
      "chunk_index": int,
      "error_type": str,
      "error_message": str,
      "retry_recommended": bool
    }
  ]
}
```

**Example (Success)**:
```json
{
  "result_id": "emb_550e8400-e29b-41d4-a716-446655440000",
  "document_id": "doc_123",
  "chunking_result_id": "chunk_456",
  "model": "qwen3-embedding-8b",
  "status": "SUCCESS",
  "successful_count": 50,
  "failed_count": 0,
  "vector_dimension": 4096,
  "json_file_path": "embedding/doc_123_20251217_103045.json",
  "processing_time_ms": 12450.5,
  "created_at": "2025-12-17T10:30:45Z",
  "error_message": null
}
```

**Example (Partial Success)**:
```json
{
  "result_id": "emb_550e8400-e29b-41d4-a716-446655440000",
  "document_id": "doc_123",
  "chunking_result_id": "chunk_456",
  "model": "bge-m3",
  "status": "PARTIAL_SUCCESS",
  "successful_count": 48,
  "failed_count": 2,
  "vector_dimension": 1024,
  "json_file_path": "embedding/doc_123_20251217_104532.json",
  "processing_time_ms": 15230.8,
  "created_at": "2025-12-17T10:45:32Z",
  "error_message": "2 chunks failed to vectorize",
  "failures": [
    {
      "chunk_index": 15,
      "error_type": "RATE_LIMIT_ERROR",
      "error_message": "Rate limit exceeded, retry after 30s",
      "retry_recommended": true
    },
    {
      "chunk_index": 32,
      "error_type": "INVALID_TEXT_ERROR",
      "error_message": "Text contains invalid UTF-8 sequences",
      "retry_recommended": false
    }
  ]
}
```

---

### 6. EmbeddingQueryResponse (Query API Response Entity)

**Purpose**: Return query results for embedding history

**Schema**:
```python
{
  "results": [EmbeddingResponse],
  "total_count": int,
  "page": int,
  "page_size": int,
  "total_pages": int
}
```

**Example**:
```json
{
  "results": [
    {
      "result_id": "emb_123",
      "document_id": "doc_456",
      "model": "qwen3-embedding-8b",
      "status": "SUCCESS",
      "successful_count": 50,
      "failed_count": 0,
      "vector_dimension": 4096,
      "created_at": "2025-12-17T10:30:45Z"
    }
  ],
  "total_count": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

### 7. DocumentSelectionState (Frontend State Entity)

**Purpose**: Track UI state for document embedding page

**Schema** (Pinia Store):
```typescript
{
  selectedDocument: {
    document_id: string,
    name: string,
    chunking_status: 'chunked',
    chunking_date: string  // YYYY-MM-DD
  } | null,
  
  selectedModel: string,  // Model name
  
  currentResult: {
    result_id: string,
    document_id: string,
    model: string,
    status: 'SUCCESS' | 'FAILED' | 'PARTIAL_SUCCESS',
    successful_count: number,
    failed_count: number,
    vector_dimension: number,
    processing_time_ms: number,
    created_at: string,
    vectors: Array<{
      chunk_index: number,
      vector: number[],
      text_length: number
    }>
  } | null,
  
  latestResults: {
    [document_id: string]: EmbeddingResult
  },
  
  isLoading: boolean,
  error: string | null
}
```

---

## Entity Relationships

```
┌─────────────────────┐
│   documents         │
│                     │
│ PK: document_id     │
└──────────┬──────────┘
           │
           │ 1
           │
           │
           │ N
┌──────────┴──────────┐
│ chunking_results    │
│                     │
│ PK: result_id       │
│ FK: document_id     │
└──────────┬──────────┘
           │
           │ 1
           │
           │
           │ N
┌──────────┴──────────┐
│ embedding_results   │
│                     │
│ PK: result_id       │
│ FK: document_id     │
│ FK: chunking_result_id │
│                     │
│ Related Files:      │
│ - JSON vector files │
└─────────────────────┘
```

**Relationship Rules**:
- One document can have many chunking results (1:N)
- One chunking result can have many embedding results (1:N)
- One document can have many embedding results (1:N, via chunking results)
- Each embedding result references exactly one JSON file (1:1)
- When document is deleted, cascade delete chunking results and embedding results
- When chunking result is deleted, cascade delete embedding results
- JSON files are NOT automatically deleted (manual cleanup process)

---

## State Transitions

### EmbeddingResult Status State Machine

```
                    ┌─────────────┐
                    │   [START]   │
                    └──────┬──────┘
                           │
                           │ Begin vectorization
                           │
                    ┌──────▼──────┐
              ┌────▶│  PROCESSING │◀────┐
              │     └──────┬──────┘     │
              │            │            │
              │            │            │
    API retry │            │            │ Continue on error
              │            │            │
              │     ┌──────▼──────────┐ │
              │     │ All chunks pass │ │
              │     └──────┬──────────┘ │
              │            │            │
              │            │            │
              │     ┌──────▼──────────┐ │
              │     │    SUCCESS      │ │
              │     │ failed_count=0  │ │
              │     └─────────────────┘ │
              │                         │
              │     ┌─────────────────┐ │
              │     │ Some chunks fail│ │
              └─────┤ but some pass   ├─┘
                    └──────┬──────────┘
                           │
                           │
                    ┌──────▼──────────┐
                    │ PARTIAL_SUCCESS │
                    │ failed_count>0  │
                    │ success_count>0 │
                    └─────────────────┘
                    
                    ┌─────────────────┐
                    │  All chunks fail│
                    └──────┬──────────┘
                           │
                           │
                    ┌──────▼──────────┐
                    │     FAILED      │
                    │ success_count=0 │
                    └─────────────────┘
```

**Transition Rules**:
- PROCESSING → SUCCESS: When all chunks vectorized successfully
- PROCESSING → PARTIAL_SUCCESS: When some chunks fail but at least one succeeds
- PROCESSING → FAILED: When all chunks fail (after retries exhausted)
- FAILED/PARTIAL_SUCCESS: Terminal states (no further transitions)
- Re-vectorization creates new EmbeddingResult record (does not modify existing)

---

## Validation Rules Summary

### Database Constraints

```sql
-- Enforce status consistency
CHECK (
  (status = 'SUCCESS' AND failed_count = 0) OR
  (status = 'FAILED' AND successful_count = 0) OR
  (status = 'PARTIAL_SUCCESS' AND successful_count > 0 AND failed_count > 0)
)

-- Enforce at least one chunk processed
CHECK (successful_count + failed_count > 0)

-- Enforce valid model names
CHECK (model IN ('bge-m3', 'qwen3-embedding-8b', 'qwen3-vl-embedding-8b'))

-- Enforce valid status values
CHECK (status IN ('SUCCESS', 'FAILED', 'PARTIAL_SUCCESS'))

-- Enforce valid dimensions (text models: 1024/4096, multimodal: 64-4096)
CHECK (vector_dimension >= 64 AND vector_dimension <= 4096)
```

### Application-Level Validation

**Pre-Vectorization**:
- Validate chunking result exists and is COMPLETED
- Validate document has active chunking results
- Validate model name is supported
- Validate batch size <= 1000

**Post-Vectorization**:
- Validate all vectors have same dimension
- Validate dimension matches model specification
- Validate JSON file was written successfully
- Validate database record was created

**Query Validation**:
- Validate result_id exists before querying
- Validate pagination parameters (page >= 1, page_size <= 100)
- Validate date range format (ISO8601)
- Validate status filter value

---

## Data Migration Plan

### Migration Script

**File**: `backend/migrations/create_embedding_results_table.py`

**Execution Order**: After chunking_results table exists

**Forward Migration**:
```sql
CREATE TABLE IF NOT EXISTS embedding_results (
    result_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunking_result_id TEXT NOT NULL,
    model TEXT NOT NULL,
    status TEXT NOT NULL,
    successful_count INTEGER NOT NULL,
    failed_count INTEGER NOT NULL,
    vector_dimension INTEGER NOT NULL,
    json_file_path TEXT NOT NULL,
    processing_time_ms REAL NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE,
    FOREIGN KEY (chunking_result_id) REFERENCES chunking_results(result_id) ON DELETE CASCADE,
    
    CHECK (
        (status = 'SUCCESS' AND failed_count = 0) OR
        (status = 'FAILED' AND successful_count = 0) OR
        (status = 'PARTIAL_SUCCESS' AND successful_count > 0 AND failed_count > 0)
    ),
    
    CHECK (successful_count + failed_count > 0),
    CHECK (model IN ('bge-m3', 'qwen3-embedding-8b', 'qwen3-vl-embedding-8b')),
    CHECK (status IN ('SUCCESS', 'FAILED', 'PARTIAL_SUCCESS')),
    CHECK (vector_dimension >= 64 AND vector_dimension <= 4096)
);

CREATE INDEX IF NOT EXISTS idx_embedding_doc_model 
ON embedding_results(document_id, model);

CREATE INDEX IF NOT EXISTS idx_embedding_created_at 
ON embedding_results(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_embedding_status 
ON embedding_results(status);
```

**Backward Migration**:
```sql
DROP INDEX IF EXISTS idx_embedding_status;
DROP INDEX IF EXISTS idx_embedding_created_at;
DROP INDEX IF EXISTS idx_embedding_doc_model;
DROP TABLE IF EXISTS embedding_results;
```

---

## References

- Feature Specification: `specs/003-vector-embedding/spec.md`
- Research Document: `specs/003-vector-embedding/research.md`
- Existing Models:
  - `backend/src/models/chunking_result.py`
  - `backend/src/models/document.py`

---

**Status**: ✅ Data model complete. Ready for contract generation.
