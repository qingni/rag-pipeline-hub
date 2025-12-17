# Quickstart: Vector Embedding Module Development

**Feature**: 003-vector-embedding  
**Target Audience**: Developers implementing the vector embedding module  
**Prerequisites**: Python 3.10+, Node.js 18+, existing RAG framework setup

---

## 🚀 Setup

### 1. Backend Dependencies

Install required Python packages:
```bash
cd backend
pip install fastapi sqlalchemy httpx tenacity pydantic
```

**Key Libraries**:
- `httpx`: Async HTTP client for OpenAI-compatible embedding API
- `tenacity`: Exponential backoff retry mechanism
- `sqlalchemy`: ORM for `embedding_results` table
- `pydantic`: Request/response validation

### 2. Frontend Dependencies

Install Vue3 components (already in project):
```bash
cd frontend
# TDesign Vue Next, Vue Router, Pinia already installed
```

### 3. Database Migration

Create `embedding_results` table:
```bash
cd backend
# Run Alembic migration or direct SQL
python -m alembic upgrade head
```

**Manual SQL** (for development):
```sql
sqlite3 database.db < migrations/003_embedding_results.sql
```

**Migration File** (`migrations/003_embedding_results.sql`):
```sql
CREATE TABLE embedding_results (
    result_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunking_result_id TEXT,
    model TEXT NOT NULL,
    status TEXT NOT NULL,
    successful_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    vector_dimension INTEGER NOT NULL,
    json_file_path TEXT NOT NULL,
    processing_time_ms REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    CHECK (status IN ('SUCCESS', 'FAILED', 'PARTIAL_SUCCESS')),
    CHECK (model IN ('bge-m3', 'qwen3-embedding-8b', 'hunyuan-embedding', 'jina-embeddings-v4'))
);

CREATE INDEX idx_doc_model ON embedding_results(document_id, model);
CREATE INDEX idx_created_at ON embedding_results(created_at DESC);
CREATE INDEX idx_status ON embedding_results(status);
```

---

## 📂 File Structure Overview

### Backend Files to Create/Modify

```
backend/src/
├── models/
│   └── embedding_models.py          # NEW: ORM model + Pydantic schemas
├── storage/
│   └── embedding_db.py               # NEW: Database queries
├── services/
│   ├── embedding_service.py          # MODIFY: Add chunking result integration
│   └── embedding_storage.py          # NEW: Dual-write logic (JSON + DB)
└── api/
    ├── embedding_routes.py           # MODIFY: Add /from-document endpoint
    └── embedding_query_routes.py     # NEW: Query endpoints
```

### Frontend Files to Create/Modify

```
frontend/src/
├── views/
│   └── VectorEmbed.vue               # NEW: Unified embedding page
├── components/embedding/
│   ├── EmbeddingPanel.vue            # NEW: Document selector + config
│   └── EmbeddingResults.vue          # MODIFY: Add database result display
└── services/
    └── embeddingApi.js               # MODIFY: Add query API calls
```

---

## 🔧 Implementation Steps

### Phase 1: Backend Database Layer

#### Step 1.1: Create ORM Model

**File**: `backend/src/models/embedding_models.py`

```python
from sqlalchemy import Column, String, Integer, Float, DateTime, CheckConstraint
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime

# SQLAlchemy ORM Model
class EmbeddingResult(Base):
    __tablename__ = "embedding_results"
    
    result_id = Column(String, primary_key=True)
    document_id = Column(String, nullable=False)
    chunking_result_id = Column(String)
    model = Column(String, nullable=False)
    status = Column(String, nullable=False)
    successful_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    vector_dimension = Column(Integer, nullable=False)
    json_file_path = Column(String, nullable=False)
    processing_time_ms = Column(Float)
    created_at = Column(DateTime, default=func.now())
    error_message = Column(String)
    
    __table_args__ = (
        CheckConstraint("status IN ('SUCCESS', 'FAILED', 'PARTIAL_SUCCESS')"),
        CheckConstraint("model IN ('bge-m3', 'qwen3-embedding-8b', 'hunyuan-embedding', 'jina-embeddings-v4')"),
    )

# Pydantic Request Schemas
class VectorizationFromChunkingRequest(BaseModel):
    chunking_result_id: str
    model: Literal['bge-m3', 'qwen3-embedding-8b', 'hunyuan-embedding', 'jina-embeddings-v4']

class VectorizationFromDocumentRequest(BaseModel):
    document_id: str
    model: Literal['bge-m3', 'qwen3-embedding-8b', 'hunyuan-embedding', 'jina-embeddings-v4']
    strategy: Optional[str] = None

# Pydantic Response Schemas
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
    
    class Config:
        orm_mode = True
```

#### Step 1.2: Implement Database Queries

**File**: `backend/src/storage/embedding_db.py`

```python
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from .models.embedding_models import EmbeddingResult

def get_embedding_by_id(db: Session, result_id: str) -> Optional[EmbeddingResult]:
    """Get embedding result by ID (FR-025)"""
    return db.query(EmbeddingResult).filter(EmbeddingResult.result_id == result_id).first()

def get_latest_embedding_by_document(
    db: Session, 
    document_id: str, 
    model: Optional[str] = None
) -> Optional[EmbeddingResult]:
    """Get latest embedding for document, optionally filtered by model (FR-026)"""
    query = db.query(EmbeddingResult).filter(EmbeddingResult.document_id == document_id)
    if model:
        query = query.filter(EmbeddingResult.model == model)
    return query.order_by(EmbeddingResult.created_at.desc()).first()

def list_embedding_results(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    document_id: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> tuple[List[EmbeddingResult], int]:
    """List embedding results with pagination and filters (FR-027)"""
    query = db.query(EmbeddingResult)
    
    # Apply filters
    if document_id:
        query = query.filter(EmbeddingResult.document_id == document_id)
    if model:
        query = query.filter(EmbeddingResult.model == model)
    if status:
        query = query.filter(EmbeddingResult.status == status)
    if date_from:
        query = query.filter(EmbeddingResult.created_at >= date_from)
    if date_to:
        query = query.filter(EmbeddingResult.created_at <= date_to)
    
    total_count = query.count()
    
    # Pagination
    results = query.order_by(EmbeddingResult.created_at.desc()) \
                   .offset((page - 1) * page_size) \
                   .limit(page_size) \
                   .all()
    
    return results, total_count

def create_or_update_embedding_result(
    db: Session,
    result_data: dict
) -> EmbeddingResult:
    """Create new or update existing embedding result (FR-024 duplicate handling)"""
    # Check if record exists for same document+chunking_result+model
    existing = db.query(EmbeddingResult).filter(
        EmbeddingResult.document_id == result_data["document_id"],
        EmbeddingResult.chunking_result_id == result_data["chunking_result_id"],
        EmbeddingResult.model == result_data["model"]
    ).first()
    
    if existing:
        # Update existing record (FR-024)
        for key, value in result_data.items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new record
        new_result = EmbeddingResult(**result_data)
        db.add(new_result)
        db.commit()
        db.refresh(new_result)
        return new_result
```

---

### Phase 2: Backend Storage Layer

#### Step 2.1: Dual-Write Implementation

**File**: `backend/src/services/embedding_storage.py`

```python
import os
import json
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from .embedding_db import create_or_update_embedding_result

RESULTS_DIR = "results/embedding"

def save_embedding_result(
    db: Session,
    result_data: dict,
    vectors_data: list
) -> tuple[str, str]:
    """
    Dual-write: Save vectors to JSON file, then save metadata to database.
    Rollback (delete JSON) if database write fails.
    
    Returns: (result_id, json_file_path)
    Raises: StorageError on failure
    """
    json_path = None
    
    try:
        # Step 1: Write JSON file
        json_path = _write_vector_json(result_data["request_id"], vectors_data, result_data)
        
        # Step 2: Update result_data with file path
        result_data["json_file_path"] = json_path
        
        # Step 3: Write/update database record
        db_result = create_or_update_embedding_result(db, result_data)
        
        return db_result.result_id, json_path
        
    except Exception as e:
        # Step 4: Rollback - delete JSON file if database write failed
        if json_path and os.path.exists(os.path.join(RESULTS_DIR, json_path)):
            full_path = os.path.join(RESULTS_DIR, json_path)
            os.remove(full_path)
        raise StorageError(f"Failed to save embedding result: {str(e)}")

def _write_vector_json(request_id: str, vectors: list, metadata: dict) -> str:
    """
    Write vectors to JSON file in dated directory.
    Returns relative path from RESULTS_DIR.
    """
    # Create directory: results/embedding/YYYY-MM-DD/
    today = datetime.now().strftime("%Y-%m-%d")
    date_dir = Path(RESULTS_DIR) / today
    date_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"embedding_{request_id[:8]}_{timestamp}.json"
    full_path = date_dir / filename
    
    # Write JSON
    json_data = {
        "request_id": request_id,
        "document_id": metadata["document_id"],
        "chunking_result_id": metadata.get("chunking_result_id"),
        "model": metadata["model"],
        "status": metadata["status"],
        "metadata": {
            "total_chunks": len(vectors) + len(metadata.get("failures", [])),
            "successful_count": metadata["successful_count"],
            "failed_count": metadata["failed_count"],
            "vector_dimension": metadata["vector_dimension"],
            "processing_time_ms": metadata.get("processing_time_ms"),
            "created_at": datetime.now().isoformat()
        },
        "vectors": vectors,
        "failures": metadata.get("failures", [])
    }
    
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    # Return relative path
    relative_path = f"{today}/{filename}"
    return relative_path
```

---

### Phase 3: Backend API Routes

#### Step 3.1: Vectorization Endpoints

**File**: `backend/src/api/embedding_routes.py` (modify existing)

Add new endpoint:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..services.embedding_service import EmbeddingService
from ..services.embedding_storage import save_embedding_result
from ..models.embedding_models import VectorizationFromDocumentRequest

router = APIRouter(prefix="/embedding", tags=["vectorization"])

@router.post("/from-document")
async def vectorize_document(
    request: VectorizationFromDocumentRequest,
    db: Session = Depends(get_db)
):
    """Vectorize latest chunking result for document (User Story 2, FR-002)"""
    service = EmbeddingService(model=request.model)
    
    # 1. Find latest chunking result for document
    chunking_result = get_latest_chunking_result(
        db, 
        request.document_id, 
        strategy=request.strategy
    )
    if not chunking_result:
        raise HTTPException(404, "No chunking result found for document")
    
    # 2. Load chunks from chunking result JSON
    chunks = load_chunks_from_json(chunking_result.json_file_path)
    
    # 3. Vectorize chunks
    result = await service.vectorize_batch(chunks)
    
    # 4. Dual-write: JSON + Database
    result_id, json_path = save_embedding_result(
        db,
        result_data={
            "request_id": result["request_id"],
            "document_id": request.document_id,
            "chunking_result_id": chunking_result.id,
            "model": request.model,
            "status": result["status"],
            "successful_count": result["successful_count"],
            "failed_count": result["failed_count"],
            "vector_dimension": result["vector_dimension"],
            "processing_time_ms": result["processing_time_ms"]
        },
        vectors_data=result["vectors"]
    )
    
    return result
```

#### Step 3.2: Query Endpoints

**File**: `backend/src/api/embedding_query_routes.py` (new)

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..storage.embedding_db import (
    get_embedding_by_id,
    get_latest_embedding_by_document,
    list_embedding_results
)
from ..models.embedding_models import EmbeddingResultDetail

router = APIRouter(prefix="/embedding/results", tags=["query"])

@router.get("/{result_id}", response_model=EmbeddingResultDetail)
def get_result_by_id(result_id: str, db: Session = Depends(get_db)):
    """Get embedding result by ID (FR-025)"""
    result = get_embedding_by_id(db, result_id)
    if not result:
        raise HTTPException(404, f"Embedding result not found: {result_id}")
    return result

@router.get("/by-document/{document_id}", response_model=EmbeddingResultDetail)
def get_latest_by_document(
    document_id: str,
    model: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get latest embedding for document (FR-026)"""
    result = get_latest_embedding_by_document(db, document_id, model)
    if not result:
        raise HTTPException(404, f"No embedding found for document: {document_id}")
    return result

@router.get("", response_model=dict)
def list_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    document_id: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List embedding results with pagination (FR-027)"""
    results, total_count = list_embedding_results(
        db, page, page_size, document_id, model, status, date_from, date_to
    )
    
    total_pages = (total_count + page_size - 1) // page_size
    
    return {
        "results": [EmbeddingResultDetail.from_orm(r) for r in results],
        "pagination": {
            "total_count": total_count,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
    }
```

---

### Phase 4: Frontend Implementation

#### Step 4.1: Unified Embedding Page

**File**: `frontend/src/views/VectorEmbed.vue`

```vue
<template>
  <div class="vector-embed-page">
    <div class="page-layout">
      <!-- Left Panel: Controls -->
      <div class="left-panel">
        <EmbeddingPanel
          @start-vectorization="handleStartVectorization"
        />
      </div>
      
      <!-- Right Panel: Results -->
      <div class="right-panel">
        <EmbeddingResults
          :result="embeddingStore.currentResult"
          :loading="embeddingStore.isLoading"
          :error="embeddingStore.error"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { useEmbeddingStore } from '@/stores/embedding'
import EmbeddingPanel from '@/components/embedding/EmbeddingPanel.vue'
import EmbeddingResults from '@/components/embedding/EmbeddingResults.vue'

const embeddingStore = useEmbeddingStore()

async function handleStartVectorization({ documentId, model }) {
  await embeddingStore.startVectorization(documentId, model)
}
</script>

<style scoped>
.page-layout {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 24px;
  height: calc(100vh - 120px);
}

.left-panel {
  border-right: 1px solid #e5e7eb;
  padding-right: 24px;
}

.right-panel {
  overflow-y: auto;
}
</style>
```

#### Step 4.2: Document Selector Component

**File**: `frontend/src/components/embedding/EmbeddingPanel.vue`

```vue
<template>
  <div class="embedding-panel">
    <t-card title="文档向量化">
      <!-- Document Selector -->
      <t-select
        v-model="selectedDocumentId"
        placeholder="选择已分块文档"
        :loading="documentsLoading"
      >
        <t-option
          v-for="doc in chunkedDocuments"
          :key="doc.id"
          :value="doc.id"
          :label="formatDocumentLabel(doc)"
        />
      </t-select>
      
      <!-- Model Selector -->
      <t-select
        v-model="selectedModel"
        placeholder="选择向量模型"
        class="mt-4"
      >
        <t-option
          v-for="(info, name) in embeddingModels"
          :key="name"
          :value="name"
          :label="`${info.name} · ${info.dimension}维 · ${info.description}`"
        />
      </t-select>
      
      <!-- Model Details Panel -->
      <div v-if="selectedModelInfo" class="model-details mt-4">
        <p><strong>维度:</strong> {{ selectedModelInfo.dimension }}</p>
        <p><strong>提供商:</strong> {{ selectedModelInfo.provider }}</p>
        <p><strong>多语言支持:</strong> {{ selectedModelInfo.supports_multilingual ? '是' : '否' }}</p>
        <p><strong>最大批量:</strong> {{ selectedModelInfo.max_batch_size }}</p>
      </div>
      
      <!-- Start Button -->
      <t-button
        theme="primary"
        block
        class="mt-4"
        :disabled="!canStartVectorization"
        @click="handleStart"
      >
        开始向量化
      </t-button>
    </t-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { embeddingApi } from '@/services/embeddingApi'

const emit = defineEmits(['start-vectorization'])

const selectedDocumentId = ref(null)
const selectedModel = ref('qwen3-embedding-8b')
const chunkedDocuments = ref([])
const embeddingModels = ref({})
const documentsLoading = ref(false)

const selectedModelInfo = computed(() => embeddingModels.value[selectedModel.value])
const canStartVectorization = computed(() => selectedDocumentId.value && selectedModel.value)

function formatDocumentLabel(doc) {
  const date = new Date(doc.latest_chunking.created_at).toLocaleDateString('zh-CN')
  return `${doc.name} · 已分块 · ${date}`
}

async function loadChunkedDocuments() {
  documentsLoading.value = true
  try {
    const response = await fetch('/api/documents?status=chunked')
    chunkedDocuments.value = (await response.json()).documents
  } finally {
    documentsLoading.value = false
  }
}

async function loadEmbeddingModels() {
  embeddingModels.value = await embeddingApi.getModels()
}

function handleStart() {
  emit('start-vectorization', {
    documentId: selectedDocumentId.value,
    model: selectedModel.value
  })
}

onMounted(() => {
  loadChunkedDocuments()
  loadEmbeddingModels()
})
</script>
```

---

## 🧪 Testing

### Unit Tests

**Backend** (`backend/tests/unit/test_embedding_storage.py`):
```python
def test_dual_write_success(db_session, tmpdir):
    result_data = {
        "request_id": "test-123",
        "document_id": "doc-1",
        "model": "bge-m3",
        "status": "SUCCESS",
        "successful_count": 10,
        "failed_count": 0,
        "vector_dimension": 1024
    }
    vectors = [{"vector": [0.1, 0.2], "index": i} for i in range(10)]
    
    result_id, json_path = save_embedding_result(db_session, result_data, vectors)
    
    # Assert database record exists
    db_result = get_embedding_by_id(db_session, result_id)
    assert db_result is not None
    assert db_result.status == "SUCCESS"
    
    # Assert JSON file exists
    assert os.path.exists(os.path.join(RESULTS_DIR, json_path))

def test_dual_write_rollback_on_db_failure(db_session, tmpdir, monkeypatch):
    # Simulate database failure
    def mock_commit():
        raise Exception("Database error")
    
    monkeypatch.setattr(db_session, "commit", mock_commit)
    
    result_data = {...}
    vectors = [...]
    
    with pytest.raises(StorageError):
        save_embedding_result(db_session, result_data, vectors)
    
    # Assert JSON file was rolled back (deleted)
    assert not os.path.exists(...)  # Check file doesn't exist
```

### Integration Tests

**API Test** (`backend/tests/integration/test_embedding_api.py`):
```python
def test_vectorize_document_endpoint(client, db_session):
    # Setup: Create document with chunking result
    doc = create_test_document(db_session)
    chunk_result = create_test_chunking_result(db_session, doc.id)
    
    # Call endpoint
    response = client.post("/api/embedding/from-document", json={
        "document_id": doc.id,
        "model": "bge-m3"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["document_id"] == doc.id
    
    # Verify database record
    db_result = get_latest_embedding_by_document(db_session, doc.id)
    assert db_result is not None
    assert db_result.model == "bge-m3"
```

---

## 📊 Verification Checklist

### Backend
- [ ] Database table `embedding_results` created with indexes
- [ ] Dual-write transaction works (JSON first, DB second, rollback on failure)
- [ ] `/from-document` endpoint uses latest chunking result
- [ ] Query endpoints return correct filtered/paginated results
- [ ] Model dimension validation prevents mismatched vectors
- [ ] Retry mechanism works (exponential backoff with jitter)

### Frontend
- [ ] `/documents/embed` route exists (no `/embeddings` route)
- [ ] Document selector shows only chunked documents
- [ ] Model selector displays dimension and description
- [ ] "开始向量化" button disabled when no document selected
- [ ] Results panel shows document source information

### Integration
- [ ] End-to-end test: Select document → Vectorize → View results
- [ ] Re-vectorization updates existing record (FR-024)
- [ ] Database query performance <100ms for 10k records (SC-016)

---

## 🐛 Troubleshooting

### Issue: "No chunked documents available"
**Cause**: No documents have completed chunking  
**Fix**: Run chunking module first on uploaded documents

### Issue: "Dimension mismatch" error
**Cause**: API returned different dimension than expected  
**Fix**: Verify `EMBEDDING_MODELS` dictionary matches actual API responses

### Issue: Orphaned JSON files
**Cause**: Database write failed without rollback  
**Fix**: Check `save_embedding_result` function has try-except with file cleanup

### Issue: Slow query performance
**Cause**: Missing database indexes  
**Fix**: Verify indexes created: `idx_doc_model`, `idx_created_at`, `idx_status`

---

## 📚 Next Steps

After completing quickstart:
1. Run full test suite: `pytest backend/tests`
2. Review API contracts: `/specs/003-vector-embedding/contracts/*.yaml`
3. Proceed to task breakdown: `/speckit.tasks` command
4. Reference data model: `/specs/003-vector-embedding/data-model.md`

**Estimated Development Time**: 3-5 days (backend 2 days, frontend 1-2 days, testing 1 day)
