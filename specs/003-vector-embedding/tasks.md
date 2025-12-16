# Tasks: Vector Embedding Module

**Feature Branch**: `003-vector-embedding`  
**Input**: Design documents from `/specs/003-vector-embedding/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Not included (not explicitly requested in specification)

**Organization**: Tasks grouped by user story for independent implementation

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no dependencies)
- **[Story]**: User story label (US1, US2, US3, US4, US5, US6, US7, US8)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify existing infrastructure and prepare for chunking integration

- [ ] T001 Verify EmbeddingService in backend/src/services/embedding_service.py has embed_query and embed_documents methods
- [ ] T002 Verify 4 models in EMBEDDING_MODELS registry (bge-m3, qwen3-embedding-8b, hunyuan-embedding, jina-embeddings-v4)
- [ ] T003 Verify EmbeddingStorage in backend/src/storage/embedding_storage.py exists
- [ ] T004 Verify embedding routes in backend/src/api/embedding_routes.py have /single and /batch endpoints
- [ ] T005 Create results/embedding directory if not exists
- [ ] T006 [P] Verify retry_utils.py has ExponentialBackoffRetry
- [ ] T007 [P] Verify logging_utils.py has embedding_logger
- [ ] T007b Audit existing routes in frontend/src/router/index.js to identify any /embeddings, /embedding, or /vector routes that conflict with new /documents/embed unified route (document for removal in Phase 6)

**Checkpoint**: Existing infrastructure verified, conflicting routes identified

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add database integration for chunking results - BLOCKS all user stories

- [ ] T008 Add ChunkingResult, ChunkingTask, Chunk model imports in backend/src/services/embedding_service.py
- [ ] T009 Add get_db() dependency in backend/src/api/embedding_routes.py
- [ ] T010 Add /documents endpoint filter ?has_chunking_result=true in backend/src/api/documents.py
- [ ] T011 Update BatchEmbeddingRequest model in backend/src/models/embedding_models.py to add optional result_id field
- [ ] T012 Add ChunkingResultEmbeddingRequest model in backend/src/models/embedding_models.py
- [ ] T013 Add DocumentEmbeddingRequest model in backend/src/models/embedding_models.py
- [ ] T014 Update EmbeddingStorage.save_batch_result() to accept source_document_id and source_result_id parameters

**Checkpoint**: Foundation ready - user story implementation can begin

---

## Phase 3: User Story 1 - Vectorize Chunking Result (P1) 🎯 MVP

**Goal**: Convert chunks from chunking result into vectors for semantic search

**Test**: Provide chunking result ID → verify vectors returned for all chunks

### Implementation

- [ ] T015 [US1] Add embed_chunking_result() method to EmbeddingService in backend/src/services/embedding_service.py
- [ ] T016 [US1] Query ChunkingResult by result_id with status=COMPLETED filter
- [ ] T017 [US1] Load all Chunks ordered by sequence_number
- [ ] T018 [US1] Extract chunk.content texts and call embed_documents()
- [ ] T019 [US1] Return BatchEmbeddingResult preserving chunk order
- [ ] T020 [US1] Add POST /embedding/from-chunking-result endpoint in backend/src/api/embedding_routes.py
- [ ] T021 [US1] Add 404 error handling for result not found
- [ ] T022 [US1] Add 400 error handling for empty chunks
- [ ] T023 [US1] Update storage layer call to include source_result_id

**Acceptance**: 50 chunks → 50 vectors ✓ | Non-existent ID → 404 ✓ | Empty chunks → 400 ✓

**Checkpoint**: US1 complete - can vectorize any chunking result by ID

---

## Phase 4: User Story 2 - Vectorize Document Latest Chunks (P1)

**Goal**: Auto-vectorize latest chunking result for a document

**Test**: Provide document ID → verify system uses latest active result

### Implementation

- [ ] T024 [US2] Add embed_document_latest_chunks() method to EmbeddingService in backend/src/services/embedding_service.py
- [ ] T025 [US2] Build query for latest active ChunkingResult for document_id
- [ ] T026 [US2] Apply optional strategy_type filter if provided
- [ ] T027 [US2] Call embed_chunking_result() with selected result
- [ ] T028 [US2] Add POST /embedding/from-document endpoint in backend/src/api/embedding_routes.py
- [ ] T029 [US2] Add 404 error handling for no result found
- [ ] T030 [US2] Add 400 error handling for invalid strategy_type
- [ ] T031 [US2] Update storage layer call to include source_document_id

**Acceptance**: Latest result used ✓ | Strategy filter works ✓ | No results → 404 ✓

**Checkpoint**: US1 + US2 complete - can vectorize by result ID or document ID

---

## Phase 5: User Story 6 - Multi-Model Support (P1)

**Goal**: Support 4 embedding models for different use cases

**Test**: Initialize service with each model → verify correct dimensions

### Implementation

- [ ] T032 [P] [US6] Verify EMBEDDING_MODELS registry dimensions (bge-m3=1024, qwen3=1536, hunyuan=1024, jina=768)
- [ ] T033 [US6] Verify model validation in __init__() rejects unsupported models with clear error
- [ ] T034 [US6] Verify _validate_vector_dimensions() fails immediately on mismatch
- [ ] T035 [US6] Update GET /embedding/models endpoint to return all 4 models
- [ ] T036 [US6] Update GET /embedding/models/{model_name} to return 404 for unsupported models

**Acceptance**: All 4 models work with correct dimensions ✓ | Unsupported model → clear error ✓

**Checkpoint**: Multi-model support validated

---

## Phase 6: User Story 3 - Frontend Unified Embedding Interface (P1)

**Goal**: Unified interface at /documents/embed for document selection and vectorization

**Test**: Navigate to /documents/embed → verify UI renders, document filtering works, vectorization triggers

### Pinia Store

- [ ] T037 [US3] Create stores/embedding.js with state: selectedDocumentId, selectedModel, isProcessing, embeddingResults, documentsWithChunking, availableModels
- [ ] T038 [US3] Add getters: currentResult, selectedDocument, canStartEmbedding
- [ ] T039 [US3] Add action fetchDocumentsWithChunking() calling embeddingService.getDocumentsWithChunking()
- [ ] T040 [US3] Add action fetchModels() calling embeddingService.getModels()
- [ ] T041 [US3] Add action startEmbedding() calling embeddingService.embedDocument()

### API Service

- [ ] T042 [P] [US3] Create services/embeddingService.js if not exists
- [ ] T043 [P] [US3] Add getDocumentsWithChunking() method calling GET /documents?has_chunking_result=true
- [ ] T044 [P] [US3] Add getModels() method calling GET /embedding/models
- [ ] T045 [P] [US3] Add embedDocument(payload) method calling POST /embedding/from-document
- [ ] T046 [P] [US3] Add embedChunkingResult(payload) method calling POST /embedding/from-chunking-result

### Components

- [ ] T047 [P] [US3] Create components/embedding/DocumentSelector.vue with t-select showing only chunked documents; if list is empty, display empty state: "暂无已分块文档,请先对文档进行分块处理"
- [ ] T048 [P] [US3] Format document display as "DocumentName · 已分块 · YYYY-MM-DD"
- [ ] T049 [P] [US3] Create components/embedding/ModelSelector.vue with t-select showing "ModelName · Dimension维 · Description"
- [ ] T050 [P] [US3] Add model detail panel below selector showing dimension, provider, multilingual, max_batch_size
- [ ] T051 [P] [US3] Create components/embedding/EmbeddingResults.vue with document source info at top
- [ ] T052 [P] [US3] Display vectors, metadata, failures in results panel

### Main View

- [ ] T053 [US3] Create views/DocumentEmbedding.vue with two-column layout
- [ ] T054 [US3] Left column: DocumentSelector + ModelSelector + "开始向量化" button
- [ ] T055 [US3] Right column: EmbeddingResults panel
- [ ] T056 [US3] Disable button or show validation message when no document selected
- [ ] T057 [US3] Connect button click to store.startEmbedding()
- [ ] T058 [US3] Display loading state during isProcessing
- [ ] T059 [US3] Display error message if store.error is set

### Router

- [ ] T060 [US3] Add /documents/embed route in router/index.js pointing to DocumentEmbedding.vue
- [ ] T061 [US3] Remove conflicting routes identified in T007b (e.g., /embeddings, /embedding) and unify to /documents/embed as sole embedding module entry point
- [ ] T062 [US3] Update navigation menu in components/layout/NavigationBar.vue to show single "文档向量化" entry

**Acceptance**: 10 scenarios validated (document filtering, model display, button behavior, layout, navigation)

**Checkpoint**: US3 complete - frontend unified interface working

---

## Phase 7: User Story 8 - Error Recovery and Retries (P2)

**Goal**: Automatic retry for failed requests to improve reliability

**Test**: Simulate network failures → verify retry behavior

### Implementation

- [ ] T063 [US8] Confirm ExponentialBackoffRetry in backend/src/utils/retry_utils.py defaults match spec FR-010: max_retries=3, initial_delay=1.0s, max_delay=32.0s, jitter=±25% (expected: PASS based on code review)
- [ ] T064 [US8] Verify retryable exceptions: RateLimitError, APITimeoutError, NetworkError
- [ ] T065 [US8] Verify non-retryable exceptions: InvalidTextError, AuthenticationError, VectorDimensionMismatchError
- [ ] T066 [US8] Verify retry callback logs attempt number, delay, error type
- [ ] T067 [US8] Verify rate limit detection in _to_service_error() extracts retry_after from error
- [ ] T068 [US8] Add rate limit hit logging in embedding_logger

**Acceptance**: Retries up to max ✓ | Exponential backoff ✓ | Fails gracefully after max retries ✓

**Checkpoint**: US8 complete - error recovery implemented

---

## Phase 8: User Story 4 - Single Text Vectorization (P3, Backend-only)

**Goal**: Backend API for single text vectorization (not exposed in frontend)

**Test**: Call /embedding/single with text → verify vector returned

### Implementation

- [ ] T069 [US4] Verify POST /embedding/single endpoint exists in backend/src/api/embedding_routes.py
- [ ] T070 [US4] Verify SingleEmbeddingRequest validation (non-empty text, valid model)
- [ ] T071 [US4] Verify error responses: 400 for empty text, 401 for auth failure, 429 for rate limit

**Acceptance**: Text → vector ✓ | Empty text → 400 ✓ | Long text handled ✓

**Checkpoint**: US4 complete - single text API working

---

## Phase 9: User Story 5 - Batch Text Vectorization (P3, Backend-only)

**Goal**: Backend API for batch text vectorization (not exposed in frontend)

**Test**: Call /embedding/batch with text array → verify all vectorized

### Implementation

- [ ] T072 [US5] Verify POST /embedding/batch endpoint exists in backend/src/api/embedding_routes.py
- [ ] T073 [US5] Verify BatchEmbeddingRequest validation (1-1000 texts, valid model)
- [ ] T074 [US5] Verify partial success handling (some texts fail, others succeed)
- [ ] T075 [US5] Verify error responses: 400 for invalid input, 413 for batch too large

**Acceptance**: 100 texts → 100 vectors ✓ | Partial success handled ✓ | >1000 texts → 413 ✓

**Checkpoint**: US5 complete - batch text API working

---

## Phase 10: User Story 7 - Model Information Query (P3)

**Goal**: Query model information for debugging and decision-making

**Test**: Call model info methods → verify returned data matches expected structure

### Implementation

- [ ] T076 [US7] Verify get_model_info() method in EmbeddingService returns current model specs
- [ ] T077 [US7] Verify list_available_models() static method returns all 4 models
- [ ] T078 [US7] Verify GET /embedding/models endpoint returns ModelsListResponse with count
- [ ] T079 [US7] Verify GET /embedding/models/{model_name} endpoint returns ModelInfo or 404

**Acceptance**: Model info query works ✓ | List models returns all 4 ✓

**Checkpoint**: US7 complete - model information query working

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Improvements across all user stories

- [ ] T080 [P] Verify all embedding results saved with source traceability (document_id, result_id)
- [ ] T081 [P] Verify file naming follows convention: {document_name}_{timestamp}.json
- [ ] T082 [P] Implement GET /embedding/health endpoint per NFR-001: validate API reachability (5s timeout), model availability via /v1/models, authentication validity; return status (healthy/degraded/unhealthy), api_connectivity, models_available, authentication, timestamp
- [ ] T083 [P] Verify operational logging captures: request_id, model, duration_ms, batch_size, successful_count, failed_count, retry_count, rate_limit_hits
- [ ] T084 [P] Review error messages for clarity and actionability
- [ ] T085 Run quickstart.md validation scenarios
- [ ] T086 Update documentation with final implementation notes

**Checkpoint**: All polish tasks complete - ready for production

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) → Phase 2 (Foundational) → BLOCKS → Phase 3-11 (User Stories + Polish)
                                                     ↓
                                    User Stories 1,2,6,3,8,4,5,7 (can proceed in parallel)
```

### User Story Independence

- **US1 (P1)**: Independent - no dependencies on other stories
- **US2 (P1)**: Independent - may call US1 method but testable alone
- **US6 (P1)**: Independent - model support validation
- **US3 (P1)**: Independent - frontend UI (depends on US1/US2 APIs existing)
- **US8 (P2)**: Independent - retry mechanism
- **US4 (P3)**: Independent - backend-only single text API
- **US5 (P3)**: Independent - backend-only batch text API
- **US7 (P3)**: Independent - model information query

### Within Each Story

- Models before services
- Services before endpoints
- Core implementation before error handling
- Backend APIs before frontend integration

### Parallel Opportunities

**Phase 1 (Setup)**: T001-T007 all [P] except verification order  
**Phase 2 (Foundational)**: T011-T014 [P] (model additions)  
**Phase 3 (US1)**: Models can be added in parallel if multiple exist  
**Phase 4 (US2)**: Can start after Phase 2, parallel with US1 if staffed  
**Phase 5 (US6)**: T032 [P] - validation tasks parallel  
**Phase 6 (US3)**: T042-T046 API methods [P], T047-T052 components [P]  
**Phase 11 (Polish)**: T080-T084 all [P]

---

## Implementation Strategy

### MVP First (User Stories 1, 2, 6 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (BLOCKS all stories)
3. Complete Phase 3: US1 (Vectorize Chunking Result)
4. Complete Phase 4: US2 (Vectorize Document Latest)
5. Complete Phase 5: US6 (Multi-Model Support)
6. **STOP and VALIDATE**: Backend MVP ready (can vectorize documents with 4 models)

### Full MVP (Add Frontend)

7. Complete Phase 6: US3 (Frontend Interface)
8. **STOP and VALIDATE**: Full MVP ready (backend + frontend)

### Incremental Delivery

9. Add Phase 7: US8 (Error Recovery) → Deploy
10. Add Phase 8: US4 (Single Text API) → Deploy
11. Add Phase 9: US5 (Batch Text API) → Deploy
12. Add Phase 10: US7 (Model Info Query) → Deploy
13. Complete Phase 11: Polish → Final deployment

### Parallel Team Strategy

With 3 developers after Phase 2 complete:
- Developer A: US1 + US2 (backend APIs)
- Developer B: US6 + US8 (models + retry)
- Developer C: US3 (frontend interface)

Then proceed to US4, US5, US7, Polish in priority order

---

## Task Summary

**Total Tasks**: 86  
**Setup**: 7 tasks  
**Foundational**: 7 tasks  
**User Story 1 (P1)**: 9 tasks  
**User Story 2 (P1)**: 8 tasks  
**User Story 6 (P1)**: 5 tasks  
**User Story 3 (P1)**: 26 tasks  
**User Story 8 (P2)**: 6 tasks  
**User Story 4 (P3)**: 3 tasks  
**User Story 5 (P3)**: 4 tasks  
**User Story 7 (P3)**: 4 tasks  
**Polish**: 7 tasks

**Parallel Opportunities**: 35 tasks marked [P]

**MVP Scope**: Phase 1-5 (36 tasks) → Backend MVP  
**Full MVP**: Phase 1-6 (62 tasks) → Backend + Frontend  

**Suggested First Sprint**: Phase 1-3 (US1 complete) → 25 tasks  
**Suggested Second Sprint**: Phase 4-6 (US2, US6, US3 complete) → 39 tasks  
**Suggested Third Sprint**: Phase 7-11 (remaining stories + polish) → 22 tasks
