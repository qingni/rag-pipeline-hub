# Research: Vector Embedding Module

**Date**: 2025-12-15  
**Feature**: 003-vector-embedding  
**Purpose**: Technical research to resolve unknowns and validate design decisions

---

## Research Areas

### 1. Frontend Document Filtering Strategy

**Question**: How should the frontend efficiently filter documents to show only those with active chunking results?

**Research Findings**:

**Option A: Client-side filtering after fetching all documents**
- Pros: Simple implementation, no backend changes
- Cons: Inefficient for large document lists, unnecessary data transfer, slow page load

**Option B: Backend API filter parameter** ⭐ **RECOMMENDED**
- Pros: Efficient data transfer, faster page load, scalable
- Cons: Requires API modification
- Implementation: Add `?has_chunking_result=true` query parameter to `/documents` endpoint

**Option C: New dedicated endpoint `/documents/with-chunking-results`**
- Pros: Clean separation of concerns
- Cons: API proliferation, duplicate logic

**Decision**: **Option B - Backend API filter parameter**

**Rationale**: 
1. Minimal API surface area expansion
2. Reuses existing document listing endpoint
3. Query parameter approach is RESTful and extensible
4. Enables efficient database query: `JOIN chunking_results WHERE status='completed' AND is_active=true`

**Implementation Details**:
```python
# backend/src/api/documents.py
@router.get("/documents")
async def list_documents(
    has_chunking_result: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Document)
    if has_chunking_result:
        query = query.join(ChunkingResult).filter(
            ChunkingResult.status == ResultStatus.COMPLETED,
            ChunkingResult.is_active == True
        ).distinct()
    return query.all()
```

---

### 2. Model Information Display Pattern

**Question**: How should the frontend present model information in the selector dropdown and detail panel?

**Research Findings**:

**Best Practice Analysis**:
- **GitHub Copilot**: Shows model name + capability tags (e.g., "GPT-4 · Code · Latest")
- **OpenAI Playground**: Dropdown shows name + version, detailed panel below with all specs
- **Anthropic Console**: Two-stage display: compact dropdown, expanded info on selection

**Pattern Selection**: **Two-stage progressive disclosure** ⭐

**Decision**: 
1. **Dropdown**: Compact format `"ModelName · Dimension维 · BriefDescription"`
   - Example: `"BGE-M3 · 1024维 · 多语言支持"`
2. **Detail Panel**: Expands below selector when model selected, shows:
   - Full model name
   - Dimension (with explanation: "每个向量包含1024个浮点数")
   - Provider information
   - Multilingual support status
   - Max batch size
   - Use case recommendations

**Rationale**:
- Dropdown readability: 3 key decision factors visible at glance
- Dimension as critical decision factor for storage/indexing planning
- Progressive disclosure reduces cognitive load
- Detail panel provides confidence without cluttering selection UI

**Implementation**:
```vue
<!-- ModelSelector.vue -->
<t-select v-model="selectedModel" @change="onModelChange">
  <t-option 
    v-for="model in models" 
    :key="model.name"
    :value="model.name"
    :label="`${model.name} · ${model.dimension}维 · ${model.description}`"
  />
</t-select>

<div v-if="selectedModel" class="model-details">
  <t-descriptions :data="modelDetailsData" />
</div>
```

---

### 3. Chunking Result Selection Logic

**Question**: When a document has multiple chunking results (different strategies or versions), which should the system use?

**Research Findings**:

**Current Schema Analysis** (from `chunking_result.py`):
- `ChunkingResult` has fields: `result_id`, `task_id`, `status`, `is_active`, `created_at`
- `ChunkingTask` links to `source_document_id` and `chunking_strategy`
- Multiple results can exist per document with different strategies

**Industry Patterns**:
1. **Explicit version selection** (Git, Confluence): User chooses specific version
2. **Latest by default** (Google Docs, Notion): Always uses most recent, optional history
3. **Strategy-based routing** (AWS Lambda): Different versions for different use cases

**Decision**: **Latest active result with optional strategy filter** ⭐

**Query Logic**:
```python
# Priority 1: If strategy_type specified, use latest for that strategy
# Priority 2: Otherwise, use globally latest active result
query = db.query(ChunkingResult).join(ChunkingTask).filter(
    ChunkingTask.source_document_id == document_id,
    ChunkingResult.status == ResultStatus.COMPLETED,
    ChunkingResult.is_active == True
)
if strategy_type:
    query = query.filter(ChunkingTask.chunking_strategy == strategy_type)
result = query.order_by(ChunkingResult.created_at.desc()).first()
```

**Rationale**:
1. **Simplicity**: One-level selection (document only) in UI
2. **Recency bias**: Latest result typically reflects user's current intent
3. **`is_active` flag**: Allows manual deactivation of problematic results
4. **Strategy override**: Backend API supports strategy filter for advanced use cases (not exposed in frontend initially)

---

### 4. Error Recovery Best Practices for Embedding APIs

**Question**: What retry strategies and error handling patterns are most effective for external embedding APIs?

**Research Findings**:

**OpenAI API Error Types** (reference for OpenAI-compatible APIs):
1. **Rate Limiting (429)**: `Retry-After` header, exponential backoff
2. **Timeout (504)**: Network congestion, retry immediately acceptable
3. **Server Error (500/502/503)**: Transient failures, exponential backoff
4. **Client Error (400/401)**: Do not retry, user action required

**Industry Best Practices**:

**AWS SDK Retry Strategy**:
- Max 3 attempts
- Exponential backoff: `delay = base * (2 ^ attempt) + jitter`
- Jitter: ±25% randomization to prevent thundering herd

**Google Cloud Retry Guidelines**:
- Timeout: 60s default
- Backoff multiplier: 2x
- Max delay cap: 32s

**Implemented Pattern** (already in `embedding_service.py`): ⭐
```python
ExponentialBackoffRetry(
    max_retries=3,
    initial_delay=1.0,  # 1s
    max_delay=32.0,     # 32s cap
    jitter=0.25         # ±25%
)
```

**Validation**: Aligns with industry standards. No changes needed.

**Additional Pattern: Circuit Breaker** (Future Enhancement):
- After 5 consecutive failures, pause requests for 60s
- Not critical for MVP, document as future optimization

---

### 5. Embedding Result Storage Format

**Question**: What should the JSON structure for persisted embedding results look like?

**Research Findings**:

**Requirements Analysis**:
1. **Source traceability**: Link back to chunking result or document
2. **Reproducibility**: Capture all parameters (model, timestamp, config)
3. **Downstream consumption**: Vector database ingestion needs specific format
4. **Debugging**: Include metrics (latency, retry count, failures)

**Proposed Schema**:
```json
{
  "request_id": "uuid-v4",
  "timestamp": "2025-12-15T10:30:00Z",
  "status": "success|partial_success|failed",
  "source": {
    "type": "chunking_result|document",
    "document_id": "doc-uuid",
    "result_id": "result-uuid",  // if from chunking result
    "document_name": "example.pdf"
  },
  "model": {
    "name": "qwen3-embedding-8b",
    "dimension": 1536,
    "provider": "qwen"
  },
  "vectors": [
    {
      "index": 0,
      "vector": [0.123, -0.456, ...],  // 1536 floats
      "text_hash": "sha256:abc123...",
      "text_length": 250,
      "processing_time_ms": 45.2
    }
  ],
  "failures": [
    {
      "index": 5,
      "error_type": "RATE_LIMIT_ERROR",
      "error_message": "Rate limit exceeded",
      "retry_count": 3
    }
  ],
  "metadata": {
    "batch_size": 50,
    "successful_count": 49,
    "failed_count": 1,
    "total_processing_time_ms": 2345.6,
    "retry_count": 8,
    "rate_limit_hits": 2,
    "config": {
      "api_endpoint": "http://dev.fit-ai.woa.com/api/llmproxy",
      "max_retries": 3,
      "timeout_seconds": 60
    }
  }
}
```

**Decision**: Adopt schema above with source traceability section ⭐

**Rationale**:
1. **`source` section**: Enables tracing back to original document and chunking parameters
2. **Vector array**: Preserves chunk order (critical for reassembly)
3. **`text_hash`**: Enables deduplication and verification
4. **Metrics**: Supports operational monitoring and SLA validation
5. **Failure tracking**: Enables partial success analysis

**File Naming Convention** (per Constitution):
```
{document_name}_{timestamp}.json
example: research_paper_20251215_103045.json
```

---

### 6. Frontend State Management for Embedding Workflow

**Question**: How should Pinia store structure handle the embedding workflow state?

**Research Findings**:

**Workflow State Analysis**:
1. **Selection State**: Current document, selected model
2. **Processing State**: Loading, progress, errors
3. **Results State**: Vector data, metadata, failures
4. **History State**: Past embeddings for comparison

**Pinia Best Practices** (Vue 3 ecosystem):
- **Normalized State**: Store entities by ID in maps
- **Computed Properties**: Derive filtered/sorted views
- **Actions Return Promises**: Enable async/await in components
- **Optimistic Updates**: Update UI immediately, rollback on error

**Proposed Store Structure**:
```javascript
// stores/embedding.js
export const useEmbeddingStore = defineStore('embedding', {
  state: () => ({
    // Selection
    selectedDocumentId: null,
    selectedModel: null,
    
    // Processing
    isProcessing: false,
    progress: 0, // 0-100
    currentRequestId: null,
    
    // Results (normalized)
    embeddingResults: {}, // { requestId: result }
    currentResultId: null,
    
    // Documents (cached for filtering)
    documentsWithChunking: [], // { id, name, chunkingStatus, chunkCount }
    
    // Models (cached from API)
    availableModels: [],
    
    // Error state
    error: null
  }),
  
  getters: {
    currentResult: (state) => 
      state.embeddingResults[state.currentResultId],
    
    selectedDocument: (state) => 
      state.documentsWithChunking.find(d => d.id === state.selectedDocumentId),
    
    canStartEmbedding: (state) => 
      state.selectedDocumentId && state.selectedModel && !state.isProcessing
  },
  
  actions: {
    async fetchDocumentsWithChunking() {
      const docs = await embeddingService.getDocumentsWithChunking()
      this.documentsWithChunking = docs
    },
    
    async startEmbedding() {
      this.isProcessing = true
      this.error = null
      try {
        const result = await embeddingService.embedDocument({
          documentId: this.selectedDocumentId,
          model: this.selectedModel
        })
        this.embeddingResults[result.request_id] = result
        this.currentResultId = result.request_id
      } catch (err) {
        this.error = err.message
      } finally {
        this.isProcessing = false
      }
    }
  }
})
```

**Decision**: Adopt normalized state pattern with computed getters ⭐

**Rationale**:
- Clear separation of concerns (selection/processing/results)
- Computed getters enable reactive validation (e.g., `canStartEmbedding`)
- Normalized results map supports history/comparison features
- Error state isolation simplifies error boundary rendering

---

## Summary of Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| **Document Filtering** | Backend API filter parameter `?has_chunking_result=true` | Efficient, scalable, RESTful |
| **Model Display** | Two-stage: compact dropdown + detail panel | Progressive disclosure, reduces cognitive load |
| **Result Selection** | Latest active result, optional strategy filter | Simplicity, recency bias, manual override via `is_active` |
| **Retry Strategy** | Current implementation (3 retries, exp backoff, jitter) validated | Aligns with AWS/Google best practices |
| **Storage Format** | JSON with source traceability section | Reproducibility, downstream compatibility |
| **State Management** | Normalized Pinia store with computed getters | Reactive validation, separation of concerns |

---

## Alternatives Considered

### Document Filtering
- ❌ **Client-side filtering**: Rejected due to inefficiency and slow page load
- ❌ **New endpoint**: Rejected due to API proliferation

### Model Selection
- ❌ **Dropdown only (no detail panel)**: Rejected due to insufficient decision information
- ❌ **Modal for details**: Rejected due to extra click required

### Result Selection
- ❌ **Explicit version picker**: Rejected due to added UI complexity (conflicts with User Story 3 requirement for one-level selection)
- ❌ **Always latest regardless of strategy**: Rejected due to inability to handle multi-strategy scenarios

### Storage Format
- ❌ **Separate metadata file**: Rejected due to atomicity concerns
- ❌ **Binary format (numpy/pickle)**: Rejected due to language portability and debugging difficulty

---

## Open Questions for Phase 1

1. **API Contract**: Should `/documents` endpoint filter return include `chunkingStatus` summary in response?
   - Recommendation: Yes, include `{ chunkingResults: [{ strategy, timestamp, chunkCount }] }` for frontend display

2. **Error Boundary**: Should frontend implement global error recovery for embedding failures?
   - Recommendation: Phase 2 - implement toast notifications, log to backend

3. **Vector Visualization**: Should results panel include dimension reduction visualization (t-SNE/UMAP)?
   - Recommendation: Out of scope for MVP, document as future enhancement

---

**Next Steps**: Proceed to Phase 1 (Data Model & Contracts generation)
