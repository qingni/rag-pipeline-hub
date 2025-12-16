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

### Session 2025-12-15

- Q: Should embedding use chunking result JSON files as data source instead of manual text input? → A: Yes, embedding should read from chunking result JSON files
- Q: Should the system support both single-chunk and batch-chunk vectorization? → A: Yes, support both from chunking results
- Q: How should the embedding service identify which chunking result to use? → A: By chunking result ID or by document ID (using latest active chunking result)
- Q: Frontend UI layout adjustment for document-based vectorization? → A: Completely remove single-text and batch-text tabs, keep only document selector + model selector
- Q: What information should document selector dropdown display? → A: Document name + latest chunking result status (e.g., "已分块 · 2025-12-15")
- Q: How should vectorization be triggered after document/model selection? → A: User must click "开始向量化" button to trigger
- Q: When document has multiple chunking results, how should frontend handle? → A: Automatically use latest active chunking result, no user selection needed
- Q: Should embedding results display component be adjusted for chunk-based data? → A: Add document source information at top (document name, chunk count, vector dimensions)

### Session 2025-12-15 (Module Unification)

- Q: Unified module routing strategy (merge document/text vectorization)? → A: Use `/documents/embed` as sole entry point, remove `/embeddings` route, navigation shows only "文档向量化"
- Q: Document list filtering for unchunked documents? → A: Completely hide unchunked documents from selector list, show only documents with status='chunked' or active chunking results
- Q: Chunking result selection method when document has multiple results? → A: User selects document only (one-level selection), system automatically uses latest active chunking result
- Q: Vector model selector UI presentation format? → A: Dropdown showing model name + dimension + brief description (e.g., "BGE-M3 · 1024维 · 多语言支持"), with detailed info panel below when selected
- Q: Overall page layout after merging functionalities? → A: Two-column layout: Left (document selection + model configuration + start button), Right (results display panel)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vectorize Chunking Result (Priority: P1)

As a RAG system user, I need to convert all chunks from a document chunking result into vector representations so that I can perform semantic search against the document collection.

**Why this priority**: This is the core functionality that enables the complete document processing pipeline (load → chunk → embed → search). This represents the minimum viable product for production use.

**Independent Test**: Can be fully tested by providing a chunking result ID and verifying vectors are returned for all chunks with expected dimensions. Delivers immediate value for document search capabilities.

**Acceptance Scenarios**:

1. **Given** a completed chunking result with 50 chunks, **When** vectorization is requested, **Then** the system returns 50 vectors with consistent dimensions matching the selected model
2. **Given** a non-existent chunking result ID, **When** vectorization is requested, **Then** the system returns a 404 error with clear message
3. **Given** a chunking result with empty chunks, **When** vectorization is requested, **Then** the system returns appropriate error for invalid chunks

---

### User Story 2 - Vectorize Document Latest Chunks (Priority: P1)

As a document processing pipeline, I need to automatically vectorize the latest chunking result for a document so that I can process documents without tracking chunking result IDs.

**Why this priority**: Simplifies the workflow by automatically selecting the most recent active chunking result. Essential for user-friendly document processing.

**Independent Test**: Can be tested by providing a document ID and verifying the system uses the latest active chunking result. Demonstrates intelligent result selection.

**Acceptance Scenarios**:

1. **Given** a document with a completed chunking result, **When** vectorization by document ID is requested, **Then** the system uses the latest active chunking result and returns vectors
2. **Given** a document with multiple chunking results, **When** vectorization with strategy filter is requested, **Then** the system uses the latest result matching that strategy
3. **Given** a document without any chunking results, **When** vectorization is requested, **Then** the system returns a 404 error indicating no chunking result found

---

### User Story 3 - Frontend Unified Embedding Interface (Priority: P1)

As a RAG system user, I need a unified embedding interface at `/documents/embed` so that I can easily select chunked documents and trigger vectorization with a streamlined workflow.

**Why this priority**: Essential for user-friendly document-based vectorization workflow. Provides single entry point eliminating confusion between document and text vectorization modes.

**Independent Test**: Can be tested by verifying UI renders correctly at `/documents/embed`, document selector shows only chunked documents, model selector displays complete information, and vectorization triggers via button click.

**Acceptance Scenarios**:

1. **Given** the user navigates to `/documents/embed` page, **When** page loads, **Then** document selector displays ONLY documents with active chunking results in format "DocumentName · 已分块 · 2025-12-15"
2. **Given** a document without chunking results exists in database, **When** document selector loads, **Then** that document is NOT displayed in the selection list
3. **Given** user selects a document from the selector, **When** document has multiple chunking results, **Then** system automatically uses the latest active chunking result without requiring manual selection
4. **Given** user views model selector dropdown, **When** dropdown opens, **Then** each model option displays "ModelName · Dimension维 · BriefDescription" format (e.g., "BGE-M3 · 1024维 · 多语言支持")
5. **Given** user selects a model, **When** selection is made, **Then** detailed model information panel appears below showing dimension, provider, multilingual support, max batch size
6. **Given** user has selected both document and model, **When** "开始向量化" button is clicked, **Then** system calls `/from-document` API with document_id and selected model
7. **Given** vectorization completes, **When** results are displayed, **Then** right panel shows document source information (document name, chunk count, vector dimensions) at the top
8. **Given** no document is selected, **When** user attempts to click "开始向量化" button, **Then** button is disabled or shows validation message "请选择文档"
9. **Given** page layout renders, **When** viewed, **Then** displays two-column layout: left side (document selector + model configuration + start button), right side (results display panel)
10. **Given** navigation menu, **When** user views menu, **Then** shows single entry "文档向量化" pointing to `/documents/embed` (no separate text vectorization entry)

---

### User Story 4 - Single Text Vectorization (Priority: P3, Backend-only)

As a developer or API user, I need backend API support for single text vectorization so that I can perform ad-hoc queries and testing via API calls.

**Why this priority**: Useful for ad-hoc queries and testing but not exposed in frontend UI. Backend-only capability for API consumers.

**Independent Test**: Can be fully tested by providing a text string via API and verifying a vector is returned with the expected dimensions.

**Acceptance Scenarios**:

1. **Given** a text query "人工智能是什么", **When** `/embedding/single` API is called, **Then** the system returns a numerical vector of the model's expected dimension
2. **Given** an empty text string, **When** the API is called, **Then** the system returns an appropriate error message (HTTP 400)
3. **Given** a very long text (>10000 characters), **When** the API is called, **Then** the system either processes it successfully or returns a clear length limitation error

---

### User Story 5 - Batch Text Vectorization (Priority: P3, Backend-only)

As a developer or API user, I need backend API support for batch text vectorization so that I can efficiently process arbitrary text collections via API calls.

**Why this priority**: Useful for processing text that isn't from chunking results, but backend-only capability. Not exposed in frontend UI.

**Independent Test**: Can be tested by providing a list of text documents via API and verifying all are vectorized with consistent dimensions.

**Acceptance Scenarios**:

1. **Given** a list of 100 text strings, **When** `/embedding/batch` API is called, **Then** the system returns 100 vectors with consistent dimensions
2. **Given** a batch containing one invalid text, **When** batch vectorization is requested, **Then** the system processes all valid texts and returns partial success with failed items clearly identified
3. **Given** a batch with more than 1000 texts, **When** batch vectorization is requested, **Then** the system rejects the request with a clear error message

---

### User Story 6 - Multi-Model Support (Priority: P1)

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

### User Story 7 - Model Information Query (Priority: P3)

As a developer, I need to query the current model's information (name, dimensions, description) and list all available models so that I can make informed decisions about model selection.

**Why this priority**: Helpful for debugging and decision-making but not essential for core functionality. Can be added after basic vectorization works.

**Independent Test**: Can be tested by calling model information methods and verifying returned data matches expected structure. Provides value for operational visibility.

**Acceptance Scenarios**:

1. **Given** a service instance with model "qwen3-embedding-8b", **When** model info is requested, **Then** the system returns name, dimension (1536), and description
2. **Given** any service state, **When** listing available models is requested, **Then** the system returns all four supported models with their specifications

---

### User Story 8 - Error Recovery and Retries (Priority: P2)

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
- **Empty document list (all documents unchunked)**: Document selector displays empty state message "暂无已分块文档,请先对文档进行分块处理" with disabled "开始向量化" button. User must navigate to chunking module to process documents first.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support vectorization of all chunks from a chunking result by result ID (backend API)
- **FR-002**: System MUST support vectorization of all chunks from a document's latest active chunking result by document ID (backend API)
- **FR-003**: System MUST support optional filtering by chunking strategy type when vectorizing by document ID (backend API)
- **FR-004**: System MUST support single text vectorization for ad-hoc queries (backend API only, not exposed in frontend)
- **FR-005**: System MUST support batch vectorization of arbitrary text strings (max 1000 texts per batch) with partial success handling (backend API only, not exposed in frontend)
- **FR-006**: System MUST support four embedding models: BGE-M3 (1024-dim), Qwen3-Embedding-8B (1536-dim), Hunyuan-Embedding (1024-dim), and Jina-Embeddings-v4 (768-dim)
- **FR-007**: System MUST validate model names and reject unsupported models with clear error messages
- **FR-008**: System MUST connect to embedding API using OpenAI-compatible protocol
- **FR-009**: System MUST accept configurable API credentials and base URL
- **FR-010**: System MUST implement automatic retry mechanism with exponential backoff strategy (initial delay 1s, max delay 32s, jitter ±25%, max 3 attempts) for failed requests, especially rate-limited requests, within the configured timeout period
- **FR-011**: System MUST implement request timeout handling
- **FR-012**: System MUST provide model information query capability (name, dimensions, description)
- **FR-013**: System MUST provide capability to list all available models
- **FR-014**: System MUST validate returned vector dimensions match the expected dimensions for the selected model and fail immediately with clear error message if mismatch detected
- **FR-015**: System MUST handle empty text inputs with appropriate error responses (HTTP 400)
- **FR-016**: System MUST handle authentication failures with clear error messages
- **FR-017**: System MUST log operational metrics including request counts, response latencies, model used, error rates, and batch sizes
- **FR-018**: System MUST handle Unicode characters according to the embedding model's tokenization rules
- **FR-019**: System MUST persist embedding results as JSON files with source information (chunking result ID or document ID when applicable)
- **FR-020**: System MUST return vectors in the same order as the input chunks for chunking-based vectorization
- **FR-021**: Frontend MUST use `/documents/embed` as the sole entry point for vector embedding module (no separate `/embeddings` route)
- **FR-022**: Frontend navigation menu MUST display single entry "文档向量化" for embedding module (no separate text vectorization entry)
- **FR-023**: Frontend document selector MUST display ONLY documents with active chunking results (completely hide unchunked documents from list)
- **FR-024**: Frontend document selector MUST show each document in format "DocumentName · 已分块 · YYYY-MM-DD"
- **FR-025**: Frontend MUST implement one-level document selection (user selects document, system automatically uses latest active chunking result)
- **FR-026**: Frontend model selector dropdown MUST display each model as "ModelName · Dimension维 · BriefDescription" (e.g., "BGE-M3 · 1024维 · 多语言支持")
- **FR-027**: Frontend MUST show detailed model information panel below selector when model is selected (dimension, provider, multilingual support, max batch size)
- **FR-028**: Frontend MUST require user to click "开始向量化" button to trigger vectorization after selecting document and model
- **FR-029**: Frontend MUST implement two-column page layout: left column (document selector + model configuration + start button), right column (results display panel)
- **FR-030**: Frontend MUST display document source information (document name, chunk count, vector dimensions) at the top of results panel after successful vectorization
- **FR-031**: Frontend MUST disable or show validation message for "开始向量化" button when no document is selected

### Non-Functional Requirements

- **NFR-001**: System MUST provide health check endpoint (`/health`) for orchestration and monitoring tools to verify service readiness and API connectivity. The health check MUST validate:
  1. **Service Status**: HTTP 200 response indicates service is running
  2. **API Endpoint Reachability**: Attempt to connect to configured embedding API base URL (timeout: 5s)
  3. **Model Availability**: Verify at least one embedding model is accessible via `/v1/models` or equivalent
  4. **Authentication Validity**: Confirm API credentials are valid (via lightweight API call, not full embedding)
  
  **Response Format**:
  ```json
  {
    "status": "healthy" | "degraded" | "unhealthy",
    "service": "up",
    "api_connectivity": true | false,
    "models_available": ["qwen3-embedding-8b", "bge-m3", ...],
    "authentication": "valid" | "invalid" | "not_checked",
    "timestamp": "2025-12-15T10:30:45Z"
  }
  ```
  
  **Status Definitions**:
  - `healthy`: All checks pass (api_connectivity=true, authentication=valid, models_available not empty)
  - `degraded`: Service up but API issues (e.g., connectivity failed, authentication invalid)
  - `unhealthy`: Service cannot start or critical dependency missing
- **NFR-002**: All API responses MUST follow standardized JSON format defined in OpenAPI specification
- **NFR-003**: System MUST handle concurrent requests without data corruption or race conditions

### Key Entities *(include if feature involves data)*

- **Embedding Model**: Represents a specific embedding model configuration with attributes: name, dimension size, description
- **Vector**: Numerical representation of text, represented as a list of floating-point numbers matching model dimension
- **Embedding Request**: Represents a vectorization request with attributes: source (chunking result ID / document ID / text content), target model, API configuration
- **Embedding Response**: Contains generated vector(s), metadata about the operation, and source information (chunking result ID or document ID when applicable)
- **Chunking Result**: Reference to a completed document chunking result containing multiple chunks to be vectorized
- **Document Selection State** (Frontend): UI state tracking selected document ID, model, and latest chunking result status for display

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can vectorize all chunks from a chunking result and receive results within 30 seconds for 100 chunks under normal conditions
- **SC-002**: System correctly identifies and uses the latest active chunking result when vectorizing by document ID
- **SC-003**: System correctly filters by strategy type when multiple chunking results exist for a document
- **SC-004**: System correctly generates vectors matching expected dimensions for all four supported models
- **SC-005**: System successfully recovers from at least 80% of temporary network failures through automatic retries
- **SC-006**: System provides clear, actionable error messages for all failure scenarios (invalid IDs, missing results, auth failure, timeout)
- **SC-007**: Model switching can be performed by configuration change without code modification
- **SC-008**: 95% of valid vectorization requests complete successfully on first attempt (measured over 24-hour rolling window with minimum 100 requests)
- **SC-009**: System logs capture sufficient operational metrics to enable performance monitoring and troubleshooting
- **SC-010**: Embedding results are persisted with complete source traceability (chunking result ID or document ID)
- **SC-011**: Frontend unified embedding page at `/documents/embed` loads within 2 seconds and displays only chunked documents in selector
- **SC-012**: Frontend document selector successfully filters out all unchunked documents (0% unchunked documents visible in list)
- **SC-013**: Frontend correctly displays document source information in results panel after successful vectorization
- **SC-014**: Frontend model selector displays complete information (name, dimension, description) for all four supported models
- **SC-015**: Navigation menu shows single "文档向量化" entry pointing to `/documents/embed` (no duplicate text vectorization entry)

## Assumptions

- API endpoint follows OpenAI-compatible embedding protocol
- Default API endpoint is `http://dev.fit-ai.woa.com/api/llmproxy`
- Default maximum retry count is 3 attempts
- Default request timeout is 60 seconds
- API authentication uses key-based mechanism
- All supported models are available on the configured API endpoint
- Text encoding is UTF-8
- Maximum text length limitations are enforced by the API provider (not client-side)
- Performance metrics assume batch parallel processing (not sequential single-chunk calls)
- "30 seconds for 100 chunks" target assumes API latency <300ms per chunk on average

## Dependencies

- External API service providing OpenAI-compatible embedding endpoint
- Network connectivity to API endpoint
- Valid API credentials with appropriate permissions
- LangChain OpenAI embeddings library compatibility
- Frontend: Document list API for populating document selector
- Frontend: Chunking results API for retrieving latest chunking status per document
- Backend: ChunkingStrategy enum from chunking module (valid values: fixed_size, semantic, recursive, markdown, sentence, paragraph)

## Out of Scope

- Local embedding model hosting
- Custom embedding model training
- Embedding model fine-tuning
- Vector storage and indexing (covered by separate module)
- Embedding cache implementation (may be added in future)
- Cost tracking and optimization
- Multi-region API failover
- Custom text preprocessing or tokenization
- Frontend manual text input for single-text or batch-text vectorization (unified into document-based interface)
- Frontend manual chunking result selection (system automatically uses latest active result)
- Multiple embedding module entry points (unified to `/documents/embed` only)
