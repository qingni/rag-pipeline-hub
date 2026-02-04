# Quickstart Guide: Vector Embedding Module

**Feature**: 003-vector-embedding  
**Date**: 2025-12-17

## Overview

This guide provides step-by-step instructions for developers to understand, build, test, and use the vector embedding module. Follow these steps to get the module running on your local machine.

---

## Prerequisites

### Required Software
- Python 3.11+ (backend)
- Node.js 18+ and npm/yarn (frontend)
- SQLite 3 (for database)
- Git (for version control)

### Required Accounts/Credentials
- Embedding API key (OpenAI-compatible service)
- API base URL for embedding service

### Knowledge Prerequisites
- Basic understanding of vector embeddings
- Familiarity with REST APIs
- Experience with Vue.js (for frontend work)
- Understanding of SQLAlchemy ORM (for backend work)

---

## Step 1: Environment Setup

### 1.1 Clone Repository and Switch Branch

```bash
cd /path/to/rag-framework-spec
git checkout 003-vector-embedding
```

### 1.2 Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 1.3 Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
# or
yarn install
```

### 1.4 Configure Environment Variables

Create `backend/.env` file:

```bash
# Database
DATABASE_URL=sqlite:///./app.db

# Embedding API Configuration (REQUIRED)
EMBEDDING_API_KEY=your_api_key_here
EMBEDDING_API_BASE_URL=https://your-embedding-api.com/v1
EMBEDDING_DEFAULT_MODEL=qwen3-embedding-8b

# Embedding Retry Configuration
EMBEDDING_MAX_RETRIES=3
EMBEDDING_TIMEOUT=60
EMBEDDING_INITIAL_DELAY=1
EMBEDDING_MAX_DELAY=32

# Storage
UPLOAD_DIR=../uploads
RESULTS_DIR=./results
EMBEDDING_RESULTS_DIR=results/embedding

# API Authentication
EMBEDDING_CLIENT_API_KEY=your_client_api_key_here

# Server
HOST=0.0.0.0
PORT=8000
RELOAD=true
LOG_LEVEL=info
```

**Important**: Replace placeholder values with actual credentials.

---

## Step 2: Database Migration

### 2.1 Run Migration Script

```bash
cd backend

# Run embedding_results table migration
python -c "
from src.storage.database import engine
from migrations.create_embedding_results_table import upgrade

with engine.connect() as conn:
    upgrade(conn)
    conn.commit()
print('Migration completed successfully')
"
```

### 2.2 Verify Table Creation

```bash
# Using SQLite CLI
sqlite3 app.db

sqlite> .schema embedding_results
# Should show CREATE TABLE statement with indexes

sqlite> .exit
```

Expected output:
```sql
CREATE TABLE embedding_results (
    result_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunking_result_id TEXT NOT NULL,
    model TEXT NOT NULL,
    ...
);
CREATE INDEX idx_embedding_doc_model ON embedding_results(document_id, model);
...
```

---

## Step 3: Start Services

### 3.1 Start Backend Server

```bash
cd backend
source venv/bin/activate  # If not already activated

# Start with uvicorn
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 3.2 Verify Backend Health

Open browser or use curl:

```bash
curl http://localhost:8000/api/embeddings/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "up",
  "api_connectivity": true,
  "models_available": [
    "qwen3-embedding-8b",
    "bge-m3",
    "hunyuan-embedding",
    "qwen3-vl-embedding-8b"  ],
  "authentication": "valid",
  "timestamp": "2025-12-17T10:30:45Z"
}
```

### 3.3 Start Frontend Development Server

```bash
cd frontend

# Start Vite dev server
npm run dev
# or
yarn dev
```

Expected output:
```
  VITE v5.0.4  ready in 234 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h to show help
```

---

## Step 4: Test Basic Functionality

### 4.1 Create Test Data (Prerequisites)

Before testing embedding, you need:
1. A document uploaded to the system
2. A completed chunking result for that document

```bash
# Example: Upload a test document
curl -X POST http://localhost:8000/api/documents/upload \
  -H "X-API-Key: your_client_api_key_here" \
  -F "file=@/path/to/test.pdf"

# Response: { "document_id": "doc_123", ... }

# Example: Create chunking result
curl -X POST http://localhost:8000/api/chunking/chunk \
  -H "X-API-Key: your_client_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc_123",
    "chunking_strategy": "fixed_size",
    "chunk_size": 512,
    "chunk_overlap": 50
  }'

# Response: { "result_id": "chunk_456", ... }
```

### 4.2 Test Vectorization API

**Test 1: Vectorize by Chunking Result ID**

```bash
curl -X POST http://localhost:8000/api/embeddings/from-chunking-result \
  -H "X-API-Key: your_client_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "result_id": "chunk_456",
    "model": "qwen3-embedding-8b"
  }'
```

Expected response:
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

**Test 2: Vectorize by Document ID**

```bash
curl -X POST http://localhost:8000/api/embeddings/from-document \
  -H "X-API-Key: your_client_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc_123",
    "model": "bge-m3"
  }'
```

### 4.3 Test Query API

**Query Latest Result for Document**

```bash
curl http://localhost:8000/api/embeddings/results/by-document/doc_123 \
  -H "X-API-Key: your_client_api_key_here"
```

**List All Results**

```bash
curl "http://localhost:8000/api/embeddings/results?page=1&page_size=20" \
  -H "X-API-Key: your_client_api_key_here"
```

### 4.4 Verify JSON File Creation

```bash
cd backend/results/embedding
ls -lh

# Should see JSON file like: doc_123_20251217_103045.json

# Inspect file structure
cat doc_123_20251217_103045.json | jq '.'
```

Expected structure:
```json
{
  "result_id": "emb_...",
  "document_id": "doc_123",
  "chunking_result_id": "chunk_456",
  "model": "qwen3-embedding-8b",
  "vector_dimension": 4096,
  "created_at": "2025-12-17T10:30:45Z",
  "vectors": [
    {
      "chunk_index": 0,
      "text_hash": "sha256:...",
      "text_length": 512,
      "vector": [0.0234, -0.0156, ...],
      "processing_time_ms": 245.3
    }
  ]
}
```

---

## Step 5: Test Frontend UI

### 5.1 Navigate to Embedding Page

1. Open browser: `http://localhost:5173`
2. Click "文档向量化" in navigation menu
3. Should see `/documents/embed` URL

### 5.2 Test Document Selection

1. Open document selector dropdown
2. Verify only chunked documents are shown
3. Select a document with existing embedding result
4. Verify:
   - Right panel immediately shows historical result
   - Model selector auto-switches to match historical model
   - Button text changes to "重新向量化"

### 5.3 Test Vectorization Workflow

**Scenario 1: View Historical Result**

1. Select document with embedding history
2. Verify metadata header shows: `DocumentName · model-name · 1024维 · 50/50块 · 1250ms`
3. Verify vector results display in right panel

**Scenario 2: Re-Vectorize with Same Model**

1. Keep same model selected
2. Click "重新向量化"
3. Wait for processing
4. Verify display auto-updates to show new result
5. Verify new database record created (old preserved)

**Scenario 3: Re-Vectorize with Different Model**

1. Select document with embedding history
2. Change model selector to different model
3. Click "重新向量化"
4. Verify new result generated with new model
5. Verify both results preserved in database

---

## Step 6: Run Automated Tests

### 6.1 Backend Unit Tests

```bash
cd backend
source venv/bin/activate

# Run all embedding tests
pytest tests/unit/test_embedding_service.py -v
pytest tests/unit/test_embedding_storage.py -v

# Run with coverage
pytest tests/unit/test_embedding*.py --cov=src.services.embedding_service --cov=src.storage.embedding_db --cov-report=html
```

Expected output:
```
tests/unit/test_embedding_service.py::test_embed_query_success PASSED
tests/unit/test_embedding_service.py::test_embed_documents_partial_success PASSED
tests/unit/test_embedding_storage.py::test_dual_write_success PASSED
tests/unit/test_embedding_storage.py::test_dual_write_rollback_on_db_failure PASSED
...
==================== 15 passed in 2.34s ====================
```

### 6.2 Backend Integration Tests

```bash
# Run API integration tests
pytest tests/integration/test_embedding_api.py -v
pytest tests/integration/test_embedding_dual_write.py -v
```

### 6.3 Frontend Component Tests

```bash
cd frontend

# Run component tests
npm run test
# or
yarn test
```

---

## Step 7: Common Workflows

### Workflow 1: First-Time Document Vectorization

```bash
# 1. Upload document
doc_id=$(curl -X POST http://localhost:8000/api/documents/upload \
  -H "X-API-Key: $API_KEY" \
  -F "file=@document.pdf" | jq -r '.document_id')

# 2. Chunk document
result_id=$(curl -X POST http://localhost:8000/api/chunking/chunk \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\": \"$doc_id\", \"chunking_strategy\": \"semantic\"}" \
  | jq -r '.result_id')

# 3. Vectorize chunks
curl -X POST http://localhost:8000/api/embeddings/from-chunking-result \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"result_id\": \"$result_id\", \"model\": \"qwen3-embedding-8b\"}"
```

### Workflow 2: Compare Multiple Models

```bash
# Vectorize same document with different models
for model in "bge-m3" "qwen3-embedding-8b" "hunyuan-embedding"; do
  echo "Vectorizing with $model..."
  curl -X POST http://localhost:8000/api/embeddings/from-document \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"document_id\": \"doc_123\", \"model\": \"$model\"}"
  sleep 2
done

# Query all results for comparison
curl "http://localhost:8000/api/embeddings/results?document_id=doc_123" \
  -H "X-API-Key: $API_KEY" | jq '.results[] | {model, vector_dimension, processing_time_ms}'
```

### Workflow 3: Batch Processing Multiple Documents

```bash
# Vectorize all documents in the system
curl http://localhost:8000/api/documents/list -H "X-API-Key: $API_KEY" \
  | jq -r '.documents[] | select(.chunking_status == "chunked") | .document_id' \
  | while read doc_id; do
      echo "Processing $doc_id..."
      curl -X POST http://localhost:8000/api/embeddings/from-document \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"document_id\": \"$doc_id\", \"model\": \"qwen3-embedding-8b\"}"
      sleep 1
    done
```

---

## Troubleshooting

### Problem 1: Health Check Shows "degraded" Status

**Symptoms**: `/api/embeddings/health` returns `"status": "degraded"`

**Possible Causes**:
- Invalid or missing `EMBEDDING_API_KEY`
- Incorrect `EMBEDDING_API_BASE_URL`
- Embedding API service is down
- Network connectivity issues

**Solutions**:
1. Verify environment variables in `.env`
2. Test API connectivity manually:
   ```bash
   curl -H "Authorization: Bearer $EMBEDDING_API_KEY" \
        $EMBEDDING_API_BASE_URL/models
   ```
3. Check API service status with provider
4. Verify firewall/proxy settings

### Problem 2: "No embedding results found for document"

**Symptoms**: 404 error when querying by document ID

**Possible Causes**:
- Document has no chunking results
- Chunking results are not in COMPLETED status
- No vectorization has been performed for this document

**Solutions**:
1. Check document's chunking status:
   ```bash
   curl http://localhost:8000/api/documents/$doc_id \
     -H "X-API-Key: $API_KEY"
   ```
2. List chunking results:
   ```bash
   curl "http://localhost:8000/api/chunking/results?document_id=$doc_id" \
     -H "X-API-Key: $API_KEY"
   ```
3. Create chunking result if missing, then vectorize

### Problem 3: Frontend Shows Empty Document List

**Symptoms**: Document selector dropdown is empty

**Possible Causes**:
- No documents have been chunked
- Backend API not responding
- CORS issues

**Solutions**:
1. Check browser console for errors
2. Verify backend is running and accessible
3. Upload and chunk at least one document
4. Check `FRONTEND_ALLOWED_ORIGINS` in backend `.env`

### Problem 4: Vectorization Fails with "Rate limit exceeded"

**Symptoms**: Status returns PARTIAL_SUCCESS or FAILED with rate limit errors

**Possible Causes**:
- Embedding API rate limit reached
- Too many concurrent requests

**Solutions**:
1. Wait for rate limit window to reset (check retry_after in response)
2. Reduce batch size (chunk document into smaller results)
3. Increase `EMBEDDING_INITIAL_DELAY` and `EMBEDDING_MAX_DELAY` in config
4. Contact API provider about rate limit increase

### Problem 5: Database Integrity Errors

**Symptoms**: Foreign key constraint errors or CHECK constraint violations

**Possible Causes**:
- Database migration not run
- Manual database modifications
- Concurrent write race conditions

**Solutions**:
1. Re-run migration:
   ```bash
   python migrations/create_embedding_results_table.py
   ```
2. Check database schema:
   ```bash
   sqlite3 app.db ".schema embedding_results"
   ```
3. Verify foreign key references exist:
   ```sql
   SELECT * FROM documents WHERE document_id = 'doc_123';
   SELECT * FROM chunking_results WHERE result_id = 'chunk_456';
   ```

---

## Performance Benchmarks

### Expected Performance Metrics

| Operation | Target | Typical Actual |
|-----------|--------|----------------|
| Vectorize 100 chunks (qwen3-embedding-8b) | <30s | 12-15s |
| Vectorize 100 chunks (bge-m3) | <30s | 8-12s |
| Query latest result by document_id | <100ms | 15-30ms |
| List 20 results with pagination | <200ms | 40-80ms |
| Dual-write 100 vectors (4096-dim) | <5s | 1.5-2.5s |
| Frontend display historical result | <500ms | 200-350ms |

### Monitoring Commands

**Check API Latency**:
```bash
time curl -X POST http://localhost:8000/api/embeddings/from-document \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "doc_123", "model": "qwen3-embedding-8b"}'
```

**Monitor Database Query Performance**:
```bash
sqlite3 app.db

sqlite> .timer ON
sqlite> SELECT * FROM embedding_results WHERE document_id = 'doc_123' ORDER BY created_at DESC LIMIT 1;
# Run time: 0.015 seconds

sqlite> .exit
```

**Check JSON File Size**:
```bash
du -h backend/results/embedding/*.json
# Typical sizes:
# - 1024-dim, 100 chunks: ~800KB
# - 4096-dim, 100 chunks: ~3.2MB
```

---

## Next Steps

After completing this quickstart:

1. **Read API Documentation**: Explore full OpenAPI specs in `contracts/` directory
2. **Review Data Model**: Understand entity relationships in `data-model.md`
3. **Study Research Decisions**: Learn about technical choices in `research.md`
4. **Implement Features**: Follow task breakdown in `tasks.md` (generated by `/speckit.tasks`)
5. **Extend Functionality**: Add new embedding models, improve error handling, or optimize performance

---

## Additional Resources

- **Feature Specification**: `specs/003-vector-embedding/spec.md`
- **Implementation Plan**: `specs/003-vector-embedding/plan.md`
- **API Contracts**: `specs/003-vector-embedding/contracts/`
- **LangChain Embeddings Docs**: https://python.langchain.com/docs/integrations/text_embedding/openai
- **TDesign Vue Next Docs**: https://tdesign.tencent.com/vue-next/overview
- **FastAPI Documentation**: https://fastapi.tiangolo.com/

---

**Status**: ✅ Quickstart guide complete. Ready for development.
