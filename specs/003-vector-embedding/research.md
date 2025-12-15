# Research: Vector Embedding Module

**Feature**: 003-vector-embedding  
**Date**: 2025-12-10  
**Phase**: 0 - Research & Decision Making

## Overview

This document consolidates research findings and technical decisions for the Vector Embedding Module implementation. All unknowns from Technical Context have been resolved through best practices analysis and technology evaluation.

---

## 1. Exponential Backoff Strategy for Rate Limiting

### Decision
Implement exponential backoff with jitter using the following parameters:
- **Initial delay**: 1 second
- **Max delay**: 32 seconds
- **Backoff multiplier**: 2x
- **Jitter**: ±25% randomization
- **Max retries**: 3 attempts (from constitution)
- **Timeout**: 60 seconds total (from constitution)

### Rationale
- **Industry standard**: Used by AWS SDK, OpenAI Python client, Google Cloud libraries
- **Prevents thundering herd**: Jitter spreads retry attempts across time
- **Respects rate limits**: Exponential growth gives API time to recover
- **Fast recovery**: 1s initial delay minimizes latency for transient errors
- **Bounded wait**: 32s max delay prevents indefinite blocking

### Implementation Approach
```python
import time
import random

def exponential_backoff_retry(func, max_retries=3, initial_delay=1, max_delay=32):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            delay = min(initial_delay * (2 ** attempt), max_delay)
            jitter = delay * random.uniform(-0.25, 0.25)
            time.sleep(delay + jitter)
```

### Alternatives Considered
- **Fixed delay**: Rejected - doesn't adapt to sustained load
- **Linear backoff**: Rejected - too slow for high-frequency rate limits
- **No jitter**: Rejected - causes synchronized retries (thundering herd)

### References
- AWS SDK Retry Strategy: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
- OpenAI Python client implementation: https://github.com/openai/openai-python
- Google Cloud Best Practices: https://cloud.google.com/apis/design/errors

---

## 2. Batch Processing Partial Failure Handling

### Decision
Return structured partial success response with clear failure identification:
```json
{
  "status": "partial_success",
  "total": 100,
  "successful": 98,
  "failed": 2,
  "vectors": [...],  // 98 successful vectors
  "failures": [
    {
      "index": 45,
      "text_preview": "First 50 chars...",
      "error_type": "InvalidTextError",
      "error_message": "Text contains only whitespace",
      "retry_recommended": false
    },
    {
      "index": 73,
      "text_preview": "First 50 chars...",
      "error_type": "APITimeoutError",
      "error_message": "Request timed out after 5s",
      "retry_recommended": true
    }
  ]
}
```

### Rationale
- **Maximizes throughput**: Processes 98% of valid data instead of failing entire batch
- **Clear diagnostics**: Users can identify and fix specific failed items
- **Retry guidance**: `retry_recommended` flag helps automation decisions
- **Preserves order**: Index mapping allows reconstruction of original batch order
- **Production pattern**: Matches Stripe API, AWS Batch, Google Cloud Batch behavior

### Implementation Approach
- Process all documents sequentially in batch
- Catch individual document errors without interrupting batch
- Accumulate failures with full context (index, error, text preview)
- Return combined result with success/failure counts

### Alternatives Considered
- **Fail entire batch**: Rejected - wastes computation, poor UX for large batches
- **Silent skipping**: Rejected - users unaware of failures, data loss risk
- **Async retry queue**: Rejected - adds complexity, out of scope for MVP

---

## 3. Operational Logging Design

### Decision
Implement structured JSON logging with the following metrics:
- **Request metrics**: request_id, timestamp, duration_ms, model_name
- **Batch metrics**: batch_size, successful_count, failed_count
- **Performance metrics**: api_latency_ms, processing_time_ms, vectors_per_second
- **Error metrics**: error_type, error_message, retry_count, retry_successful
- **Rate limit metrics**: rate_limit_hit, backoff_delay_ms, total_retry_time_ms

**Log levels**:
- INFO: Successful requests, batch summaries
- WARNING: Retries, partial failures, rate limits
- ERROR: Complete failures, validation errors, API errors

### Rationale
- **Structured logging**: JSON format enables log aggregation tools (ELK, Splunk, CloudWatch)
- **Performance monitoring**: Latency metrics enable SLA tracking and alerting
- **Troubleshooting**: Request IDs enable end-to-end tracing
- **Capacity planning**: Throughput metrics inform scaling decisions
- **No sensitive data**: Text content excluded (privacy & cost considerations)

### Implementation Approach
```python
import logging
import json
from datetime import datetime

logger = logging.getLogger("embedding_service")

def log_embedding_request(request_id, model, duration, batch_size, success_count, failed_count):
    logger.info(json.dumps({
        "event": "embedding_request",
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),
        "model": model,
        "duration_ms": duration,
        "batch_size": batch_size,
        "successful": success_count,
        "failed": failed_count,
        "success_rate": success_count / batch_size if batch_size > 0 else 0
    }))
```

### Alternatives Considered
- **Verbose logging (log text content)**: Rejected - privacy concerns, log bloat, cost
- **Minimal logging (errors only)**: Rejected - insufficient for performance monitoring
- **Metrics-only (no logs)**: Rejected - loses troubleshooting context

### References
- OpenTelemetry Logging Standard: https://opentelemetry.io/docs/specs/otel/logs/
- Twelve-Factor App Logging: https://12factor.net/logs
- Structured Logging Best Practices: https://www.datadoghq.com/blog/structured-logging/

---

## 4. Vector Dimension Validation

### Decision
Implement strict dimension validation with immediate failure:
```python
def validate_vector_dimensions(vector, expected_dim, model_name):
    actual_dim = len(vector)
    if actual_dim != expected_dim:
        raise VectorDimensionMismatchError(
            f"Model '{model_name}' returned vector with {actual_dim} dimensions, "
            f"expected {expected_dim}. This may indicate API version mismatch or "
            f"model misconfiguration. Please verify model settings."
        )
    return vector
```

### Rationale
- **Data integrity**: Wrong dimensions corrupt vector database, break search
- **Fail fast**: Immediate detection prevents silent data corruption
- **Clear diagnostics**: Error message includes expected vs actual for debugging
- **API contract enforcement**: Ensures API provider compliance

### Implementation Approach
- Validate every vector immediately after API response
- Include model name and dimensions in error context
- Fail entire request if any vector has wrong dimensions
- Log dimension mismatch events for monitoring

### Alternatives Considered
- **Padding/truncation**: Rejected - destroys semantic meaning, unpredictable search behavior
- **Warning only**: Rejected - silent data corruption, difficult to detect later
- **Skip invalid vectors**: Rejected - violates user expectations, data loss

---

## 5. Batch Size Limit Enforcement

### Decision
Maximum batch size: **1000 documents per request**

**Validation approach**:
- Pre-request validation: Reject batches >1000 before API call
- Clear error message: "Batch size {size} exceeds maximum limit of 1000. Please split into smaller batches."
- Suggested chunking: Error response includes guidance on splitting batches

### Rationale
- **Memory safety**: Prevents OOM errors with large batches
- **API reliability**: Most embedding APIs have similar limits (OpenAI: 2048, Cohere: 96, HuggingFace: varies)
- **Timeout prevention**: 1000 docs @ 30s = 33ms/doc, reasonable for API round-trip
- **User control**: Forces explicit chunking, prevents accidental large requests

### Implementation Approach
```python
MAX_BATCH_SIZE = 1000

def validate_batch_size(texts):
    if len(texts) > MAX_BATCH_SIZE:
        raise BatchSizeLimitError(
            f"Batch size {len(texts)} exceeds maximum limit of {MAX_BATCH_SIZE}. "
            f"Please split your request into {(len(texts) + MAX_BATCH_SIZE - 1) // MAX_BATCH_SIZE} batches."
        )
```

### Alternatives Considered
- **Unlimited batches**: Rejected - OOM risk, timeout issues
- **Auto-chunking**: Rejected - hides behavior, complicates error handling
- **Lower limit (100)**: Rejected - too restrictive, excessive API calls

---

## 6. JSON Result Persistence Format

### Decision
Per-request JSON file with naming: `embedding_{request_id}_{timestamp}.json`

**Structure**:
```json
{
  "metadata": {
    "request_id": "uuid-v4",
    "timestamp": "2025-12-10T10:30:45.123Z",
    "model": "qwen3-embedding-8b",
    "model_dimension": 1536,
    "batch_size": 100,
    "successful_count": 98,
    "failed_count": 2,
    "processing_time_ms": 2847
  },
  "vectors": [
    {
      "index": 0,
      "text_hash": "sha256-hash",
      "text_length": 245,
      "vector": [0.123, -0.456, ...],
      "dimension": 1536
    }
  ],
  "failures": [
    {
      "index": 45,
      "error_type": "InvalidTextError",
      "error_message": "Text contains only whitespace"
    }
  ],
  "config": {
    "api_endpoint": "http://dev.fit-ai.woa.com/api/llmproxy",
    "max_retries": 3,
    "timeout_seconds": 60
  }
}
```

### Rationale
- **Constitution compliance**: Meets JSON persistence requirement
- **Traceability**: Request ID enables linking to logs and downstream processing
- **Reproducibility**: Config section allows exact reproduction
- **Text privacy**: Store hash instead of full text (unless explicitly enabled)
- **Metadata richness**: Supports analytics and debugging

### Implementation Approach
- Write JSON after successful vectorization
- Atomic write (tmp file + rename) prevents partial files
- Directory structure: `results/embedding/YYYY-MM-DD/`
- Optional compression for large batches

### Alternatives Considered
- **One file per vector**: Rejected - excessive file count, poor performance
- **Append to single file**: Rejected - concurrent write issues, large file management
- **Database only**: Rejected - violates constitution requirement

---

## 7. Error Classification & Recovery Strategy

### Decision
Three-tier error classification for recovery decisions:

**Tier 1 - Retryable (Auto-retry with backoff)**:
- `RateLimitError`: API rate limits
- `APITimeoutError`: Request timeouts
- `NetworkError`: Connection failures
- `ServiceUnavailableError`: 503 responses

**Tier 2 - Non-retryable (Fail immediately)**:
- `AuthenticationError`: Invalid API key
- `ModelNotFoundError`: Unsupported model
- `InvalidTextError`: Empty or malformed text
- `BatchSizeLimitError`: Exceeds 1000 docs
- `VectorDimensionMismatchError`: Wrong dimensions

**Tier 3 - Partial retry (Document-level)**:
- `SingleDocumentError`: Individual text issues in batch
- Continue processing remaining documents

### Rationale
- **Efficiency**: Don't retry permanent failures
- **Reliability**: Automatically recover from transient errors
- **User experience**: Clear distinction between fixable and permanent errors
- **Cost optimization**: Avoid wasted API calls

### Implementation Approach
```python
RETRYABLE_ERRORS = {RateLimitError, APITimeoutError, NetworkError, ServiceUnavailableError}

def is_retryable(error):
    return type(error) in RETRYABLE_ERRORS

def handle_embedding_error(error, attempt, max_retries):
    if is_retryable(error) and attempt < max_retries:
        return "retry"
    else:
        return "fail"
```

---

## 8. LangChain Integration Best Practices

### Decision
Use LangChain's `OpenAIEmbeddings` class with custom retry logic wrapper:
- **Preserve interface**: Maintain compatibility with LangChain ecosystem
- **Override retry**: Implement custom exponential backoff (LangChain's is simpler)
- **Add logging**: Inject operational metrics at wrapper level
- **Maintain testability**: Wrapper enables mocking for tests

### Rationale
- **Ecosystem compatibility**: Works with LangChain vector stores, chains
- **OpenAI protocol**: Supports all OpenAI-compatible embedding APIs
- **Proven library**: Battle-tested, well-documented, active maintenance
- **Extensibility**: Easy to swap providers or add custom logic

### Implementation Approach
```python
from langchain_openai import OpenAIEmbeddings

class EnhancedEmbeddingService:
    def __init__(self, model, api_key, base_url):
        self._embeddings = OpenAIEmbeddings(
            model=model,
            openai_api_key=api_key,
            openai_api_base=base_url,
            max_retries=0  # Disable LangChain retries, use our own
        )
        self._retry_handler = ExponentialBackoffRetry()
        self._logger = EmbeddingLogger()
    
    def embed_query(self, text):
        return self._retry_handler.execute(
            lambda: self._embeddings.embed_query(text)
        )
```

### Alternatives Considered
- **Direct OpenAI SDK**: Rejected - less flexible for multi-provider support
- **Custom HTTP client**: Rejected - reinventing wheel, more maintenance
- **HuggingFace Transformers**: Rejected - requires local model hosting

---

## Summary of Key Decisions

| Topic | Decision | Impact |
|-------|----------|--------|
| Retry Strategy | Exponential backoff with jitter (1s-32s, 3 retries) | High reliability, respects rate limits |
| Partial Failures | Process valid docs, return structured failure details | Maximizes throughput, clear diagnostics |
| Logging | Structured JSON with metrics, no text content | Production observability, privacy-safe |
| Dimension Validation | Fail immediately with clear error | Data integrity, fail fast |
| Batch Limit | 1000 documents maximum | Memory safety, timeout prevention |
| Persistence | JSON per request with metadata | Constitution compliance, traceability |
| Error Classification | 3-tier retry strategy (auto/fail/partial) | Efficiency, user experience |
| LangChain Integration | Wrapped OpenAIEmbeddings with custom logic | Ecosystem compatibility, extensibility |

All technical unknowns from Phase 0 have been resolved. Ready to proceed to Phase 1 (Design & Contracts).
