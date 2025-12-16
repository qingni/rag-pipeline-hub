# Quickstart: Vector Embedding Module

**Feature**: 003-vector-embedding  
**Date**: 2025-12-15  
**Purpose**: Developer quickstart guide for implementing and using the vector embedding module

---

## Prerequisites

### Environment Setup

**Backend Requirements**:
```bash
# Python 3.9+
python --version  # Should be >= 3.9

# Install dependencies
cd backend
pip install -r requirements.txt

# Required environment variables
export EMBEDDING_API_KEY="your-api-key-here"
export EMBEDDING_API_BASE_URL="http://dev.fit-ai.woa.com/api/llmproxy"  # Optional, has default
export EMBEDDING_RESULTS_DIR="results/embedding"  # Optional, has default
```

**Frontend Requirements**:
```bash
# Node.js 16+
node --version  # Should be >= 16

# Install dependencies
cd frontend
npm install
```

**Database Setup**:
```bash
# Apply database migrations (chunking tables must exist)
cd backend
alembic upgrade head
```

---

## Quick Start (5 minutes)

### Step 1: Start Backend Server

```bash
cd backend
uvicorn src.main:app --reload --port 8000
```

**Verify health check**:
```bash
curl http://localhost:8000/embedding/health
# Expected: {"status": "healthy", "api_connectivity": true, ...}
```

### Step 2: Start Frontend Server

```bash
cd frontend
npm run dev
```

**Open browser**: http://localhost:5173

### Step 3: Use Unified Embedding Interface

1. Navigate to **"文档向量化"** in left sidebar
2. Select a document from dropdown (only documents with chunking results appear)
3. Select an embedding model (e.g., "Qwen3-Embedding-8B · 1536维 · 通义千问模型")
4. Click **"开始向量化"** button
5. View results in right panel (vectors, metadata, processing time)

---

## API Usage Examples

### Example 1: Embed from Chunking Result (Primary Use Case)

**Scenario**: You have a completed chunking result and want to vectorize all chunks.

```python
import requests

# Prepare request
payload = {
    "result_id": "your-chunking-result-id",
    "document_id": "your-document-id",  # Optional, for display
    "model": "qwen3-embedding-8b"
}

# Call API
response = requests.post(
    "http://localhost:8000/embedding/from-chunking-result",
    json=payload,
    headers={"X-API-Key": "your-api-key"}
)

# Parse response
result = response.json()
print(f"Status: {result['status']}")
print(f"Vectors: {len(result['vectors'])}")
print(f"Failures: {len(result['failures'])}")
print(f"Processing time: {result['metadata']['processing_time_ms']}ms")

# Access individual vectors
for vector_data in result['vectors']:
    index = vector_data['index']
    vector = vector_data['vector']  # Array of floats
    dimension = vector_data['dimension']  # e.g., 1536
    print(f"Chunk {index}: {dimension}-dim vector")
```

**cURL Example**:
```bash
curl -X POST http://localhost:8000/embedding/from-chunking-result \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "result_id": "result-abc-123",
    "model": "bge-m3"
  }'
```

---

### Example 2: Embed from Document (Automatic Latest Result)

**Scenario**: You want to vectorize a document's latest chunking result without knowing the result ID.

```python
import requests

payload = {
    "document_id": "your-document-id",
    "model": "bge-m3"
}

response = requests.post(
    "http://localhost:8000/embedding/from-document",
    json=payload
)

result = response.json()
print(f"Used chunking result: {result['metadata']['config']}")
print(f"Generated {len(result['vectors'])} vectors")
```

**With Strategy Filter**:
```python
payload = {
    "document_id": "your-document-id",
    "model": "bge-m3",
    "strategy_type": "SEMANTIC"  # Only use semantic chunking results
}
```

---

### Example 3: Single Text Embedding (Backend-only)

**Scenario**: Ad-hoc query vectorization for testing or API integration.

```python
import requests

payload = {
    "text": "人工智能是什么?",
    "model": "qwen3-embedding-8b"
}

response = requests.post(
    "http://localhost:8000/embedding/single",
    json=payload
)

result = response.json()
vector = result['vector']['vector']
print(f"Generated {len(vector)}-dimensional vector")
print(f"Text hash: {result['vector']['text_hash']}")
```

---

### Example 4: Batch Text Embedding (Backend-only)

**Scenario**: Vectorize multiple arbitrary texts without chunking.

```python
import requests

payload = {
    "texts": [
        "First document content",
        "Second document content",
        "Third document content"
    ],
    "model": "hunyuan-embedding",
    "max_retries": 5,
    "timeout": 120
}

response = requests.post(
    "http://localhost:8000/embedding/batch",
    json=payload
)

result = response.json()

# Handle partial success
if result['status'] == 'partial_success':
    print(f"Successful: {result['metadata']['successful_count']}")
    print(f"Failed: {result['metadata']['failed_count']}")
    
    # Process failures
    for failure in result['failures']:
        print(f"Index {failure['index']}: {failure['error_message']}")
        if failure['retry_recommended']:
            print("  → Retry recommended")
```

---

## Frontend Integration

### Component Structure

```
src/
├── views/
│   └── DocumentEmbedding.vue       # Main page at /documents/embed
├── components/
│   └── embedding/
│       ├── DocumentSelector.vue    # Document dropdown (filters chunked docs)
│       ├── ModelSelector.vue       # Model selection with detail panel
│       └── EmbeddingResults.vue    # Results display panel
├── stores/
│   └── embedding.js                # Pinia state management
└── services/
    └── embeddingService.js         # API client
```

### Using the Embedding Store

```javascript
// In a Vue component
import { useEmbeddingStore } from '@/stores/embedding'

export default {
  setup() {
    const embeddingStore = useEmbeddingStore()
    
    // Fetch documents with chunking results
    onMounted(async () => {
      await embeddingStore.fetchDocumentsWithChunking()
    })
    
    // Start embedding
    const startEmbedding = async () => {
      if (!embeddingStore.canStartEmbedding) {
        return  // Validation failed
      }
      
      await embeddingStore.startEmbedding()
      
      if (embeddingStore.error) {
        // Handle error
        console.error(embeddingStore.error)
      } else {
        // Success
        const result = embeddingStore.currentResult
        console.log(`Generated ${result.vectors.length} vectors`)
      }
    }
    
    return {
      embeddingStore,
      startEmbedding
    }
  }
}
```

### API Service Methods

```javascript
// services/embeddingService.js

export const embeddingService = {
  // Get documents with active chunking results
  async getDocumentsWithChunking() {
    const response = await api.get('/documents', {
      params: { has_chunking_result: true }
    })
    return response.data
  },
  
  // Get available models
  async getModels() {
    const response = await api.get('/embedding/models')
    return response.data.models
  },
  
  // Embed from document
  async embedDocument(payload) {
    const response = await api.post('/embedding/from-document', payload)
    return response.data
  },
  
  // Embed from chunking result
  async embedChunkingResult(payload) {
    const response = await api.post('/embedding/from-chunking-result', payload)
    return response.data
  }
}
```

---

## Error Handling

### Common Error Scenarios

#### 1. Invalid API Key
```json
{
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "message": "Invalid API key. Please check your credentials."
  }
}
```
**Solution**: Set correct `EMBEDDING_API_KEY` environment variable.

#### 2. Chunking Result Not Found
```json
{
  "error": {
    "code": "CHUNKING_RESULT_NOT_FOUND",
    "message": "Chunking result abc-123 not found or not completed"
  }
}
```
**Solution**: Verify chunking result exists and has `status = COMPLETED`.

#### 3. Rate Limit Exceeded
```json
{
  "error": {
    "code": "RATE_LIMIT_ERROR",
    "message": "Rate limit exceeded",
    "details": {
      "retry_after_seconds": 30
    }
  }
}
```
**Solution**: System automatically retries with exponential backoff. If all retries fail, wait specified time and retry manually.

#### 4. Dimension Mismatch
```json
{
  "error": {
    "code": "DIMENSION_MISMATCH_ERROR",
    "message": "Vector dimension mismatch: expected 1536, got 768",
    "details": {
      "expected": 1536,
      "actual": 768,
      "model": "qwen3-embedding-8b"
    }
  }
}
```
**Solution**: Check API configuration, verify model name matches API deployment.

---

## Testing

### Backend Unit Tests

```bash
cd backend
pytest tests/test_embedding_service.py -v
pytest tests/test_embedding_routes.py -v
```

### Integration Test Example

```python
# tests/test_embedding_integration.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_embed_from_chunking_result():
    # Setup: Create test document and chunking result
    # (Assume fixtures exist)
    
    response = client.post("/embedding/from-chunking-result", json={
        "result_id": "test-result-id",
        "model": "bge-m3"
    })
    
    assert response.status_code == 200
    result = response.json()
    assert result['status'] == 'success'
    assert len(result['vectors']) > 0
    assert result['metadata']['model'] == 'bge-m3'
```

### Frontend Component Tests

```bash
cd frontend
npm test
```

---

## Performance Optimization

### Best Practices

1. **Batch Size Optimization**
   ```python
   # For large documents, process in chunks of 100-500 items
   chunk_size = 500
   for i in range(0, len(chunks), chunk_size):
       batch = chunks[i:i+chunk_size]
       embed_batch(batch)
   ```

2. **Model Selection**
   - **Small documents (<100 chunks)**: Use higher-dimension models (Qwen3-Embedding-8B, 1536-dim)
   - **Large documents (>500 chunks)**: Use lower-dimension models (BGE-M3, 1024-dim) for faster processing

3. **Retry Configuration**
   ```python
   # For stable networks
   payload = {
       "max_retries": 2,
       "timeout": 30
   }
   
   # For unstable networks
   payload = {
       "max_retries": 5,
       "timeout": 120
   }
   ```

4. **Frontend Caching**
   ```javascript
   // Cache model list in Pinia store
   const embeddingStore = useEmbeddingStore()
   if (embeddingStore.availableModels.length === 0) {
     await embeddingStore.fetchModels()  // Only fetch once
   }
   ```

---

## Monitoring and Logging

### Operational Metrics

**Backend Logs** (check `logs/` directory):
```
[INFO] Embedding request started: model=qwen3-embedding-8b, batch_size=50
[INFO] Request complete: duration=2345ms, vectors=50, failures=0, retries=1
[WARN] Rate limit hit: retry_after=30s, attempt=2/3
```

**Key Metrics to Monitor**:
- Request latency (target: <30s for 100 chunks)
- Retry rate (target: <5%)
- Rate limit hit rate (target: <10%)
- Partial success rate (target: >90% full success)

### Health Check Monitoring

```bash
# Add to your monitoring script
while true; do
  curl -s http://localhost:8000/embedding/health | jq '.status'
  sleep 30
done
```

---

## Troubleshooting

### Issue: Frontend shows "No documents available"

**Diagnosis**:
1. Check if documents exist: `curl http://localhost:8000/documents`
2. Check if chunking results exist: Query database or check `results/chunking/`
3. Verify documents have `status=COMPLETED` chunking results

**Solution**: Complete chunking workflow first before attempting embedding.

---

### Issue: All requests fail with timeout

**Diagnosis**:
1. Check API connectivity: `curl http://dev.fit-ai.woa.com/api/llmproxy/health`
2. Check network: `ping dev.fit-ai.woa.com`
3. Check API key validity

**Solution**:
- Increase timeout: `"timeout": 120`
- Check firewall/VPN settings
- Verify API key with provider

---

### Issue: Vectors have incorrect dimensions

**Diagnosis**:
```python
# Check model configuration
response = requests.get("http://localhost:8000/embedding/models/qwen3-embedding-8b")
print(response.json()['dimension'])  # Should match actual vectors
```

**Solution**: Verify model name in API matches deployed model on embedding service.

---

## Next Steps

1. **Phase 2 Implementation**: Implement backend service methods and API routes
2. **Phase 3 Testing**: Write comprehensive unit and integration tests
3. **Phase 4 Frontend**: Implement unified embedding interface
4. **Phase 5 Optimization**: Add caching, batch processing improvements
5. **Phase 6 Monitoring**: Set up operational dashboards

---

## Additional Resources

- **API Documentation**: See `contracts/api-contract.yaml` for full OpenAPI spec
- **Data Model**: See `data-model.md` for entity definitions
- **Research**: See `research.md` for design decisions and alternatives
- **Specification**: See `spec.md` for complete feature requirements

---

**Support**: For questions or issues, contact the RAG Framework team or open an issue in the repository.
