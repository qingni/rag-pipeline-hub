# Research & Technical Decisions: Vector Embedding Module

**Feature**: 003-vector-embedding  
**Date**: 2025-12-17  
**Status**: Complete

## Overview

This document consolidates research findings and technical decisions for implementing the vector embedding module. All unknowns from the Technical Context have been resolved through analysis of existing codebase, specification requirements, and best practices.

## Research Topics

### 1. Database Schema Design for Embedding Results

**Decision**: Use dedicated `embedding_results` table with composite indexes

**Rationale**:
- Metadata (result_id, status, timestamps, counts) stored in database for fast querying
- Large vector arrays (up to 4096 floats) stored in JSON files to avoid database bloat
- Composite index on `(document_id, model)` enables fast lookups for "get latest result by document+model"
- Index on `created_at DESC` supports "latest result" queries efficiently
- Index on `status` enables filtering by SUCCESS/FAILED/PARTIAL_SUCCESS

**Schema**:
```sql
CREATE TABLE embedding_results (
    result_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunking_result_id TEXT NOT NULL,
    model TEXT NOT NULL,
    status TEXT NOT NULL,  -- SUCCESS, FAILED, PARTIAL_SUCCESS
    successful_count INTEGER NOT NULL,
    failed_count INTEGER NOT NULL,
    vector_dimension INTEGER NOT NULL,
    json_file_path TEXT NOT NULL,  -- relative path from EMBEDDING_RESULTS_DIR
    processing_time_ms REAL NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (document_id) REFERENCES documents(document_id),
    FOREIGN KEY (chunking_result_id) REFERENCES chunking_results(result_id)
);

CREATE INDEX idx_embedding_doc_model ON embedding_results(document_id, model);
CREATE INDEX idx_embedding_created_at ON embedding_results(created_at DESC);
CREATE INDEX idx_embedding_status ON embedding_results(status);
```

**Alternatives Considered**:
- **Store vectors in database as BLOB**: Rejected - would cause table bloat, slow queries, difficult to version
- **Use NoSQL document store**: Rejected - adds new dependency, existing SQLite works well for metadata
- **Single index on document_id only**: Rejected - would require full table scan when filtering by model

---

### 2. Dual-Write Transaction Strategy

**Decision**: Write JSON file first, then database record; rollback (delete JSON) if DB write fails

**Rationale**:
- JSON file write is atomic at filesystem level (write to temp, then rename)
- Database write can fail due to constraints, locks, or disk space
- Orphaned JSON files are worse than missing DB records (harder to detect/cleanup)
- Rollback by deleting JSON file is simple and reliable
- This pattern ensures "no orphaned JSON files" guarantee (NFR-005)

**Implementation Pattern**:
```python
try:
    # Step 1: Write JSON file (atomic)
    json_path = write_vectors_to_json(vectors, document_id, model)
    
    try:
        # Step 2: Write database record
        db_record = create_embedding_result_record(
            document_id=document_id,
            json_file_path=json_path,
            ...
        )
        db.commit()
    except Exception as db_error:
        # Step 3: Rollback - delete JSON file
        os.remove(json_path)
        raise
except Exception:
    # Log error and re-raise
    raise
```

**Alternatives Considered**:
- **Database-first, then JSON**: Rejected - leaves DB records pointing to non-existent files on JSON failure
- **Two-phase commit protocol**: Rejected - overkill for single-node deployment, adds complexity
- **Write both in parallel**: Rejected - no way to guarantee atomicity, harder to rollback

---

### 3. Frontend State Management for Historical Results

**Decision**: Use Pinia store with reactive state and automatic API calls on document selection

**Rationale**:
- Pinia is already in use (package.json shows `pinia: ^2.1.7`)
- Reactive state enables automatic UI updates when historical results load
- Store can cache latest results per document to avoid redundant API calls
- Centralized state makes it easy to sync model selector with historical result's model

**Store Structure**:
```javascript
export const useEmbeddingStore = defineStore('embedding', {
  state: () => ({
    selectedDocument: null,
    selectedModel: 'qwen3-embedding-8b',
    latestResults: {},  // { [documentId]: EmbeddingResult }
    currentResult: null,
    isLoading: false
  }),
  
  actions: {
    async selectDocument(documentId) {
      this.selectedDocument = documentId;
      this.isLoading = true;
      
      // Check cache first
      if (this.latestResults[documentId]) {
        this.currentResult = this.latestResults[documentId];
        this.selectedModel = this.currentResult.model;
        this.isLoading = false;
        return;
      }
      
      // Fetch from API
      try {
        const result = await embeddingAPI.getLatestByDocument(documentId);
        if (result) {
          this.latestResults[documentId] = result;
          this.currentResult = result;
          this.selectedModel = result.model;
        } else {
          this.currentResult = null;
        }
      } finally {
        this.isLoading = false;
      }
    }
  }
});
```

**Alternatives Considered**:
- **Component-local state with props drilling**: Rejected - harder to share state across components
- **Vuex**: Rejected - Pinia is the modern recommended approach for Vue 3
- **Direct API calls in components**: Rejected - leads to duplicate calls, no caching

---

### 4. Model Selector Auto-Switch Behavior

**Decision**: Auto-switch to historical result's model while keeping selector enabled

**Rationale**:
- User feedback shows confusion when selector is locked after viewing historical results
- Allowing model change enables "compare models" workflow (view history, then re-vectorize with different model)
- Button text change to "重新向量化" signals that clicking will generate new result
- Preserves user agency while providing smart defaults

**Implementation**:
```vue
<template>
  <t-select v-model="store.selectedModel" :disabled="false">
    <t-option 
      v-for="model in availableModels" 
      :key="model.name"
      :value="model.name"
      :label="`${model.name} · ${model.dimension}维 · ${model.description}`"
    />
  </t-select>
  
  <t-button 
    @click="handleVectorize"
    :disabled="!store.selectedDocument"
  >
    {{ buttonText }}
  </t-button>
</template>

<script setup>
const buttonText = computed(() => {
  if (store.currentResult && store.selectedDocument) {
    return '重新向量化';
  }
  return '开始向量化';
});
</script>
```

**Alternatives Considered**:
- **Lock selector to historical model**: Rejected - reduces flexibility, user must deselect document to change model
- **Show separate "View History" and "New Vectorization" modes**: Rejected - adds UI complexity
- **Always show "开始向量化"**: Rejected - doesn't signal that new result will be created

---

### 5. Query API Performance Optimization

**Decision**: Use database indexes + LIMIT clauses + prepared statements

**Rationale**:
- Index on `(document_id, model)` ensures <100ms for "latest by document" queries
- Index on `created_at DESC` with `LIMIT 1` ensures <100ms for "latest overall" queries
- Pagination with `LIMIT` + `OFFSET` prevents large result sets
- SQLAlchemy ORM generates efficient queries with proper index usage

**Query Examples**:
```python
# Get latest result for document (target: <100ms for 10K records)
result = db.query(EmbeddingResult)\
    .filter(EmbeddingResult.document_id == document_id)\
    .order_by(EmbeddingResult.created_at.desc())\
    .limit(1)\
    .first()

# Get latest result for document + model
result = db.query(EmbeddingResult)\
    .filter(
        EmbeddingResult.document_id == document_id,
        EmbeddingResult.model == model
    )\
    .order_by(EmbeddingResult.created_at.desc())\
    .limit(1)\
    .first()

# Paginated list (target: <200ms for 10K records)
results = db.query(EmbeddingResult)\
    .filter(EmbeddingResult.status == 'SUCCESS')\
    .order_by(EmbeddingResult.created_at.desc())\
    .limit(page_size)\
    .offset(page * page_size)\
    .all()
```

**Alternatives Considered**:
- **Redis caching layer**: Rejected - adds dependency, premature optimization for 10K records
- **Denormalized document table with latest_embedding_id**: Rejected - complicates writes, violates normalization
- **GraphQL with DataLoader**: Rejected - adds complexity, REST is sufficient

---

### 6. Error Handling Strategy for Partial Vectorization Failures

**Decision**: Continue processing valid chunks, return partial success with detailed failure info

**Rationale**:
- Aligns with user requirement (Session 2025-12-10 clarification: "Continue processing valid documents")
- Partial success is valuable - user gets vectors for valid chunks immediately
- Detailed error_message field stores JSON array of failed chunk indices and reasons
- Frontend can display partial results with warning banner

**Response Format**:
```json
{
  "result_id": "abc-123",
  "status": "PARTIAL_SUCCESS",
  "successful_count": 48,
  "failed_count": 2,
  "error_message": "[{\"chunk_index\": 15, \"error\": \"Rate limit exceeded\"}, {\"chunk_index\": 32, \"error\": \"Invalid text encoding\"}]",
  "processing_time_ms": 12450.5
}
```

**Alternatives Considered**:
- **Fail entire batch on first error**: Rejected - wastes successful vectorization work
- **Retry failed chunks automatically**: Rejected - could cause infinite loops, better to let user re-trigger
- **Store failures in separate table**: Rejected - overkill, error_message JSON field is sufficient

---

### 7. Frontend Display of Metadata in Results Panel

**Decision**: Show document name, model (with dimension), success/total chunks, processing time

**Rationale**:
- Aligns with Session 2025-12-17 clarification: "Display core metrics"
- Provides essential context without cluttering UI
- Format: `DocumentName · model-name · 1024维 · 50/50块 · 1250ms`
- Processing time helps users understand performance characteristics

**Component Structure**:
```vue
<template>
  <div class="results-header">
    <h3>{{ result.document_name }}</h3>
    <div class="metadata">
      <t-tag>{{ result.model }} · {{ result.vector_dimension }}维</t-tag>
      <t-tag variant="success" v-if="result.status === 'SUCCESS'">
        {{ result.successful_count }}/{{ totalChunks }}块
      </t-tag>
      <t-tag variant="warning" v-else>
        {{ result.successful_count }}/{{ totalChunks }}块 · 部分成功
      </t-tag>
      <t-tag>{{ result.processing_time_ms }}ms</t-tag>
    </div>
  </div>
</template>
```

**Alternatives Considered**:
- **Minimal display (name + model only)**: Rejected - missing context about chunk coverage and performance
- **Verbose display (all fields including result_id, timestamps)**: Rejected - clutters UI, not user-facing info
- **Separate info icon with modal**: Rejected - extra click required, core metrics should be immediately visible

---

## Technology Stack Decisions

### Backend

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Web Framework | FastAPI 0.104+ | Already in use, excellent async support, auto-generated OpenAPI docs |
| ORM | SQLAlchemy 2.0+ | Already in use, supports migrations, type-safe query building |
| Embedding Client | langchain-openai 0.2+ | Already in use, OpenAI-compatible protocol, retry built-in |
| Database | SQLite (app.db) | Already in use, sufficient for 10K records, no new dependency |
| Testing | pytest 7.4+, httpx | Already in use, excellent async test support |

### Frontend

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Framework | Vue 3.3+ | Already in use, Composition API enables clean reactive state |
| UI Library | TDesign Vue Next 1.13+ | Already in use, consistent design system |
| State Management | Pinia 2.1+ | Already in use, modern Vuex alternative, TypeScript support |
| HTTP Client | Axios 1.6+ | Already in use, interceptor support for auth |
| Router | Vue Router 4.2+ | Already in use, declarative routing |

---

## Migration Strategy

**Decision**: Create new migration file for `embedding_results` table

**Script**: `backend/migrations/create_embedding_results_table.py`

**Execution**: Run before deploying code changes

```python
# migrations/create_embedding_results_table.py
from sqlalchemy import text

def upgrade(db_connection):
    db_connection.execute(text("""
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
            FOREIGN KEY (document_id) REFERENCES documents(document_id),
            FOREIGN KEY (chunking_result_id) REFERENCES chunking_results(result_id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_embedding_doc_model 
        ON embedding_results(document_id, model);
        
        CREATE INDEX IF NOT EXISTS idx_embedding_created_at 
        ON embedding_results(created_at DESC);
        
        CREATE INDEX IF NOT EXISTS idx_embedding_status 
        ON embedding_results(status);
    """))

def downgrade(db_connection):
    db_connection.execute(text("DROP TABLE IF EXISTS embedding_results;"))
```

---

## API Design Patterns

### RESTful Endpoints

**Pattern**: Noun-based resources with standard HTTP verbs

```
POST   /api/embeddings/from-chunking-result    # Vectorize by chunking result ID
POST   /api/embeddings/from-document            # Vectorize by document ID
GET    /api/embeddings/results/{result_id}      # Get result by ID
GET    /api/embeddings/results                  # List results (with filters)
GET    /api/embeddings/models                   # List available models
GET    /api/embeddings/health                   # Health check
```

**Rationale**:
- Clear, predictable URL structure
- Standard HTTP verbs match CRUD operations
- Query parameters for filters (document_id, model, status, date_range)
- Aligns with existing API patterns in codebase

---

## Performance Benchmarks

### Target Metrics (from NFRs)

| Operation | Target | Strategy |
|-----------|--------|----------|
| Vectorize 100 chunks | <30s | Batch API call, parallel processing where possible |
| Query latest result | <100ms | Indexed query with LIMIT 1 |
| List with pagination | <200ms | Indexed query with LIMIT + OFFSET |
| Dual-write 100 vectors | <5s | Async file I/O, prepared statements |
| Frontend display history | <500ms | Includes API round-trip + rendering |

### Monitoring Points

- Log processing_time_ms for all operations
- Track retry_count and rate_limit_hits
- Monitor query latencies at p50, p95, p99
- Alert if orphaned JSON files detected (should be 0)

---

## Security Considerations

### API Authentication

**Decision**: Use existing API key middleware

**Implementation**: Apply `APIKeyMiddleware` to embedding endpoints

```python
# backend/src/api/embedding_routes.py
from ..middleware.api_key_middleware import verify_api_key

@router.post("/from-document", dependencies=[Depends(verify_api_key)])
async def vectorize_document(...):
    ...
```

### Input Validation

- Validate document_id and result_id exist before processing
- Sanitize file paths to prevent directory traversal
- Validate model name against whitelist
- Check batch size against MAX_BATCH_SIZE (1000)

---

## Rollout Plan

### Phase 1: Backend Implementation
1. Create database migration
2. Implement EmbeddingResult ORM model
3. Update embedding_service.py with chunking methods
4. Implement dual-write storage layer
5. Create API endpoints
6. Write unit and integration tests

### Phase 2: Frontend Implementation
1. Create Pinia embedding store
2. Implement DocumentEmbedding.vue page
3. Create UI components (selectors, results display)
4. Add route to router
5. Wire up API calls
6. Write component tests

### Phase 3: Integration & Testing
1. End-to-end testing of full workflow
2. Performance testing (vectorize 100 chunks)
3. Load testing (10K queries)
4. UI/UX testing with real users

---

## Open Questions & Future Work

### Resolved
- ✅ Database schema design
- ✅ Dual-write transaction strategy
- ✅ Frontend state management
- ✅ Query performance optimization

### Future Enhancements (Out of Scope)
- Embedding result versioning (track changes over time)
- Batch re-vectorization (re-process multiple documents)
- Cost tracking (monitor API usage costs)
- Vector similarity search UI
- Export embedding results to CSV/Parquet

---

## References

- Feature Specification: `specs/003-vector-embedding/spec.md`
- Existing Code:
  - `backend/src/services/embedding_service.py`
  - `backend/src/storage/embedding_db.py`
  - `backend/src/storage/embedding_storage_dual.py`
- Constitution: `.specify/memory/constitution.md`
- LangChain OpenAI Embeddings: https://python.langchain.com/docs/integrations/text_embedding/openai

---

**Status**: ✅ All research topics resolved. Ready for Phase 1 (Design & Contracts).
