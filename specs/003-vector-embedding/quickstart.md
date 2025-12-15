# Quickstart: Vector Embedding Module

**Feature**: 003-vector-embedding  
**Audience**: Developers implementing or using the embedding service  
**Prerequisites**: Python 3.11+, FastAPI, API access credentials

## 🚀 Quick Start (5 minutes)

### 1. Installation

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Verify embedding service exists
ls backend/src/services/embedding_service.py
```

### 2. Configuration

Create or update `backend/.env`:

```bash
# API Configuration
EMBEDDING_API_KEY=your-api-key-here
EMBEDDING_API_BASE_URL=http://dev.fit-ai.woa.com/api/llmproxy
EMBEDDING_DEFAULT_MODEL=qwen3-embedding-8b

# Retry Configuration
EMBEDDING_MAX_RETRIES=3
EMBEDDING_TIMEOUT=60
EMBEDDING_INITIAL_DELAY=1
EMBEDDING_MAX_DELAY=32

# Storage Configuration
EMBEDDING_RESULTS_DIR=results/embedding
```

### 3. Start the Service

```bash
# Terminal 1: Start backend
cd backend
uvicorn src.main:app --reload --port 8000

# Terminal 2: Start frontend (optional)
cd frontend
npm run dev
```

### 4. Test Single Text Vectorization

```bash
curl -X POST http://localhost:8000/api/v1/embedding/single \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "text": "人工智能是什么",
    "model": "qwen3-embedding-8b"
  }'
```

**Expected Response**:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "SUCCESS",
  "vector": {
    "index": 0,
    "vector": [0.123, -0.456, ...],
    "dimension": 1536,
    "text_length": 18
  },
  "metadata": {
    "model": "qwen3-embedding-8b",
    "processing_time_ms": 245.7
  },
  "timestamp": "2025-12-10T10:30:45.123Z"
}
```

### 5. Test Batch Vectorization

```bash
curl -X POST http://localhost:8000/api/v1/embedding/batch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "texts": ["人工智能", "机器学习", "深度学习"],
    "model": "qwen3-embedding-8b"
  }'
```

---

## 📚 Common Use Cases

### Use Case 1: Single Query Vectorization (RAG Search)

```python
from src.services.embedding_service import EmbeddingService

# Initialize service
service = EmbeddingService(
    api_key="your-api-key",
    model="qwen3-embedding-8b",
    base_url="http://dev.fit-ai.woa.com/api/llmproxy"
)

# Vectorize user query
query = "什么是机器学习?"
vector = service.embed_query(query)

print(f"Vector dimension: {len(vector)}")
print(f"First 5 values: {vector[:5]}")

# Use vector for similarity search
# results = vector_db.search(vector, top_k=5)
```

### Use Case 2: Batch Document Processing

```python
from src.services.embedding_service import EmbeddingService
import json

# Initialize service
service = EmbeddingService(
    api_key="your-api-key",
    model="bge-m3",  # 1024-dim for smaller storage
    base_url="http://dev.fit-ai.woa.com/api/llmproxy"
)

# Process document chunks
documents = [
    "第一章：人工智能简介",
    "第二章：机器学习基础",
    "第三章：深度学习框架",
    # ... up to 1000 docs
]

# Batch vectorize
vectors = service.embed_documents(documents)

# Save results (JSON persistence per constitution)
result = {
    "document_count": len(documents),
    "model": service.model,
    "dimension": service.model_info["dimension"],
    "vectors": [
        {
            "index": i,
            "text_preview": doc[:50],
            "vector": vec
        }
        for i, (doc, vec) in enumerate(zip(documents, vectors))
    ]
}

with open("results/embedding/batch_result.json", "w") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
```

### Use Case 3: Multi-Model Comparison

```python
from src.services.embedding_service import EmbeddingService

# List available models
models = EmbeddingService.list_available_models()
for name, info in models.items():
    print(f"{name}: {info['dimension']}维, {info['description']}")

# Compare same text with different models
text = "自然语言处理技术"

for model_name in ["qwen3-embedding-8b", "bge-m3", "jina-embeddings-v4"]:
    service = EmbeddingService(
        api_key="your-api-key",
        model=model_name
    )
    
    import time
    start = time.time()
    vector = service.embed_query(text)
    duration = time.time() - start
    
    print(f"{model_name}:")
    print(f"  Dimension: {len(vector)}")
    print(f"  Latency: {duration*1000:.2f}ms")
    print(f"  First 3: {vector[:3]}")
    print()
```

### Use Case 4: Error Handling & Retries

```python
from src.services.embedding_service import EmbeddingService
import logging

logging.basicConfig(level=logging.INFO)

service = EmbeddingService(
    api_key="your-api-key",
    model="qwen3-embedding-8b",
    max_retries=5,        # Increase retries
    request_timeout=30    # Shorter timeout
)

texts = ["valid text", "", "another valid text"]  # Contains empty text

try:
    vectors = service.embed_documents(texts)
    print(f"Success: {len(vectors)} vectors generated")
except Exception as e:
    print(f"Error: {e}")
    # Check logs for retry attempts and failure details
```

---

## 🔧 API Endpoints Reference

### Single Text Vectorization

**Endpoint**: `POST /api/v1/embedding/single`

**Request**:
```json
{
  "text": "要向量化的文本",
  "model": "qwen3-embedding-8b",
  "max_retries": 3,
  "timeout": 60
}
```

**Response (Success)**:
```json
{
  "request_id": "uuid",
  "status": "SUCCESS",
  "vector": {
    "index": 0,
    "vector": [0.1, 0.2, ...],
    "dimension": 1536,
    "text_length": 21
  },
  "metadata": {
    "model": "qwen3-embedding-8b",
    "processing_time_ms": 245.7
  },
  "timestamp": "2025-12-10T10:30:45Z"
}
```

### Batch Vectorization

**Endpoint**: `POST /api/v1/embedding/batch`

**Request**:
```json
{
  "texts": ["文本1", "文本2", "文本3"],
  "model": "bge-m3",
  "max_retries": 3,
  "timeout": 60
}
```

**Response (Partial Success)**:
```json
{
  "request_id": "uuid",
  "status": "PARTIAL_SUCCESS",
  "vectors": [
    {
      "index": 0,
      "vector": [0.1, 0.2, ...],
      "dimension": 1024,
      "text_length": 9
    },
    {
      "index": 2,
      "vector": [0.3, 0.4, ...],
      "dimension": 1024,
      "text_length": 9
    }
  ],
  "failures": [
    {
      "index": 1,
      "text_preview": "   ",
      "error_type": "INVALID_TEXT_ERROR",
      "error_message": "Text contains only whitespace",
      "retry_recommended": false,
      "retry_count": 0
    }
  ],
  "metadata": {
    "model": "bge-m3",
    "batch_size": 3,
    "successful_count": 2,
    "failed_count": 1,
    "processing_time_ms": 512.3
  },
  "timestamp": "2025-12-10T10:30:46Z"
}
```

### List Models

**Endpoint**: `GET /api/v1/models`

**Response**:
```json
{
  "models": [
    {
      "name": "qwen3-embedding-8b",
      "dimension": 1536,
      "description": "通义千问 Embedding 模型,8B 参数",
      "provider": "qwen",
      "supports_multilingual": true
    },
    ...
  ],
  "count": 4
}
```

### Get Model Info

**Endpoint**: `GET /api/v1/models/{model_name}`

**Response**:
```json
{
  "name": "bge-m3",
  "dimension": 1024,
  "description": "BGE-M3 多语言模型,支持中英文,性能优秀",
  "provider": "bge",
  "supports_multilingual": true,
  "max_batch_size": 1000
}
```

---

## 🧪 Testing

### Run Unit Tests

```bash
cd backend
pytest tests/unit/test_embedding_service.py -v
```

### Run Integration Tests

```bash
pytest tests/integration/test_embedding_api.py -v
```

### Test Coverage

```bash
pytest --cov=src.services.embedding_service --cov-report=html
open htmlcov/index.html
```

---

## 🎯 Frontend Integration

### Vue 3 Component Example

```vue
<template>
  <div class="embedding-panel">
    <t-form @submit="handleSubmit">
      <t-form-item label="模型选择">
        <t-select v-model="selectedModel">
          <t-option
            v-for="model in models"
            :key="model.name"
            :value="model.name"
            :label="`${model.name} (${model.dimension}维)`"
          />
        </t-select>
      </t-form-item>

      <t-form-item label="文本输入">
        <t-textarea
          v-model="text"
          placeholder="输入要向量化的文本"
          :rows="5"
        />
      </t-form-item>

      <t-button type="submit" :loading="loading">
        向量化
      </t-button>
    </t-form>

    <div v-if="result" class="result-display">
      <h3>向量结果 (维度: {{ result.vector.dimension }})</h3>
      <pre>{{ result.vector.vector.slice(0, 10) }}...</pre>
      <p>处理时间: {{ result.metadata.processing_time_ms }}ms</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { embeddingService } from '@/services/embeddingService'

const models = ref([])
const selectedModel = ref('qwen3-embedding-8b')
const text = ref('')
const loading = ref(false)
const result = ref(null)

onMounted(async () => {
  models.value = await embeddingService.listModels()
})

const handleSubmit = async () => {
  loading.value = true
  try {
    result.value = await embeddingService.embedSingle({
      text: text.value,
      model: selectedModel.value
    })
  } catch (error) {
    console.error('Embedding failed:', error)
  } finally {
    loading.value = false
  }
}
</script>
```

### API Service (`embeddingService.js`)

```javascript
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
const API_KEY = import.meta.env.VITE_API_KEY

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
  }
})

export const embeddingService = {
  async embedSingle({ text, model, max_retries = 3, timeout = 60 }) {
    const response = await client.post('/embedding/single', {
      text,
      model,
      max_retries,
      timeout
    })
    return response.data
  },

  async embedBatch({ texts, model, max_retries = 3, timeout = 60 }) {
    const response = await client.post('/embedding/batch', {
      texts,
      model,
      max_retries,
      timeout
    })
    return response.data
  },

  async listModels() {
    const response = await client.get('/models')
    return response.data.models
  },

  async getModelInfo(modelName) {
    const response = await client.get(`/models/${modelName}`)
    return response.data
  }
}
```

---

## 🐛 Troubleshooting

### Issue: "Model not found" error

**Solution**: Check model name matches exactly:
```bash
curl http://localhost:8000/api/v1/models
```
Valid models: `qwen3-embedding-8b`, `bge-m3`, `hunyuan-embedding`, `jina-embeddings-v4`

### Issue: "Batch size limit exceeded"

**Solution**: Split large batches:
```python
def chunk_texts(texts, chunk_size=1000):
    for i in range(0, len(texts), chunk_size):
        yield texts[i:i + chunk_size]

# Process in chunks
all_vectors = []
for chunk in chunk_texts(large_text_list, 1000):
    vectors = service.embed_documents(chunk)
    all_vectors.extend(vectors)
```

### Issue: Rate limiting errors

**Solution**: Exponential backoff is automatic, but you can:
1. Increase `max_retries` in request
2. Reduce batch size to lower API load
3. Check API rate limits with provider

### Issue: Dimension mismatch

**Solution**: Verify model configuration:
```python
# Check expected dimensions
service = EmbeddingService(model="bge-m3", ...)
print(service.get_model_info())
# Should show: dimension=1024

# If API returns wrong dimension, check:
# 1. API endpoint correctness
# 2. Model name spelling
# 3. API provider model availability
```

---

## 📊 Performance Tuning

### Batch Size Optimization

```python
import time

# Test different batch sizes
for batch_size in [10, 50, 100, 500, 1000]:
    texts = ["sample text"] * batch_size
    
    start = time.time()
    vectors = service.embed_documents(texts)
    duration = time.time() - start
    
    throughput = batch_size / duration
    print(f"Batch {batch_size}: {throughput:.2f} docs/sec")
```

### Concurrent Requests (Advanced)

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def embed_batch_async(texts, model):
    # Use ThreadPoolExecutor for sync API
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        service = EmbeddingService(model=model, ...)
        return await loop.run_in_executor(
            pool, 
            service.embed_documents, 
            texts
        )

# Process multiple batches concurrently
batches = [batch1, batch2, batch3]
results = await asyncio.gather(*[
    embed_batch_async(batch, "qwen3-embedding-8b")
    for batch in batches
])
```

---

## 📖 Next Steps

1. **Implement Backend**: Follow [data-model.md](./data-model.md) and [OpenAPI spec](./contracts/openapi.yaml)
2. **Add Frontend UI**: Use Vue 3 + TDesign components as shown above
3. **Write Tests**: Cover edge cases (empty text, rate limits, dimension mismatch)
4. **Monitor Logs**: Check operational metrics in structured JSON logs
5. **Integrate with Vector DB**: Use generated vectors for similarity search

## 🔗 Resources

- [Feature Spec](./spec.md) - Complete requirements
- [Research Findings](./research.md) - Technical decisions
- [Data Model](./data-model.md) - Entity definitions
- [API Contract](./contracts/openapi.yaml) - OpenAPI specification
- [Constitution](../../.specify/memory/constitution.md) - Project principles
