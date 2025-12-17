# Tasks: Vector Embedding Module

**Input**: Design documents from `/specs/003-vector-embedding/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, etc.)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Verify Python 3.11+ and Node.js 18+ are installed on development machine
- [x] T002 Switch to feature branch `003-vector-embedding` in repository
- [x] T003 [P] Install backend dependencies from backend/requirements.txt into virtual environment
- [x] T004 [P] Install frontend dependencies from frontend/package.json using npm/yarn
- [x] T005 [P] Create backend/.env file with EMBEDDING_API_KEY, EMBEDDING_API_BASE_URL, and other required environment variables per quickstart.md
- [x] T006 [P] Create backend/results/embedding/ directory for JSON vector file storage

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Create database migration file backend/migrations/create_embedding_results_table.py with schema from data-model.md
- [x] T008 Run database migration to create embedding_results table with indexes (document_id+model, created_at DESC, status)
- [x] T009 Verify embedding_results table schema in app.db using SQLite CLI
- [x] T010 [P] Create backend/src/models/embedding_result.py ORM model with all fields from data-model.md (result_id, document_id, chunking_result_id, model, status, counts, dimension, json_file_path, processing_time_ms, created_at, error_message)
- [x] T011 [P] Create backend/src/storage/embedding_storage_dual.py implementing dual-write strategy (JSON first, then DB with rollback on failure)
- [x] T012 [P] Update backend/src/services/embedding_service.py to add methods: embed_from_chunking_result(), embed_from_document(), with OpenAI-compatible API integration
- [x] T013 [P] Update backend/src/storage/embedding_db.py with database operations: create_embedding_result(), get_result_by_id(), get_latest_by_document(), list_results() with pagination
- [x] T014 Update backend/src/main.py to register embedding routes (embedding_routes, embedding_query_routes) and verify server starts without errors

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 6 - Multi-Model Support (Priority: P1) 🎯 FOUNDATION

**Goal**: Configure and validate all four embedding models (BGE-M3, Qwen3-Embedding-8B, Hunyuan-Embedding, Jina-Embeddings-v4) with OpenAI-compatible protocol

**Independent Test**: Initialize service with each model and verify vectors generated with correct dimensions (1024 for bge-m3/hunyuan, 4096 for qwen3, 768 for jina)

### Implementation for User Story 6

- [x] T015 [P] [US6] Define EMBEDDING_MODELS constant in backend/src/models/embedding_models.py with all 4 models (name, dimension, description, provider, supports_multilingual, max_batch_size)
- [x] T016 [P] [US6] Implement get_model_info() method in backend/src/services/embedding_service.py returning ModelInfo for current model
- [x] T017 [P] [US6] Implement list_available_models() method in backend/src/services/embedding_service.py returning all EMBEDDING_MODELS
- [x] T018 [US6] Add model validation in backend/src/services/embedding_service.py __init__ method to reject unsupported model names
- [x] T019 [US6] Implement /api/embeddings/models GET endpoint in backend/src/api/embedding_routes.py returning all models with specifications

**Checkpoint**: All 4 models configured and queryable via API

---

## Phase 4: User Story 1 - Vectorize Chunking Result (Priority: P1) 🎯 MVP

**Goal**: Convert all chunks from a chunking result into vector representations

**Independent Test**: Provide chunking result ID, verify vectors returned for all chunks with expected dimensions

### Implementation for User Story 1

- [x] T020 [P] [US1] Create FromChunkingResultRequest schema in backend/src/models/embedding_models.py with result_id, model, request_id fields
- [x] T021 [P] [US1] Create EmbeddingResponse schema in backend/src/models/embedding_models.py with all fields from embedding-api.yaml
- [x] T022 [US1] Implement embed_from_chunking_result() in backend/src/services/embedding_service.py: validate result exists and status=COMPLETED, load chunks from chunking result JSON, call embedding API, return vectors
- [x] T023 [US1] Implement _batch_vectorize() helper method in backend/src/services/embedding_service.py to handle batching (max 1000 texts), partial success tracking, and retry logic with exponential backoff
- [x] T024 [US1] Implement dual_write_embedding_result() in backend/src/storage/embedding_storage_dual.py: write JSON file first with naming convention {document_id}_{timestamp}.json, then write DB record, rollback JSON on DB failure
- [x] T025 [US1] Implement POST /api/embeddings/from-chunking-result endpoint in backend/src/api/embedding_routes.py with request validation, service call, and error handling per embedding-api.yaml
- [x] T026 [US1] Add dimension validation in backend/src/services/embedding_service.py to fail immediately if returned vector dimension doesn't match model specification

**Checkpoint**: Can vectorize chunking results via API, results persisted to JSON + database

---

## Phase 5: User Story 2 - Vectorize Document Latest Chunks (Priority: P1) 🎯 MVP

**Goal**: Automatically vectorize latest chunking result for a document without tracking result IDs

**Independent Test**: Provide document ID, verify system uses latest active chunking result and returns vectors

### Implementation for User Story 2

- [x] T027 [P] [US2] Create FromDocumentRequest schema in backend/src/models/embedding_models.py with document_id, model, strategy_type, request_id fields
- [x] T028 [US2] Implement get_latest_chunking_result() helper in backend/src/services/embedding_service.py to query chunking_results table with filters (document_id, strategy_type if provided, status=COMPLETED) ordered by created_at DESC LIMIT 1
- [x] T029 [US2] Implement embed_from_document() in backend/src/services/embedding_service.py: get latest chunking result, delegate to embed_from_chunking_result(), return response
- [x] T030 [US2] Implement POST /api/embeddings/from-document endpoint in backend/src/api/embedding_routes.py with request validation, service call, 404 error if no chunking result found
- [x] T031 [US2] Add error handling for "no chunking result found" with clear message indicating document must be chunked first

**Checkpoint**: Can vectorize documents by ID, system automatically selects latest chunking result

---

## Phase 6: User Story 8 - Error Recovery and Retries (Priority: P2)

**Goal**: Automatic retry with exponential backoff for transient failures (network issues, rate limits)

**Independent Test**: Simulate network failures, verify retry behavior and eventual success/timeout

### Implementation for User Story 8

- [x] T032 [P] [US8] Implement _exponential_backoff_retry() decorator in backend/src/services/embedding_service.py with parameters: max_retries=3, initial_delay=1s, max_delay=32s, jitter=±25%
- [x] T033 [P] [US8] Add retry logic to embedding API calls in backend/src/services/embedding_service.py specifically for RATE_LIMIT_ERROR and NETWORK_ERROR
- [x] T034 [US8] Implement timeout handling in backend/src/services/embedding_service.py using asyncio.wait_for() with configurable EMBEDDING_TIMEOUT (default 60s)
- [x] T035 [US8] Add error classification in backend/src/services/embedding_service.py to distinguish retryable (rate limit, network) from non-retryable errors (invalid text, auth failure)
- [x] T036 [US8] Implement logging for retry attempts in backend/src/services/embedding_service.py (log attempt count, delay, error type)
- [x] T037 [US8] Update partial success handling to populate failures array in EmbeddingResponse with chunk_index, error_type, error_message, retry_recommended

**Checkpoint**: System automatically recovers from transient failures, clear error reporting for permanent failures

---

## Phase 7: User Story 9 - Query Embedding Results (Priority: P2)

**Goal**: Query embedding results from database for displaying status, history, and management features

**Independent Test**: Create embedding records, verify query APIs return correct filtered/paginated results

### Implementation for User Story 9

- [x] T038 [P] [US9] Create EmbeddingResult response schema in backend/src/models/embedding_models.py matching data-model.md entity
- [x] T039 [P] [US9] Create EmbeddingResultList response schema in backend/src/models/embedding_models.py with results, total_count, page, page_size, total_pages
- [x] T040 [P] [US9] Implement get_result_by_id() in backend/src/storage/embedding_db.py: query embedding_results table by result_id primary key
- [x] T041 [P] [US9] Implement get_latest_by_document() in backend/src/storage/embedding_db.py: query with document_id filter, optional model filter, order by created_at DESC LIMIT 1
- [x] T042 [P] [US9] Implement list_results() in backend/src/storage/embedding_db.py with filters (document_id, model, status, date_from, date_to), pagination (page, page_size), and sort (created_at:asc/desc)
- [x] T043 [US9] Create backend/src/api/embedding_query_routes.py with FastAPI router
- [x] T044 [US9] Implement GET /api/embeddings/results/{result_id} endpoint in backend/src/api/embedding_query_routes.py with 404 handling
- [x] T045 [US9] Implement GET /api/embeddings/results endpoint in backend/src/api/embedding_query_routes.py with query parameter validation (page>=1, page_size<=100, valid date range)
- [x] T046 [US9] Implement GET /api/embeddings/results/by-document/{document_id} endpoint in backend/src/api/embedding_query_routes.py with optional model query parameter
- [x] T047 [US9] Register embedding_query_routes in backend/src/main.py

**Checkpoint**: All query APIs functional, frontend can retrieve embedding history

---

## Phase 8: User Story 7 - Model Information Query (Priority: P3)

**Goal**: Query current model information and list all available models

**Independent Test**: Call model info methods, verify returned data matches expected structure

### Implementation for User Story 7

- [x] T048 [P] [US7] Verify GET /api/embeddings/models endpoint (already created in US6 T019) returns complete ModelInfo for all 4 models
- [x] T049 [US7] Add API documentation comments to /api/embeddings/models endpoint describing response format and use cases

**Checkpoint**: Model information queryable via API for decision-making

---

## Phase 9: User Story 4 - Single Text Vectorization (Priority: P3, Backend-only)

**Goal**: Backend API support for single text vectorization (ad-hoc queries, testing)

**Independent Test**: Provide text string via API, verify vector returned with expected dimensions

### Implementation for User Story 4

- [x] T050 [P] [US4] Create SingleTextRequest schema in backend/src/models/embedding_models.py with text and model fields
- [x] T051 [US4] Implement embed_single_text() in backend/src/services/embedding_service.py: validate text not empty, call embedding API, return single vector
- [x] T052 [US4] Implement POST /api/embeddings/single endpoint in backend/src/api/embedding_routes.py (backend-only, not exposed in frontend navigation)
- [x] T053 [US4] Add validation for empty text with HTTP 400 error response

**Checkpoint**: Single text vectorization available via API for developers

---

## Phase 10: User Story 5 - Batch Text Vectorization (Priority: P3, Backend-only)

**Goal**: Backend API support for batch text vectorization (arbitrary text collections)

**Independent Test**: Provide list of text documents via API, verify all vectorized with consistent dimensions

### Implementation for User Story 5

- [x] T054 [P] [US5] Create BatchTextRequest schema in backend/src/models/embedding_models.py with texts array (max 1000) and model fields
- [x] T055 [US5] Implement embed_batch_texts() in backend/src/services/embedding_service.py: validate batch size <=1000, call _batch_vectorize(), return vectors with partial success handling
- [x] T056 [US5] Implement POST /api/embeddings/batch endpoint in backend/src/api/embedding_routes.py (backend-only, not exposed in frontend navigation)
- [x] T057 [US5] Add validation for batch size >1000 with clear error message indicating limit

**Checkpoint**: Batch text vectorization available via API for developers

---

## Phase 11: User Story 3 - Frontend Unified Embedding Interface (Priority: P1) 🎯 MVP

**Goal**: Unified embedding interface at /documents/embed with document selector, model selector, and vectorization trigger

**Independent Test**: Verify UI renders correctly, document selector shows only chunked documents, model selector displays complete info, vectorization triggers via button

### Implementation for User Story 3

- [x] T058 [P] [US3] Create frontend/src/stores/embedding.js Pinia store with state (selectedDocument, selectedModel, currentResult, latestResults cache, isLoading, error)
- [x] T059 [P] [US3] Implement selectDocument() action in frontend/src/stores/embedding.js: cache check first, then API call to /api/embeddings/results/by-document/{id}, auto-switch selectedModel to match historical result
- [x] T060 [P] [US3] Implement triggerVectorization() action in frontend/src/stores/embedding.js: call POST /api/embeddings/from-document with selectedDocument and selectedModel, update currentResult on success
- [x] T061 [P] [US3] Create frontend/src/services/embedding.js API client with methods: getLatestByDocument(), vectorizeDocument(), getModels()
- [x] T062 [P] [US3] Create frontend/src/components/DocumentSelector.vue component: dropdown showing documents with chunking_status='chunked' in format "DocumentName · 已分块 · YYYY-MM-DD", filter out unchunked documents
- [x] T063 [P] [US3] Create frontend/src/components/EmbeddingModelSelector.vue component: dropdown with format "ModelName · Dimension维 · BriefDescription", detailed info panel below when selected
- [x] T064 [P] [US3] Create frontend/src/components/EmbeddingResults.vue component: header with metadata (document name, model+dimension, success/total chunks, processing time), vector list display
- [x] T065 [US3] Create frontend/src/pages/DocumentEmbedding.vue page with two-column layout: left (DocumentSelector + ModelSelector + button), right (EmbeddingResults)
- [x] T066 [US3] Implement button behavior in frontend/src/pages/DocumentEmbedding.vue: text="开始向量化" when no currentResult, text="重新向量化" when currentResult exists, disabled when no document selected
- [x] T067 [US3] Add route /documents/embed to frontend/src/router/index.js pointing to DocumentEmbedding.vue
- [x] T068 [US3] Update frontend navigation menu to show single entry "文档向量化" pointing to /documents/embed (remove any separate text vectorization entries)
- [x] T069 [US3] Implement empty state display in DocumentSelector when all documents are unchunked: message "暂无已分块文档,请先对文档进行分块处理"

**Checkpoint**: Full frontend interface functional, can select documents, view history, trigger vectorization

---

## Phase 12: User Story 10 - Display Historical Embedding Results (Priority: P1) 🎯 MVP

**Goal**: Immediately display latest embedding results when selecting document with existing vectors

**Independent Test**: Create embedding records, select document in UI, verify latest result displays within 500ms with correct metadata and auto-switched model selector

### Implementation for User Story 10

- [x] T070 [US10] Update selectDocument() action in frontend/src/stores/embedding.js to automatically query /api/embeddings/results/by-document/{id} on document selection
- [x] T071 [US10] Implement auto-display logic in frontend/src/pages/DocumentEmbedding.vue: watch selectedDocument change, trigger currentResult display when API returns data
- [x] T072 [US10] Implement model selector auto-switch in frontend/src/stores/embedding.js: when currentResult loads, set selectedModel = currentResult.model
- [x] T073 [US10] Update button text computation in frontend/src/pages/DocumentEmbedding.vue: show "重新向量化" when currentResult exists, "开始向量化" otherwise
- [x] T074 [US10] Implement metadata header display in frontend/src/components/EmbeddingResults.vue: format "DocumentName · model-name · dimension维 · success/total块 · processing_time_ms"
- [x] T075 [US10] Add handling for PARTIAL_SUCCESS status in frontend/src/components/EmbeddingResults.vue: show "部分成功" badge, display error_message
- [x] T076 [US10] Implement document switching behavior: when switching from doc A to doc B, clear previous result, fetch and display doc B's latest result
- [x] T077 [US10] Add loading spinner in frontend/src/pages/DocumentEmbedding.vue right panel while fetching historical results (target: display within 500ms)

**Checkpoint**: Historical results display immediately on document selection, seamless user experience

### Enhancement: Auto-load Vector Results on Document Selection

**Implemented**: 2025-12-17

- [x] T078-ENH [US10] Add `EmbeddingResultWithVectors` model to backend/src/models/embedding_models.py extending EmbeddingResultDetail with vectors, failures, and metadata fields
- [x] T079-ENH [US10] Modify GET /api/embedding/results/by-document/{document_id} endpoint to support `include_vectors` query parameter (default: true)
- [x] T080-ENH [US10] Implement JSON file loading in embedding_query_routes.py to load vector data from json_file_path
- [x] T081-ENH [US10] Add `getLatestByDocument`, `getResultById`, `listResults` methods to frontend/src/services/embeddingService.js
- [x] T082-ENH [US10] Add `fetchLatestEmbeddingResult` action to frontend/src/stores/embedding.js with auto-model-switch logic
- [x] T083-ENH [US10] Add watch on `selectedDocumentId` in frontend/src/views/DocumentEmbedding.vue to trigger auto-load
- [x] T084-ENH [US10] Add `loadingResult` state and loading overlay in DocumentEmbedding.vue right panel
- [x] T085-ENH [US10] Update button text logic to show "重新向量化" when currentResult exists, "开始向量化" otherwise

**Result**: When user selects a document that has been vectorized, the system immediately loads and displays the latest vector results (including full vector data, metadata, and statistics) within 500ms. The model selector automatically switches to match the historical result's model.

---

## Phase 13: NFR - Health Check Endpoint (Priority: P2)

**Goal**: Provide health check endpoint for orchestration and monitoring tools

**Independent Test**: Call /api/embeddings/health, verify response shows service status, API connectivity, model availability, authentication validity

- [x] T078 [P] Create HealthResponse schema in backend/src/models/embedding_models.py with status, service, api_connectivity, models_available, authentication, timestamp fields
- [x] T079 Implement check_api_connectivity() helper in backend/src/services/embedding_service.py: attempt to connect to EMBEDDING_API_BASE_URL with 5s timeout
- [x] T080 Implement check_models_availability() helper in backend/src/services/embedding_service.py: call /v1/models endpoint or equivalent to list available models
- [x] T081 Implement check_authentication() helper in backend/src/services/embedding_service.py: verify API key validity via lightweight API call
- [x] T082 Implement GET /api/embeddings/health endpoint in backend/src/api/embedding_routes.py: aggregate checks, return healthy/degraded/unhealthy status with 200/200/503 HTTP codes
- [x] T083 Add health check endpoint to backend/src/main.py startup validation (optional: log warning if degraded on startup)

**Checkpoint**: Health check endpoint operational for monitoring

---

## Phase 14: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T084 [P] Add comprehensive logging to backend/src/services/embedding_service.py: log request counts, latencies, model used, error rates, batch sizes per FR-017
- [x] T085 [P] Add input validation and sanitization in backend/src/api/embedding_routes.py for all endpoints (prevent injection attacks, path traversal)
- [x] T086 [P] Implement API key middleware in backend/src/api/embedding_routes.py and backend/src/api/embedding_query_routes.py using existing verify_api_key dependency
- [x] T087 [P] Add CORS configuration in backend/src/main.py to allow frontend origin (configure FRONTEND_ALLOWED_ORIGINS)
- [x] T088 [P] Add error boundary component in frontend/src/pages/DocumentEmbedding.vue to catch and display component errors gracefully
- [x] T089 [P] Implement loading states for all async operations in frontend (document list loading, model list loading, vectorization in progress)
- [x] T090 [P] Add success/error toast notifications in frontend/src/pages/DocumentEmbedding.vue using TDesign Message component for vectorization completion
- [x] T091 Code review and refactoring: extract reusable functions, remove code duplication, ensure consistent error handling patterns
- [x] T092 Performance optimization: verify dual-write completes <5s for 100 vectors (4096-dim), query APIs <100ms for 10K records
- [x] T093 Verify all acceptance scenarios from spec.md user stories are satisfied (test each scenario manually or with automated tests)
- [x] T094 Run quickstart.md validation workflow end-to-end: upload document → chunk → vectorize → query history → display in UI
- [x] T095 Update CODEBUDDY.md with final implementation notes, known limitations, and operational guidance
- [x] T096 [P] Add inline code documentation (docstrings) for all public methods in backend services and storage modules
- [x] T097 Security audit: verify API keys not logged, file paths sanitized, database queries parameterized, no SQL injection vulnerabilities

**Checkpoint**: Production-ready implementation with monitoring, security, and error handling

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-12)**: All depend on Foundational phase completion
  - US6 (Multi-Model) should complete first as it provides model configurations used by US1, US2
  - US1 (Vectorize Chunking Result) is core - should complete before US2
  - US2 (Vectorize Document) depends on US1 implementation
  - US9 (Query APIs) should complete before US10 (Display History)
  - US3 (Frontend Interface) can start after US1, US2 APIs ready
  - US10 (Display History) requires US3 (Frontend) + US9 (Query APIs)
  - US4, US5, US7, US8 are independent enhancements (can be done in parallel)
- **NFR - Health Check (Phase 13)**: Can be done in parallel with user stories
- **Polish (Phase 14)**: Depends on all desired user stories being complete

### Critical Path for MVP

**Minimum for MVP (User Stories 1, 2, 3, 6, 10)**:
1. Setup (Phase 1) → Foundational (Phase 2)
2. US6 (Multi-Model Support)
3. US1 (Vectorize Chunking Result)
4. US2 (Vectorize Document)
5. US9 (Query APIs) - needed for US10
6. US3 (Frontend Interface)
7. US10 (Display History)
8. Polish (selected tasks)

### Parallel Opportunities

**Within Setup (Phase 1)**:
- T003, T004, T005, T006 can all run in parallel

**Within Foundational (Phase 2)**:
- T010, T011, T012, T013 can run in parallel after T009

**Across User Stories (after Foundational complete)**:
- US6, US7, US8 can run in parallel
- US4, US5 can run in parallel (both backend-only)
- US3 frontend work can start once US1, US2 backend APIs are ready
- Within each user story: tasks marked [P] can run in parallel

**Within US3 (Frontend)**:
- T058, T059, T060, T061, T062, T063, T064 all run in parallel (different files)

**Within US9 (Query APIs)**:
- T038, T039, T040, T041, T042 all run in parallel (different methods)

---

## Parallel Example: User Story 1 (Vectorize Chunking Result)

```bash
# Launch all schema definitions together:
Task T020: "Create FromChunkingResultRequest schema"
Task T021: "Create EmbeddingResponse schema"

# After schemas ready, implement service layer:
Task T022: "Implement embed_from_chunking_result()"
Task T023: "Implement _batch_vectorize() helper"

# Then storage and API in parallel:
Task T024: "Implement dual_write_embedding_result()"
Task T025: "Implement POST /api/embeddings/from-chunking-result endpoint"
```

---

## Implementation Strategy

### MVP First (User Stories 1, 2, 3, 6, 9, 10 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: US6 (Multi-Model Support)
4. Complete Phase 4: US1 (Vectorize Chunking Result)
5. Complete Phase 5: US2 (Vectorize Document)
6. Complete Phase 7: US9 (Query APIs)
7. Complete Phase 11: US3 (Frontend Interface)
8. Complete Phase 12: US10 (Display History)
9. **STOP and VALIDATE**: Test end-to-end workflow
10. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add US6 + US1 → Test vectorization independently → Deploy/Demo (Core API!)
3. Add US2 → Test document-based vectorization → Deploy/Demo
4. Add US9 + US3 + US10 → Test full UI workflow → Deploy/Demo (MVP!)
5. Add US8 (Error Recovery) → Improve reliability → Deploy/Demo
6. Add US4, US5, US7 → Developer features → Deploy/Demo
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US6 + US1 (backend core)
   - Developer B: US2 + US9 (backend extensions + queries)
   - Developer C: US3 + US10 (frontend)
   - Developer D: US8 + Health Check (reliability)
3. Stories complete and integrate independently

---

## Notes

- All tasks follow strict checklist format: `- [ ] [ID] [P?] [Story?] Description with file path`
- [P] tasks target different files with no dependencies - can run in parallel
- [Story] label maps task to specific user story (US1-US10) for traceability
- Each user story should be independently completable and testable
- Backend-only stories (US4, US5) are not exposed in frontend navigation
- Tests are NOT included (not explicitly requested in spec.md)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Performance targets: <30s for 100 chunks, <100ms queries, <500ms frontend display
- Database constraints enforced via SQLAlchemy ORM validation and CHECK constraints
- Dual-write rollback ensures no orphaned JSON files (NFR-005)
