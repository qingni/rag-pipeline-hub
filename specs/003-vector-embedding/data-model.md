# Data Model: Vector Embedding Module

**Feature**: 003-vector-embedding  
**Date**: 2025-12-10  
**Phase**: 1 - Design & Contracts

## Overview

This document defines the data entities, validation rules, and state transitions for the Vector Embedding Module. All entities are extracted from functional requirements in the feature specification.

---

## Core Entities

### 1. EmbeddingModel

**Description**: Configuration for a specific embedding model provider

**Attributes**:
- `name` (string, required): Model identifier (e.g., "qwen3-embedding-8b")
- `dimension` (integer, required): Vector dimension size (768, 1024, or 1536)
- `description` (string, required): Human-readable model description
- `provider` (string, required): Provider name (e.g., "qwen", "bge", "hunyuan", "jina")
- `max_batch_size` (integer, optional): Provider-specific batch limit (default: 1000)
- `supports_multilingual` (boolean, optional): Multilingual support flag

**Validation Rules**:
- `name` must match pattern: `^[a-z0-9\-]+$`
- `dimension` must be one of: [768, 1024, 1536]
- `description` must be non-empty string
- `max_batch_size` must be positive integer ≤ 1000

**Supported Models**:
```python
EMBEDDING_MODELS = {
    "bge-m3": {
        "name": "bge-m3",
        "dimension": 1024,
        "description": "BGE-M3 多语言模型,支持中英文,性能优秀",
        "provider": "bge",
        "supports_multilingual": True
    },
    "qwen3-embedding-8b": {
        "name": "qwen3-embedding-8b",
        "dimension": 1536,
        "description": "通义千问 Embedding 模型,8B 参数",
        "provider": "qwen",
        "supports_multilingual": True
    },
    "hunyuan-embedding": {
        "name": "hunyuan-embedding",
        "dimension": 1024,
        "description": "腾讯混元 Embedding 模型",
        "provider": "hunyuan",
        "supports_multilingual": True
    },
    "jina-embeddings-v4": {
        "name": "jina-embeddings-v4",
        "dimension": 768,
        "description": "Jina AI Embeddings v4,多语言支持",
        "provider": "jina",
        "supports_multilingual": True
    }
}
```

---

### 2. EmbeddingRequest

**Description**: Request to vectorize single or multiple texts

**Attributes**:
- `request_id` (UUID, required): Unique request identifier (auto-generated)
- `texts` (list[string], required): Text(s) to vectorize (1-1000 items)
- `model` (string, required): Model name from EMBEDDING_MODELS
- `api_key` (string, required): API authentication key
- `base_url` (string, optional): API endpoint URL (default: from config)
- `max_retries` (integer, optional): Maximum retry attempts (default: 3)
- `timeout` (integer, optional): Request timeout in seconds (default: 60)
- `timestamp` (datetime, required): Request creation time (auto-generated)

**Validation Rules**:
- `texts` must be non-empty list with 1 ≤ length ≤ 1000
- Each text must be non-null string
- Empty strings are invalid (must contain non-whitespace)
- `model` must exist in EMBEDDING_MODELS
- `max_retries` must be 0 ≤ value ≤ 10
- `timeout` must be 1 ≤ value ≤ 300 seconds

**State Transitions**:
```
CREATED → VALIDATING → PROCESSING → [COMPLETED | PARTIAL_SUCCESS | FAILED]
                ↓
            VALIDATION_FAILED
```

---

### 3. Vector

**Description**: Numerical representation of text

**Attributes**:
- `index` (integer, required): Position in batch (0-based)
- `vector` (list[float], required): Vector values
- `dimension` (integer, required): Vector length (must match model)
- `text_hash` (string, optional): SHA256 hash of source text
- `text_length` (integer, required): Character count of source text
- `processing_time_ms` (float, optional): Time to generate this vector

**Validation Rules**:
- `vector` length must equal model's expected dimension
- All vector values must be finite floats (no NaN, Infinity)
- `dimension` must match model configuration
- `text_hash` format: `sha256:{64-char-hex}`
- `text_length` must be positive integer

**Relationships**:
- Belongs to EmbeddingResponse
- References EmbeddingModel (via dimension)

---

### 4. EmbeddingResponse

**Description**: Result of vectorization request (success or partial)

**Attributes**:
- `request_id` (UUID, required): Matches EmbeddingRequest
- `status` (enum, required): Response status
  - `SUCCESS`: All texts vectorized
  - `PARTIAL_SUCCESS`: Some texts failed
  - `FAILED`: Complete failure
- `vectors` (list[Vector], required): Successfully generated vectors
- `failures` (list[EmbeddingFailure], optional): Failed text details
- `metadata` (EmbeddingMetadata, required): Processing metadata
- `timestamp` (datetime, required): Response completion time

**Validation Rules**:
- If `status == SUCCESS`: `failures` must be empty
- If `status == PARTIAL_SUCCESS`: both `vectors` and `failures` must be non-empty
- If `status == FAILED`: `vectors` must be empty
- Total count: `len(vectors) + len(failures)` must equal original batch size

**Relationships**:
- Corresponds to one EmbeddingRequest
- Contains multiple Vector entities
- Contains multiple EmbeddingFailure entities (if partial)
- Contains one EmbeddingMetadata entity

---

### 5. EmbeddingFailure

**Description**: Details of a failed text vectorization

**Attributes**:
- `index` (integer, required): Position in original batch
- `text_preview` (string, optional): First 50 chars of failed text
- `error_type` (enum, required): Error classification
  - `INVALID_TEXT_ERROR`: Empty or malformed text
  - `API_TIMEOUT_ERROR`: Request timeout
  - `RATE_LIMIT_ERROR`: API rate limiting
  - `NETWORK_ERROR`: Connection failure
  - `AUTHENTICATION_ERROR`: Invalid credentials
  - `DIMENSION_MISMATCH_ERROR`: Wrong vector size
  - `UNKNOWN_ERROR`: Unclassified error
- `error_message` (string, required): Human-readable error description
- `retry_recommended` (boolean, required): Whether retry likely to succeed
- `retry_count` (integer, required): Number of retry attempts made

**Validation Rules**:
- `index` must be valid batch position (0 ≤ index < batch_size)
- `error_message` must be non-empty string
- `retry_count` must be non-negative integer
- If `retry_recommended == True`: error_type must be retryable

**Retryable Error Types**:
- `RATE_LIMIT_ERROR`: Yes
- `API_TIMEOUT_ERROR`: Yes
- `NETWORK_ERROR`: Yes
- `AUTHENTICATION_ERROR`: No
- `INVALID_TEXT_ERROR`: No
- `DIMENSION_MISMATCH_ERROR`: No

---

### 6. EmbeddingMetadata

**Description**: Processing statistics and configuration

**Attributes**:
- `model` (string, required): Model name used
- `model_dimension` (integer, required): Expected vector dimension
- `batch_size` (integer, required): Total texts in request
- `successful_count` (integer, required): Successfully vectorized count
- `failed_count` (integer, required): Failed vectorization count
- `processing_time_ms` (float, required): Total processing duration
- `api_latency_ms` (float, optional): API round-trip time
- `retry_count` (integer, required): Total retry attempts
- `rate_limit_hits` (integer, required): Number of rate limit encounters
- `vectors_per_second` (float, optional): Throughput metric (successful_count / processing_time_seconds)
- `config` (EmbeddingConfig, required): Request configuration

**Validation Rules**:
- `batch_size == successful_count + failed_count`
- `processing_time_ms` must be positive float
- `retry_count` must be non-negative integer
- All counts must be non-negative integers

---

### 7. EmbeddingConfig

**Description**: Configuration snapshot for reproducibility

**Attributes**:
- `api_endpoint` (string, required): Full API URL
- `max_retries` (integer, required): Retry limit
- `timeout_seconds` (integer, required): Request timeout
- `exponential_backoff` (boolean, required): Backoff enabled flag
- `initial_delay_seconds` (float, required): First retry delay
- `max_delay_seconds` (float, required): Maximum retry delay

**Validation Rules**:
- `api_endpoint` must be valid HTTP(S) URL
- `max_retries` must be 0 ≤ value ≤ 10
- `timeout_seconds` must be positive integer
- `initial_delay_seconds` must be positive float
- `max_delay_seconds` must be ≥ initial_delay_seconds

---

## Persistence Schema

### JSON File Format

**File Naming**: `embedding_{request_id}_{timestamp}.json`

**Directory Structure**:
```
results/embedding/
├── 2025-12-10/
│   ├── embedding_abc123_20251210_103045.json
│   ├── embedding_def456_20251210_103120.json
│   └── ...
└── 2025-12-11/
    └── ...
```

**JSON Schema**:
```json
{
  "request_id": "uuid-v4",
  "status": "SUCCESS|PARTIAL_SUCCESS|FAILED",
  "timestamp": "ISO8601-datetime",
  "metadata": {
    "model": "string",
    "model_dimension": "integer",
    "batch_size": "integer",
    "successful_count": "integer",
    "failed_count": "integer",
    "processing_time_ms": "float",
    "api_latency_ms": "float",
    "retry_count": "integer",
    "rate_limit_hits": "integer",
    "config": {
      "api_endpoint": "string",
      "max_retries": "integer",
      "timeout_seconds": "integer",
      "exponential_backoff": "boolean",
      "initial_delay_seconds": "float",
      "max_delay_seconds": "float"
    }
  },
  "vectors": [
    {
      "index": "integer",
      "vector": ["float[]"],
      "dimension": "integer",
      "text_hash": "string",
      "text_length": "integer",
      "processing_time_ms": "float"
    }
  ],
  "failures": [
    {
      "index": "integer",
      "text_preview": "string",
      "error_type": "string",
      "error_message": "string",
      "retry_recommended": "boolean",
      "retry_count": "integer"
    }
  ]
}
```

---

## Database Schema (Optional - Metadata Tracking)

### Table: embedding_requests

**Purpose**: Track request history and statistics

```sql
CREATE TABLE embedding_requests (
    request_id UUID PRIMARY KEY,
    model VARCHAR(50) NOT NULL,
    batch_size INTEGER NOT NULL,
    successful_count INTEGER NOT NULL,
    failed_count INTEGER NOT NULL,
    processing_time_ms FLOAT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    rate_limit_hits INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    result_file_path VARCHAR(500),
    CONSTRAINT status_check CHECK (status IN ('SUCCESS', 'PARTIAL_SUCCESS', 'FAILED'))
);

CREATE INDEX idx_model ON embedding_requests(model);
CREATE INDEX idx_created_at ON embedding_requests(created_at);
CREATE INDEX idx_status ON embedding_requests(status);
```

### Table: embedding_failures

**Purpose**: Track failure patterns for diagnostics

```sql
CREATE TABLE embedding_failures (
    id SERIAL PRIMARY KEY,
    request_id UUID REFERENCES embedding_requests(request_id),
    batch_index INTEGER NOT NULL,
    error_type VARCHAR(50) NOT NULL,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_request_id ON embedding_failures(request_id);
CREATE INDEX idx_error_type ON embedding_failures(error_type);
```

---

## State Machine

### EmbeddingRequest Lifecycle

```
┌─────────┐
│ CREATED │ (Initial state)
└────┬────┘
     │
     ▼
┌────────────┐
│ VALIDATING │ (Check batch size, model, texts)
└──┬─────┬───┘
   │     │
   │     └─────────────┐
   │                   ▼
   │            ┌──────────────────┐
   │            │ VALIDATION_FAILED │ (Terminal)
   │            └──────────────────┘
   │
   ▼
┌────────────┐
│ PROCESSING │ (Calling API, retrying)
└──┬─────┬───┘
   │     │
   │     └──────────────┐
   │                    │
   ▼                    ▼
┌───────────┐    ┌─────────────────┐
│ COMPLETED │    │ PARTIAL_SUCCESS │ (Terminal states)
└───────────┘    └─────────────────┘
                        │
                        ▼
                 ┌────────┐
                 │ FAILED │ (Terminal)
                 └────────┘
```

### State Descriptions

- **CREATED**: Request object instantiated, not yet validated
- **VALIDATING**: Checking batch size, model name, text validity
- **VALIDATION_FAILED**: Invalid input detected (terminal state)
- **PROCESSING**: API calls in progress, retries happening
- **COMPLETED**: All texts successfully vectorized (terminal state)
- **PARTIAL_SUCCESS**: Some texts vectorized, some failed (terminal state)
- **FAILED**: No texts vectorized successfully (terminal state)

---

## Validation Summary

| Entity | Key Validations |
|--------|----------------|
| EmbeddingModel | Name pattern, dimension enum, non-empty description |
| EmbeddingRequest | 1-1000 texts, valid model, timeout/retry bounds |
| Vector | Dimension match, finite floats, positive text_length |
| EmbeddingResponse | Status consistency (vectors/failures match status) |
| EmbeddingFailure | Valid index, non-empty message, retry flag consistency |
| EmbeddingMetadata | Count arithmetic (batch = success + failed) |
| EmbeddingConfig | Valid URL, positive timeouts, delay ordering |

All validation rules align with functional requirements (FR-001 through FR-014) and clarification decisions.
