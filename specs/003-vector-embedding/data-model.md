# Data Model: Vector Embedding Module

**Feature**: 003-vector-embedding  
**Date**: 2025-12-16  
**Source**: Extracted from spec.md Requirements and research.md decisions

---

## 1. Database Schema

### EmbeddingResult Table

**Purpose**: Store metadata for vectorization operations with source traceability and query optimization.

**Schema**:
```sql
CREATE TABLE embedding_results (
    -- Identity
    result_id TEXT PRIMARY KEY,          -- UUID v4 format
    
    -- Source Traceability
    document_id TEXT NOT NULL,           -- Reference to documents table
    chunking_result_id TEXT,             -- Reference to chunking_results (NULL for ad-hoc text)
    
    -- Model Configuration
    model TEXT NOT NULL,                 -- One of: bge-m3, qwen3-embedding-8b, hunyuan-embedding, jina-embeddings-v4
    vector_dimension INTEGER NOT NULL,   -- Model-specific: 1024, 4096, 1024, 2048
    
    -- Processing Status
    status TEXT NOT NULL,                -- One of: SUCCESS, FAILED, PARTIAL_SUCCESS
    successful_count INTEGER DEFAULT 0,  -- Number of successfully vectorized chunks
    failed_count INTEGER DEFAULT 0,      -- Number of failed chunks
    
    -- Storage Reference
    json_file_path TEXT NOT NULL,        -- Relative path: embedding/YYYY-MM-DD/embedding_{request_id}_{timestamp}.json
    
    -- Performance Metrics
    processing_time_ms REAL,             -- Total vectorization time in milliseconds
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Error Tracking
    error_message TEXT,                  -- Detailed error for FAILED or PARTIAL_SUCCESS status
    
    -- Constraints
    CHECK (status IN ('SUCCESS', 'FAILED', 'PARTIAL_SUCCESS')),
    CHECK (model IN ('bge-m3', 'qwen3-embedding-8b', 'hunyuan-embedding', 'jina-embeddings-v4')),
    CHECK (successful_count >= 0),
    CHECK (failed_count >= 0),
    CHECK (vector_dimension > 0)
);

-- Indexes (from FR-028)
CREATE INDEX idx_doc_model ON embedding_results(document_id, model);
CREATE INDEX idx_created_at ON embedding_results(created_at DESC);
CREATE INDEX idx_status ON embedding_results(status);
```

**Field Descriptions**:

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `result_id` | TEXT | NO | Unique identifier (UUID v4) for this embedding operation |
| `document_id` | TEXT | NO | Foreign key to source document |
| `chunking_result_id` | TEXT | YES | Foreign key to chunking result (NULL for ad-hoc text vectorization) |
| `model` | TEXT | NO | Embedding model name (validated against EMBEDDING_MODELS) |
| `vector_dimension` | INTEGER | NO | Actual dimension of generated vectors |
| `status` | TEXT | NO | Processing outcome (SUCCESS/FAILED/PARTIAL_SUCCESS) |
| `successful_count` | INTEGER | NO | Count of chunks successfully vectorized |
| `failed_count` | INTEGER | NO | Count of chunks that failed vectorization |
| `json_file_path` | TEXT | NO | Relative path to JSON file containing vector data |
| `processing_time_ms` | REAL | YES | Total processing duration in milliseconds |
| `created_at` | TIMESTAMP | NO | Record creation timestamp (UTC) |
| `error_message` | TEXT | YES | Error details for failed operations |

**Validation Rules** (from Spec Requirements):
- `model` must match one of four supported models (FR-006)
- `vector_dimension` must match model's expected dimension (FR-014)
- `status='SUCCESS'` requires `successful_count > 0` and `failed_count = 0`
- `status='PARTIAL_SUCCESS'` requires `successful_count > 0` and `failed_count > 0`
- `status='FAILED'` requires `successful_count = 0` and `error_message IS NOT NULL`
- `json_file_path` must be relative path from configured results directory (FR-023)

---

## 2. JSON Vector Data Format

### File Naming Convention
**Pattern**: `embedding_{request_id}_{timestamp}.json`  
**Example**: `embedding_a3b7c9f2-4e5d-6789-abcd-ef0123456789_20251216_143052.json`

**Directory Structure**:
```
results/
└── embedding/
    └── 2025-12-16/
        ├── embedding_a3b7c9f2_20251216_143052.json
        └── embedding_b8d4e1a3_20251216_150125.json
```

### JSON Schema
```json
{
  "request_id": "a3b7c9f2-4e5d-6789-abcd-ef0123456789",
  "document_id": "doc-123",
  "chunking_result_id": "chunk-456",
  "model": "qwen3-embedding-8b",
  "status": "SUCCESS",
  "metadata": {
    "total_chunks": 50,
    "successful_count": 50,
    "failed_count": 0,
    "vector_dimension": 4096,
    "processing_time_ms": 8234.5,
    "created_at": "2025-12-16T14:30:52Z"
  },
  "vectors": [
    {
      "index": 0,
      "chunk_text": "First chunk content...",
      "vector": [0.1234, -0.5678, 0.9012, ...],  // 4096 floats
      "dimension": 4096,
      "text_length": 256,
      "processing_time_ms": 164.7
    },
    {
      "index": 1,
      "chunk_text": "Second chunk content...",
      "vector": [0.3456, 0.7890, -0.2345, ...],
      "dimension": 4096,
      "text_length": 312,
      "processing_time_ms": 175.2
    }
    // ... 48 more vectors
  ],
  "failures": []  // Empty for SUCCESS status
}
```

**For PARTIAL_SUCCESS Status**:
```json
{
  "status": "PARTIAL_SUCCESS",
  "metadata": {
    "successful_count": 48,
    "failed_count": 2
  },
  "vectors": [ /* 48 successful vectors */ ],
  "failures": [
    {
      "index": 15,
      "chunk_text": "Problematic chunk...",
      "error": "API timeout after 60 seconds",
      "error_code": "TIMEOUT"
    },
    {
      "index": 32,
      "chunk_text": "Another failed chunk...",
      "error": "Empty text after preprocessing",
      "error_code": "EMPTY_TEXT"
    }
  ]
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `request_id` | string | Matches database `result_id` |
| `document_id` | string | Source document identifier |
| `chunking_result_id` | string \| null | Source chunking result (null for ad-hoc text) |
| `model` | string | Embedding model used |
| `status` | string | SUCCESS \| FAILED \| PARTIAL_SUCCESS |
| `metadata.total_chunks` | integer | Total chunks attempted |
| `metadata.successful_count` | integer | Successfully vectorized chunks |
| `metadata.failed_count` | integer | Failed chunks count |
| `metadata.vector_dimension` | integer | Dimension of vectors |
| `metadata.processing_time_ms` | float | Total processing time |
| `vectors[].index` | integer | Original chunk index (0-based) |
| `vectors[].chunk_text` | string | Original text chunk (for traceability) |
| `vectors[].vector` | float[] | Embedding vector (dimension matches model) |
| `vectors[].dimension` | integer | Actual dimension (validation) |
| `vectors[].text_length` | integer | Character count of chunk |
| `vectors[].processing_time_ms` | float | Time to vectorize this chunk |
| `failures[].index` | integer | Failed chunk index |
| `failures[].chunk_text` | string | Failed chunk text |
| `failures[].error` | string | Human-readable error message |
| `failures[].error_code` | string | Machine-readable error code |

---

## 3. API Request/Response Models

### VectorizationRequest (Chunking-based)

**Endpoint**: `POST /embedding/from-chunking-result`

```python
class VectorizationFromChunkingRequest(BaseModel):
    chunking_result_id: str = Field(..., description="ID of completed chunking result")
    model: str = Field(..., description="Embedding model name")
    
    @validator('model')
    def validate_model(cls, v):
        valid_models = ['bge-m3', 'qwen3-embedding-8b', 'hunyuan-embedding', 'jina-embeddings-v4']
        if v not in valid_models:
            raise ValueError(f"Invalid model. Must be one of {valid_models}")
        return v
```

### VectorizationRequest (Document-based)

**Endpoint**: `POST /embedding/from-document`

```python
class VectorizationFromDocumentRequest(BaseModel):
    document_id: str = Field(..., description="Document ID")
    model: str = Field(..., description="Embedding model name")
    strategy: Optional[str] = Field(None, description="Filter by chunking strategy (optional)")
    
    @validator('model')
    def validate_model(cls, v):
        # Same validation as above
        pass
    
    @validator('strategy')
    def validate_strategy(cls, v):
        if v is not None:
            valid_strategies = ['fixed_size', 'semantic', 'recursive', 'markdown', 'sentence', 'paragraph']
            if v not in valid_strategies:
                raise ValueError(f"Invalid strategy. Must be one of {valid_strategies}")
        return v
```

### VectorizationResponse

```python
class VectorResult(BaseModel):
    index: int
    chunk_text: str
    vector: List[float]
    dimension: int
    text_length: int
    processing_time_ms: float

class FailureInfo(BaseModel):
    index: int
    chunk_text: str
    error: str
    error_code: str

class VectorizationResponse(BaseModel):
    request_id: str
    document_id: str
    chunking_result_id: Optional[str]
    model: str
    status: Literal['SUCCESS', 'FAILED', 'PARTIAL_SUCCESS']
    metadata: Dict[str, Any]  # Contains total_chunks, counts, timing, etc.
    vectors: List[VectorResult]
    failures: List[FailureInfo]
    json_file_path: str  # Where vectors are persisted
```

### Query Requests/Responses

**Endpoint**: `GET /embedding/results/{result_id}`

```python
class EmbeddingResultDetail(BaseModel):
    result_id: str
    document_id: str
    chunking_result_id: Optional[str]
    model: str
    status: str
    successful_count: int
    failed_count: int
    vector_dimension: int
    json_file_path: str
    processing_time_ms: Optional[float]
    created_at: datetime
    error_message: Optional[str]
```

**Endpoint**: `GET /embedding/results/by-document/{document_id}?model=xxx`

```python
class LatestEmbeddingQuery(BaseModel):
    document_id: str
    model: Optional[str] = None  # Filter by model if provided

# Response: EmbeddingResultDetail (latest by created_at DESC)
```

**Endpoint**: `GET /embedding/results?page=1&page_size=20&status=SUCCESS&date_from=2025-12-15`

```python
class EmbeddingResultListQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    document_id: Optional[str] = None
    model: Optional[str] = None
    status: Optional[Literal['SUCCESS', 'FAILED', 'PARTIAL_SUCCESS']] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

class EmbeddingResultListResponse(BaseModel):
    results: List[EmbeddingResultDetail]
    pagination: Dict[str, Any]  # total_count, total_pages, current_page, page_size
```

---

## 4. Entity Relationships

```
┌─────────────────┐
│   Documents     │
│  (external)     │
└────────┬────────┘
         │ 1
         │
         │ N
┌────────▼────────────┐
│ ChunkingResults     │
│  (external)         │
└────────┬────────────┘
         │ 1
         │
         │ N
┌────────▼────────────┐         ┌──────────────────┐
│ EmbeddingResults    │────────▶│ JSON Vector File │
│   (database)        │ 1    1  │  (file system)   │
└─────────────────────┘         └──────────────────┘

Relationship: embedding_results.json_file_path → vector JSON file
Constraint: Delete cascade NOT implemented (preserve historical JSON files per FR-024)
```

**Foreign Key Relationships**:
- `embedding_results.document_id` → `documents.id` (implicit, not enforced by FK constraint)
- `embedding_results.chunking_result_id` → `chunking_results.id` (implicit, not enforced)
- `embedding_results.json_file_path` → physical JSON file (enforced by dual-write transaction)

**Cardinality**:
- One document → Many chunking results → Many embedding results
- One chunking result → Many embedding results (different models)
- One embedding result → One JSON file (1:1 enforced by dual-write)

**Concurrency Control (NFR-003)**:
- Row-level locks (`SELECT ... FOR UPDATE`) prevent race conditions when multiple requests update same document+model
- Transaction isolation ensures atomic dual-write operations (JSON file + database record)
- Optimistic locking alternative considered but rejected (see research.md Section 8)

---

## 5. State Transitions

### Embedding Result Status Lifecycle

```
       ┌──────────────┐
       │   CREATED    │ (transient state, not persisted)
       └──────┬───────┘
              │
              ▼
       ┌──────────────┐
       │  PROCESSING  │ (transient state, in-memory only)
       └──────┬───────┘
              │
       ┌──────┴──────┬────────────────┐
       │             │                │
       ▼             ▼                ▼
┌─────────────┐ ┌────────────┐ ┌──────────────┐
│   SUCCESS   │ │   FAILED   │ │PARTIAL_SUCCESS│
│ (terminal)  │ │ (terminal) │ │  (terminal)   │
└─────────────┘ └────────────┘ └──────────────┘

Terminal states are persisted to database.
```

**Transition Rules**:
- `PROCESSING → SUCCESS`: All chunks vectorized successfully
- `PROCESSING → FAILED`: All chunks failed OR critical error (API auth, timeout)
- `PROCESSING → PARTIAL_SUCCESS`: Some chunks succeeded, some failed (per FR-001 batch handling)
- Once in terminal state, status never changes (re-vectorization creates new record per FR-024)

**Success Criteria**:
- `SUCCESS`: `successful_count == total_chunks`, `failed_count == 0`
- `FAILED`: `successful_count == 0`, `error_message != NULL`
- `PARTIAL_SUCCESS`: `successful_count > 0 AND failed_count > 0`

---

## 6. Data Validation Rules

### Database-Level Constraints
1. **result_id**: Must be UUID v4 format (validated in application layer)
2. **model**: CHECK constraint enforces one of four valid models
3. **status**: CHECK constraint enforces three valid statuses
4. **vector_dimension**: Must match model's expected dimension (application validation)
5. **counts**: CHECK constraints ensure non-negative values
6. **json_file_path**: Must be relative path (application validation)

### Application-Level Validation
```python
def validate_embedding_result(result: EmbeddingResultCreate):
    # Model validation
    assert result.model in EMBEDDING_MODELS, "Invalid model"
    
    # Dimension validation
    expected_dim = EMBEDDING_MODELS[result.model]["dimension"]
    assert result.vector_dimension == expected_dim, f"Dimension mismatch: expected {expected_dim}"
    
    # Status consistency validation
    if result.status == "SUCCESS":
        assert result.successful_count > 0, "SUCCESS requires successful_count > 0"
        assert result.failed_count == 0, "SUCCESS requires failed_count == 0"
        assert result.error_message is None, "SUCCESS cannot have error_message"
    
    elif result.status == "FAILED":
        assert result.successful_count == 0, "FAILED requires successful_count == 0"
        assert result.error_message is not None, "FAILED requires error_message"
    
    elif result.status == "PARTIAL_SUCCESS":
        assert result.successful_count > 0, "PARTIAL_SUCCESS requires some success"
        assert result.failed_count > 0, "PARTIAL_SUCCESS requires some failures"
    
    # File path validation
    assert not os.path.isabs(result.json_file_path), "json_file_path must be relative"
    assert result.json_file_path.startswith("embedding/"), "Path must start with embedding/"


def save_embedding_with_concurrency_control(result_data: dict, session: Session):
    """
    NFR-003: Concurrent-safe save operation using row-level locking.
    Prevents race conditions when multiple requests update same document+model.
    """
    # Acquire row-level lock to prevent concurrent updates
    existing = session.execute(
        select(EmbeddingResult)
        .where(
            EmbeddingResult.document_id == result_data['document_id'],
            EmbeddingResult.model == result_data['model']
        )
        .with_for_update()  # Blocks concurrent transactions until commit
    ).scalar_one_or_none()
    
    # Proceed with create or update
    if existing:
        for key, value in result_data.items():
            setattr(existing, key, value)
        return existing
    else:
        new_record = EmbeddingResult(**result_data)
        session.add(new_record)
        return new_record
```

---

## 7. Performance Considerations

### Index Usage Analysis
**Query**: "Get latest embedding for document X with model Y"
```sql
SELECT * FROM embedding_results
WHERE document_id = 'doc-123' AND model = 'bge-m3'
ORDER BY created_at DESC
LIMIT 1;
```
**Index Used**: `idx_doc_model` (composite) + `idx_created_at` (sorting)  
**Expected Performance**: <10ms for 10k records

**Query**: "List all SUCCESS embeddings, paginated"
```sql
SELECT * FROM embedding_results
WHERE status = 'SUCCESS'
ORDER BY created_at DESC
LIMIT 20 OFFSET 40;
```
**Index Used**: `idx_status` + `idx_created_at`  
**Expected Performance**: <20ms for 10k records

### Data Growth Estimation
- Average embedding result: ~500 bytes (database row)
- Average JSON file: ~50KB for 50 chunks × 4096-dim vectors
- Expected growth: 1000 documents/month × 2 re-vectorizations = 2000 records/month
- Database size (1 year): 2000 × 12 × 500 bytes = ~12MB
- File storage (1 year): 2000 × 12 × 50KB = ~1.2GB

---

## Summary

| Entity | Storage | Purpose | Key Indexes |
|--------|---------|---------|-------------|
| `embedding_results` | SQLite table | Metadata + query optimization | (doc+model), created_at DESC, status |
| Vector JSON files | File system | High-dimensional vector data | N/A (accessed via path) |
| API Request/Response models | In-memory (Pydantic) | Type safety + validation | N/A |

**Critical Design Decisions**:
1. **Dual Storage**: Database for metadata (fast queries), JSON for vectors (storage efficiency)
2. **No Foreign Keys**: Implicit relationships to avoid cross-module coupling
3. **Composite Indexes**: Optimized for "latest embedding by document+model" pattern
4. **Immutable Records**: Re-vectorization creates new records (preserves history per FR-024)

**Next Phase**: API contract design (contracts/) and quickstart guide (quickstart.md)
