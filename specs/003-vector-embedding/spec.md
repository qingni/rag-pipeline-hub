# Feature Specification: Vector Embedding Module

**Feature Branch**: `003-vector-embedding`  
**Created**: 2025-12-10  
**Status**: Draft  
**Input**: User description: "新建个分支,帮我实现向量嵌入模块。使用哪些嵌入模型以及如何使用可以参考embedding_service.py代码"

## Clarifications

### Session 2025-12-10

- Q: When one document in a batch fails, should the system process remaining valid documents (partial success) or fail the entire batch (atomic operation)? → A: Continue processing valid documents, return partial success with failed items identified
- Q: What is the maximum number of documents allowed in a single batch request? → A: 1000 documents maximum
- Q: When the API returns a rate limit error, how should the system respond? → A: Retry with exponential backoff within timeout period
- Q: What level of operational logging should the embedding service provide? → A: Standard: Log request counts, latencies, model used, error rates, batch sizes
- Q: When the API returns a vector with unexpected dimensions, how should the system respond? → A: Fail immediately with clear error indicating expected vs actual dimensions

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Single Text Vectorization (Priority: P1)

As a RAG system user, I need to convert a single query text into a vector representation so that I can perform semantic search against document collections.

**Why this priority**: This is the core functionality that enables semantic search. Without it, the RAG system cannot function. This represents the minimum viable product.

**Independent Test**: Can be fully tested by providing a text string and verifying a vector is returned with the expected dimensions. Delivers immediate value for basic search capabilities.

**Acceptance Scenarios**:

1. **Given** a text query "人工智能是什么", **When** the user requests vectorization, **Then** the system returns a numerical vector of the model's expected dimension
2. **Given** an empty text string, **When** the user requests vectorization, **Then** the system returns an appropriate error message
3. **Given** a very long text (>10000 characters), **When** the user requests vectorization, **Then** the system either processes it successfully or returns a clear length limitation error

---

### User Story 2 - Batch Document Vectorization (Priority: P2)

As a document processing pipeline, I need to convert multiple documents into vectors in a single request so that I can efficiently process large document collections.

**Why this priority**: Batch processing significantly improves performance and reduces API costs. Critical for production usage but the system can function with single-text processing.

**Independent Test**: Can be tested by providing a list of text documents and verifying all are vectorized with consistent dimensions. Demonstrates clear performance improvement over sequential single-text processing.

**Acceptance Scenarios**:

1. **Given** a list of 100 documents, **When** batch vectorization is requested, **Then** the system returns 100 vectors with consistent dimensions
2. **Given** a batch containing one invalid document, **When** batch vectorization is requested, **Then** the system processes all valid documents and returns partial success with failed items clearly identified (including error reasons and document indices)
3. **Given** an empty document list, **When** batch vectorization is requested, **Then** the system returns an appropriate error or empty result
4. **Given** a batch with more than 1000 documents, **When** batch vectorization is requested, **Then** the system rejects the request with a clear error message indicating the maximum batch size limit

---

### User Story 3 - Multi-Model Support (Priority: P1)

As a system administrator, I need to choose from multiple embedding models (BGE-M3, Qwen3-Embedding-8B, Hunyuan-Embedding, Jina-Embeddings-v4) so that I can optimize for different use cases (multilingual support, dimension size, performance).

**Why this priority**: Different use cases require different models. This flexibility is essential for production deployment across various scenarios.

**Independent Test**: Can be tested by initializing the service with each supported model and verifying vectors are generated with correct dimensions. Each model can be validated independently.

**Acceptance Scenarios**:

1. **Given** the model name "qwen3-embedding-8b", **When** service is initialized, **Then** vectors are generated with 1536 dimensions
2. **Given** the model name "bge-m3", **When** service is initialized, **Then** vectors are generated with 1024 dimensions
3. **Given** the model name "hunyuan-embedding", **When** service is initialized, **Then** vectors are generated with 1024 dimensions
4. **Given** the model name "jina-embeddings-v4", **When** service is initialized, **Then** vectors are generated with 768 dimensions
5. **Given** an unsupported model name, **When** service initialization is attempted, **Then** the system returns a clear error listing supported models

---

### User Story 4 - Model Information Query (Priority: P3)

As a developer, I need to query the current model's information (name, dimensions, description) and list all available models so that I can make informed decisions about model selection.

**Why this priority**: Helpful for debugging and decision-making but not essential for core functionality. Can be added after basic vectorization works.

**Independent Test**: Can be tested by calling model information methods and verifying returned data matches expected structure. Provides value for operational visibility.

**Acceptance Scenarios**:

1. **Given** a service instance with model "qwen3-embedding-8b", **When** model info is requested, **Then** the system returns name, dimension (1536), and description
2. **Given** any service state, **When** listing available models is requested, **Then** the system returns all four supported models with their specifications

---

### User Story 5 - Error Recovery and Retries (Priority: P2)

As a system operator, I need the embedding service to automatically retry failed requests so that temporary network issues don't cause system failures.

**Why this priority**: Essential for production reliability but the basic functionality can work without it initially. Significantly improves system robustness.

**Independent Test**: Can be tested by simulating network failures and verifying retry behavior. Demonstrates clear improvement in system reliability.

**Acceptance Scenarios**:

1. **Given** a temporary network failure, **When** embedding is requested, **Then** the system retries up to the configured maximum attempts
2. **Given** a persistent API failure, **When** maximum retries are exhausted, **Then** the system returns a clear error message
3. **Given** a timeout scenario, **When** request exceeds timeout limit, **Then** the system fails gracefully with timeout information
4. **Given** an API rate limit error, **When** embedding is requested, **Then** the system retries with exponential backoff delays until success or timeout

---

### Edge Cases

- **Special characters and emoji**: Handled according to model tokenization rules without filtering (see FR-015)
- **Unsupported languages**: System defers to model behavior; may return vectors but with degraded semantic quality (see FR-016)
- **Invalid/expired API key**: System returns clear authentication error with actionable message (see FR-013)
- **Unreachable API endpoint**: System retries with exponential backoff, fails after timeout with network error (see FR-007)
- **Vector dimension mismatch**: System fails immediately with clear error message indicating expected dimensions (per model specification) versus actual dimensions received from API (see FR-011)
- **Rate limiting**: System retries with exponential backoff (increasing delays between attempts, jitter ±25%) when API returns rate limit errors, respecting timeout constraints (see FR-007)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support vectorization of single text inputs and return numerical vectors
- **FR-002**: System MUST support batch vectorization of multiple texts (max 1000 documents per batch) with partial success handling: continue processing valid documents when some fail, return partial success response with successful vectors and clear identification of failed items (error reasons and indices), and reject batches exceeding 1000 documents with clear error message
- **FR-003**: System MUST support four embedding models: BGE-M3 (1024-dim), Qwen3-Embedding-8B (1536-dim), Hunyuan-Embedding (1024-dim), and Jina-Embeddings-v4 (768-dim)
- **FR-004**: System MUST validate model names and reject unsupported models with clear error messages
- **FR-005**: System MUST connect to embedding API using OpenAI-compatible protocol
- **FR-006**: System MUST accept configurable API credentials and base URL
- **FR-007**: System MUST implement automatic retry mechanism with exponential backoff strategy (initial delay 1s, max delay 32s, jitter ±25%, max 3 attempts) for failed requests, especially rate-limited requests, within the configured timeout period
- **FR-008**: System MUST implement request timeout handling
- **FR-009**: System MUST provide model information query capability (name, dimensions, description)
- **FR-010**: System MUST provide capability to list all available models
- **FR-011**: System MUST validate returned vector dimensions match the expected dimensions for the selected model (BGE-M3: 1024, Qwen3: 1536, Hunyuan: 1024, Jina: 768) and fail immediately with clear error message showing expected vs actual dimensions if mismatch detected
- **FR-012**: System MUST handle empty text inputs with appropriate error responses (HTTP 400 with error_code: INVALID_TEXT_ERROR per OpenAPI specification)
- **FR-013**: System MUST handle authentication failures with clear error messages
- **FR-014**: System MUST log operational metrics including request counts, response latencies, model used, error rates, and batch sizes for monitoring and troubleshooting
- **FR-015**: System MUST handle Unicode characters (including emoji, special characters, and non-ASCII text) according to the embedding model's tokenization rules without preprocessing or filtering
- **FR-016**: System MUST process text in any language supported by the selected model; for unsupported languages, the system defers to model behavior (may return vectors with degraded semantic quality but will not fail)

### Non-Functional Requirements

- **NFR-001**: System MUST provide health check endpoint (`/health`) for orchestration and monitoring tools to verify service readiness and API connectivity
- **NFR-002**: All API responses MUST follow standardized JSON format defined in OpenAPI specification
- **NFR-003**: System MUST handle concurrent requests without data corruption or race conditions

### Key Entities *(include if feature involves data)*

- **Embedding Model**: Represents a specific embedding model configuration with attributes: name, dimension size, description
- **Vector**: Numerical representation of text, represented as a list of floating-point numbers matching model dimension
- **Embedding Request**: Represents a vectorization request with attributes: text content(s), target model, API configuration
- **Embedding Response**: Contains generated vector(s) and metadata about the operation

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can vectorize a single text query and receive results within 2 seconds under normal conditions (defined as: API response time <500ms, no rate limiting, network latency <100ms)
- **SC-002**: System successfully processes batch requests of 100 documents within 30 seconds
- **SC-003**: System correctly generates vectors matching expected dimensions for all four supported models
- **SC-004**: System successfully recovers from at least 80% of temporary network failures through automatic retries
- **SC-005**: System provides clear, actionable error messages for all failure scenarios (invalid model, auth failure, timeout)
- **SC-006**: Model switching can be performed by configuration change without code modification
- **SC-007**: 95% of valid vectorization requests complete successfully on first attempt (measured over 24-hour rolling window with minimum 100 requests)
- **SC-008**: System logs capture sufficient operational metrics (request counts, latencies, error rates, batch sizes, model usage) to enable performance monitoring and troubleshooting without logging sensitive text content

## Assumptions

- API endpoint follows OpenAI-compatible embedding protocol
- Default API endpoint is `http://dev.fit-ai.woa.com/api/llmproxy`
- Default maximum retry count is 3 attempts
- Default request timeout is 60 seconds
- API authentication uses key-based mechanism
- All supported models are available on the configured API endpoint
- Text encoding is UTF-8
- Maximum text length limitations are enforced by the API provider (not client-side)

## Dependencies

- External API service providing OpenAI-compatible embedding endpoint
- Network connectivity to API endpoint
- Valid API credentials with appropriate permissions
- LangChain OpenAI embeddings library compatibility

## Out of Scope

- Local embedding model hosting
- Custom embedding model training
- Embedding model fine-tuning
- Vector storage and indexing (covered by separate module)
- Embedding cache implementation (may be added in future)
- Cost tracking and optimization
- Multi-region API failover
- Custom text preprocessing or tokenization
