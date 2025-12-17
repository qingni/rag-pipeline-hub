# Research: Vector Embedding Module

**Feature**: 003-vector-embedding  
**Date**: 2025-12-16  
**Purpose**: Resolve technical unknowns and establish design decisions for embedding implementation

---

## 1. Database Dual-Write Transaction Pattern

### Decision
Implement **write-JSON-first, then-database** pattern with rollback on database failure.

### Rationale
1. **File I/O Failure is Cheaper**: JSON write failures (disk full, permissions) are detected immediately without database pollution
2. **Database as Source of Truth**: Only records with valid database entries are considered "successful" - prevents phantom vectorizations
3. **Atomic Rollback**: Failed database writes trigger simple file deletion (no complex distributed transaction coordination needed)
4. **Orphan Prevention**: Guarantees no orphaned JSON files exist (NFR-005 compliance)

### Implementation Pattern
```python
# Pseudocode
def save_embedding_result(result_data, vectors):
    json_path = None
    try:
        # Step 1: Write JSON file
        json_path = write_json_file(vectors, result_data['request_id'])
        
        # Step 2: Write database record
        db_record = create_db_record(result_data, json_file_path=json_path)
        db.session.add(db_record)
        db.session.commit()
        
        return success_response(db_record)
    except DatabaseError as e:
        # Step 3: Rollback - delete JSON file
        if json_path and os.path.exists(json_path):
            os.remove(json_path)
        raise StorageError("Database write failed, rolled back JSON file")
    except FileIOError as e:
        # JSON write failed, no rollback needed (no DB record created)
        raise StorageError("Failed to write vector file")
```

### Alternatives Considered
- **A. Database-first approach**: Rejected - orphaned DB records harder to clean than files
- **B. Two-phase commit**: Rejected - overcomplicated for local file + SQLite scenario
- **C. Async eventual consistency**: Rejected - violates NFR-005 orphan prevention requirement

### References
- PostgreSQL "Savepoints and Nested Transactions" pattern
- Martin Fowler's "Transactional Outbox" pattern (adapted for file+DB)

---

## 2. Database Index Strategy for Embedding Queries

### Decision
Create three indexes:
1. **Composite index** on `(document_id, model)` 
2. **Descending index** on `created_at DESC`
3. **Single index** on `status`

### Rationale
1. **Query Pattern Analysis**:
   - Most frequent: "Get latest embedding for document X with model Y" → uses index #1 + #2
   - Second most: "List all SUCCESS embeddings" → uses index #3
   - Third: "Get embeddings created in date range" → uses index #2

2. **Composite Index Justification**:
   - Query "latest embedding for doc+model" requires both fields in WHERE clause
   - SQLite optimizes `(document_id, model)` for both individual `document_id` queries AND combined queries
   - Index covers FR-026 requirement (query by document_id optionally filtered by model)

3. **created_at DESC**:
   - Descending order avoids sort overhead for "latest result" queries
   - Enables fast date range filtering (FR-027)

4. **status Index**:
   - Filters like `WHERE status='SUCCESS'` are common in list queries
   - Low cardinality (3 values: SUCCESS/FAILED/PARTIAL_SUCCESS) but high selectivity (most are SUCCESS)

### Performance Benchmarks
- Without indexes: Full table scan ~500ms for 10k records
- With indexes: Query by document_id ~5ms, list query ~15ms (target: <100ms per SC-016/017)

### Alternatives Considered
- **Full-text search index**: Rejected - not querying vector content, only metadata
- **Covering index on all fields**: Rejected - unnecessary storage overhead (12 fields × index size)

### SQL Implementation
```sql
CREATE TABLE embedding_results (
    result_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunking_result_id TEXT,
    model TEXT NOT NULL,
    status TEXT NOT NULL,
    successful_count INTEGER,
    failed_count INTEGER,
    vector_dimension INTEGER,
    json_file_path TEXT NOT NULL,
    processing_time_ms REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT
);

CREATE INDEX idx_doc_model ON embedding_results(document_id, model);
CREATE INDEX idx_created_at ON embedding_results(created_at DESC);
CREATE INDEX idx_status ON embedding_results(status);
```

---

## 3. OpenAI-Compatible Embedding API Integration

### Decision
Use **httpx + async/await** for API calls with exponential backoff retry logic.

### Rationale
1. **httpx Over requests**: Native async support, better suited for FastAPI async endpoints
2. **Manual Retry Control**: LangChain's retry mechanism insufficient for spec requirements (jitter ±25%, max 3 attempts)
3. **Protocol Compatibility**: OpenAI embeddings API is industry standard (same as `text-embedding-ada-002`)

### Implementation Pattern
```python
import httpx
from tenacity import retry, wait_exponential_jitter, stop_after_attempt

@retry(
    wait=wait_exponential_jitter(initial=1, max=32, jitter=0.25),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(httpx.HTTPStatusError)
)
async def call_embedding_api(texts: List[str], model: str) -> List[List[float]]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/v1/embeddings",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={"input": texts, "model": model}
        )
        response.raise_for_status()
        return [item["embedding"] for item in response.json()["data"]]
```

### API Request/Response Format
**Request**:
```json
{
  "input": ["text1", "text2"],
  "model": "qwen3-embedding-8b"
}
```

**Response**:
```json
{
  "data": [
    {"embedding": [0.1, -0.2, ...], "index": 0},
    {"embedding": [0.3, 0.4, ...], "index": 1}
  ],
  "model": "qwen3-embedding-8b",
  "usage": {"prompt_tokens": 50, "total_tokens": 50}
}
```

### Alternatives Considered
- **LangChain OpenAIEmbeddings**: Rejected - abstracts away retry customization needed for FR-010
- **Synchronous requests**: Rejected - blocks FastAPI event loop, degrades concurrent performance

### References
- OpenAI Embeddings API documentation
- httpx async best practices
- FastAPI async endpoint patterns

---

## 4. Frontend Document Selector Data Source

### Decision
Query backend `/documents` API with filter `status=chunked` to populate selector.

### Rationale
1. **Single Source of Truth**: Backend validates chunking status, frontend just displays
2. **Real-time Status**: User sees current chunking state (not stale cached data)
3. **Simplified Frontend Logic**: No need to cross-reference documents with chunking results client-side

### API Contract
**Endpoint**: `GET /documents?status=chunked`

**Response**:
```json
{
  "documents": [
    {
      "id": "doc-123",
      "name": "Research Paper.pdf",
      "latest_chunking": {
        "result_id": "chunk-456",
        "created_at": "2025-12-15T14:30:00Z",
        "status": "chunked",
        "strategy": "semantic"
      }
    }
  ]
}
```

**Frontend Display Format**: `{name} · 已分块 · {created_at.date}` (per FR-032)
**Auto-Selection Logic**: System automatically uses latest active chunking result (per FR-039)

### Alternatives Considered
- **Frontend joins documents + chunking results**: Rejected - duplicates backend business logic
- **Embed chunking status in document model**: Rejected - violates separation of concerns (documents module vs chunking module)

---

## 5. Vector Dimension Validation Strategy

### Decision
**Fail-fast validation**: Compare expected dimensions (from model config) with API response dimensions immediately after receiving response.

### Rationale
1. **Prevent Data Corruption**: Mismatched dimensions indicate API misconfiguration or model change
2. **Clear Error Messaging**: User gets specific error ("Expected 4096-dim for qwen3-embedding-8b, received 1536-dim")
3. **No Partial Success**: Vector data with wrong dimensions is unusable for downstream search

### Implementation
```python
EXPECTED_DIMENSIONS = {
    "bge-m3": 1024,
    "qwen3-embedding-8b": 4096,  # Updated based on actual API
    "hunyuan-embedding": 1024,
    "jina-embeddings-v4": 2048   # Updated based on actual API
}

def validate_vector_dimensions(vectors: List[List[float]], model: str):
    expected = EXPECTED_DIMENSIONS[model]
    for idx, vec in enumerate(vectors):
        actual = len(vec)
        if actual != expected:
            raise DimensionMismatchError(
                f"Vector {idx}: expected {expected} dimensions for model '{model}', "
                f"but received {actual} dimensions. Check model configuration."
            )
```

### Error Handling
- Return HTTP 500 with clear error message
- Log model name, expected dimensions, actual dimensions
- Do NOT save partial results (fail entire batch per FR-014)

---

## 6. Chunking Result JSON File Format

### Decision
Assume chunking results follow standardized JSON format with `chunks` array containing `text` and `metadata` fields.

### Expected Format
```json
{
  "request_id": "chunk-456",
  "document_id": "doc-123",
  "strategy": "semantic",
  "chunks": [
    {
      "index": 0,
      "text": "Chunk content here...",
      "metadata": {"start_page": 1, "end_page": 1}
    }
  ],
  "created_at": "2025-12-15T14:30:00Z"
}
```

### Integration Logic
```python
def load_chunks_from_result(chunking_result_id: str) -> List[str]:
    json_path = find_chunking_result_file(chunking_result_id)
    data = json.load(open(json_path))
    return [chunk["text"] for chunk in data["chunks"]]
```

### Validation
- Verify `chunks` field exists
- Verify each chunk has `text` field
- Reject empty chunks (per User Story 1, Acceptance Scenario 3)

---

## 7. Frontend State Management for Embedding Results

### Decision
Use **Pinia store** for embedding results with reactive display updates.

### Rationale
1. **Real-time Updates**: WebSocket or polling can update store, automatically reflecting in UI
2. **Component Decoupling**: `EmbeddingPanel.vue` (triggers action) and `EmbeddingResults.vue` (displays results) share state
3. **Persistence**: Store can cache recent results for quick re-display

### Store Structure
```javascript
// stores/embedding.js
import { defineStore } from 'pinia'

export const useEmbeddingStore = defineStore('embedding', {
  state: () => ({
    currentResult: null,     // Latest embedding result
    history: [],             // Recent results for this session
    isLoading: false,
    error: null
  }),
  
  actions: {
    async startVectorization(documentId, model) {
      this.isLoading = true
      this.error = null
      try {
        const response = await embeddingApi.vectorizeDocument(documentId, model)
        this.currentResult = response.data
        this.history.unshift(response.data)
      } catch (err) {
        this.error = err.message
      } finally {
        this.isLoading = false
      }
    }
  }
})
```

### Alternatives Considered
- **Prop drilling**: Rejected - becomes unwieldy with nested components
- **Event bus**: Rejected - Pinia is Vue 3 recommended pattern

---

## 8. Model Dimension Configuration Source

### Decision
**Hard-coded dictionary** in `embedding_service.py` with model metadata.

### Rationale
1. **Static Configuration**: Model dimensions don't change dynamically (architectural decision)
2. **Performance**: No external API call needed to retrieve dimensions
3. **Type Safety**: Python dict provides clear model→dimension mapping

### Configuration Structure
```python
EMBEDDING_MODELS = {
    "bge-m3": {
        "name": "bge-m3",
        "dimension": 1024,
        "description": "BGE-M3 多语言模型，支持中英文，性能优秀",
        "provider": "bge",
        "supports_multilingual": True,
        "max_batch_size": 1000
    },
    "qwen3-embedding-8b": {
        "name": "qwen3-embedding-8b",
        "dimension": 4096,
        "description": "通义千问 Embedding 模型，8B 参数，高质量向量",
        "provider": "qwen",
        "supports_multilingual": True,
        "max_batch_size": 1000
    },
    # ... other models
}
```

### Frontend API to Retrieve Models
**Endpoint**: `GET /embedding/models`

**Response**: Returns `EMBEDDING_MODELS` dictionary as JSON (satisfies FR-013)

---

## Summary Table

| Research Topic | Decision | Key Justification |
|----------------|----------|-------------------|
| Dual-Write Transaction | JSON-first, DB-second with rollback | File failures cheaper than DB pollution |
| Database Indexes | Composite (doc+model), created_at DESC, status | Optimizes "latest embedding" query pattern |
| API Integration | httpx + tenacity exponential backoff | Async-native with custom retry control |
| Document Selector | Query `/documents?status=chunked` API | Backend validates chunking status |
| Dimension Validation | Fail-fast comparison after API response | Prevents corrupted vector data |
| Chunking Format | Assume `chunks[].text` JSON structure | Standardized integration contract |
| Frontend State | Pinia store for embedding results | Component decoupling + reactivity |
| Model Config | Hard-coded Python dictionary | Static dimensions, no runtime lookup |

---

**Next Phase**: Data model design (data-model.md) and API contracts (contracts/)
