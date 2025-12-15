# Tasks: Vector Embedding Module

**Input**: Design documents from `/specs/003-vector-embedding/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/src/`, `backend/tests/`
- **Frontend**: `frontend/src/`
- **Results**: `backend/results/embedding/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create results directory structure at backend/results/embedding/
- [x] T002 [P] Update backend/requirements.txt to ensure langchain-openai==0.2.14 is included
- [x] T003 [P] Verify environment variables in backend/.env for EMBEDDING_API_KEY and EMBEDDING_API_BASE_URL

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities and models that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [P] Create exponential backoff retry utility in backend/src/utils/retry_utils.py with ExponentialBackoffRetry class (1s-32s, jitter, max 3 retries)
- [x] T005 [P] Create structured logging utility in backend/src/utils/logging_utils.py with EmbeddingLogger class (JSON format, request_id, metrics)
- [x] T006 [P] Create Pydantic models in backend/src/models/embedding_models.py (SingleEmbeddingRequest, BatchEmbeddingRequest, SingleEmbeddingResponse, BatchEmbeddingResponse, Vector, EmbeddingFailure, EmbeddingMetadata)
- [x] T007 Create JSON storage layer in backend/src/storage/embedding_storage.py with EmbeddingStorage class (atomic writes, per-request files with naming convention embedding_{request_id}_{timestamp}.json)
- [x] T008 Create error classification enums and custom exceptions in backend/src/models/embedding_models.py (RateLimitError, APITimeoutError, InvalidTextError, VectorDimensionMismatchError, BatchSizeLimitError)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Single Text Vectorization (Priority: P1) 🎯 MVP

**Goal**: Enable single query text vectorization for basic semantic search

**Independent Test**: Provide text "人工智能是什么", verify vector returned with expected dimension (1536 for qwen3-embedding-8b)

### Implementation for User Story 1

- [x] T009 [US1] Enhance embedding_service.py: Add dimension validation method _validate_vector_dimensions() that fails immediately with clear error if mismatch
- [x] T010 [US1] Enhance embedding_service.py: Wrap embed_query() with retry logic using ExponentialBackoffRetry from retry_utils.py
- [x] T011 [US1] Enhance embedding_service.py: Add logging for single query operations (request_id, model, duration_ms, text_length)
- [x] T012 [US1] Enhance embedding_service.py: Add empty text validation in embed_query() (reject if only whitespace)
- [x] T013 [US1] Create FastAPI route POST /api/v1/embedding/single in backend/src/api/embedding_routes.py using SingleEmbeddingRequest model
- [x] T014 [US1] Implement single embedding endpoint handler: validate request, call embed_query(), build SingleEmbeddingResponse with metadata
- [x] T015 [US1] Add error handling middleware for single endpoint: catch InvalidTextError, AuthenticationError, VectorDimensionMismatchError and return appropriate HTTP status codes
- [x] T016 [US1] Persist single query result to JSON file using EmbeddingStorage.save_single_result() with request_id and timestamp
- [x] T017 [US1] Register embedding routes in backend/src/main.py with /api/v1 prefix

**Checkpoint**: Single text vectorization functional - can test with curl/Postman

---

## Phase 4: User Story 3 - Multi-Model Support (Priority: P1)

**Goal**: Support 4 embedding models with correct dimensions (BGE-M3: 1024, Qwen3: 1536, Hunyuan: 1024, Jina: 768)

**Independent Test**: Initialize with each model, verify vectors have correct dimensions

### Implementation for User Story 3

- [x] T018 [P] [US3] Verify EMBEDDING_MODELS dictionary in embedding_service.py contains all 4 models with correct configurations
- [x] T019 [US3] Add model name validation in embedding_service.__init__() that rejects unsupported models with list of valid options
- [x] T020 [US3] Update dimension validation to use model-specific expected dimensions from EMBEDDING_MODELS
- [x] T021 [US3] Test all 4 models through single embedding endpoint: qwen3-embedding-8b (1536), bge-m3 (1024), hunyuan-embedding (1024), jina-embeddings-v4 (768)

**Checkpoint**: All 4 models working with correct dimensions through single text endpoint

---

## Phase 5: User Story 2 - Batch Document Vectorization (Priority: P2)

**Goal**: Process multiple documents (1-1000) in single request with partial success handling

**Independent Test**: Provide 100 documents, verify 100 vectors returned with consistent dimensions

### Implementation for User Story 2

- [x] T022 [P] [US2] Add batch size validation (max 1000) in embedding_service.py with BatchSizeLimitError
- [x] T023 [US2] Implement embed_documents() with partial failure handling: process all documents, catch individual failures, accumulate successful vectors and failures list
- [x] T024 [US2] Add batch-level retry logic with exponential backoff in embed_documents()
- [x] T025 [US2] Add structured logging for batch operations: batch_size, successful_count, failed_count, processing_time_ms
- [x] T026 [US2] Create FastAPI route POST /api/v1/embedding/batch in backend/src/api/embedding_routes.py using BatchEmbeddingRequest model
- [x] T027 [US2] Implement batch embedding endpoint handler: validate batch size, call embed_documents(), build BatchEmbeddingResponse with status (SUCCESS/PARTIAL_SUCCESS/FAILED)
- [x] T028 [US2] Add error handling for batch endpoint: BatchSizeLimitError → 413, partial failures → 200 with failures array
- [x] T029 [US2] Persist batch result to JSON file using EmbeddingStorage.save_batch_result() including vectors and failures arrays
- [x] T030 [US2] Build EmbeddingFailure objects for failed documents with index, error_type, error_message, retry_recommended, retry_count

**Checkpoint**: Batch processing works with partial success and proper error reporting

---

## Phase 6: User Story 5 - Error Recovery and Retries (Priority: P2)

**Goal**: Automatic retry with exponential backoff for transient failures (rate limits, timeouts, network errors)

**Independent Test**: Simulate rate limit error, verify exponential backoff retries with increasing delays

### Implementation for User Story 5

- [x] T031 [US5] Implement rate limit detection in retry_utils.py: check for RateLimitError from API responses
- [x] T032 [US5] Add exponential backoff calculation with jitter: delay = min(initial_delay * (2 ** attempt), max_delay) + random jitter
- [x] T033 [US5] Implement timeout handling in embedding_service.py: wrap API calls with timeout (default 60s)
- [x] T034 [US5] Add retry logging: log each retry attempt with attempt_number, delay_ms, error_type
- [x] T035 [US5] Test retry behavior: verify max 3 attempts, verify backoff delays increase, verify final failure message after exhausting retries
- [x] T036 [US5] Add rate_limit_hits counter to EmbeddingMetadata

**Checkpoint**: Automatic retries working for rate limits and timeouts

---

## Phase 7: User Story 4 - Model Information Query (Priority: P3)

**Goal**: Query model information and list available models

**Independent Test**: Call GET /models, verify 4 models returned with correct specifications

### Implementation for User Story 4

- [x] T037 [P] [US4] Create FastAPI route GET /api/v1/models in backend/src/api/embedding_routes.py
- [x] T038 [P] [US4] Create FastAPI route GET /api/v1/models/{model_name} in backend/src/api/embedding_routes.py
- [x] T039 [US4] Implement list models endpoint: call EmbeddingService.list_available_models(), return ModelsListResponse
- [x] T040 [US4] Implement get model info endpoint: validate model_name, return ModelInfo or 404
- [x] T041 [P] [US4] Create FastAPI route GET /api/v1/health for health check (returns API connectivity status)

**Checkpoint**: Model information endpoints functional

---

## Phase 8: Frontend Integration

**Purpose**: Vue 3 + TDesign UI for embedding operations

- [x] T042 [P] Create API client in frontend/src/services/embeddingService.js with axios (embedSingle, embedBatch, listModels, getModelInfo)
- [x] T043 [P] Create EmbeddingView.vue in frontend/src/views/ with TDesign layout (left panel + right content)
- [x] T044 [P] Create EmbeddingPanel.vue component in frontend/src/components/ (model selection dropdown, text input textarea, batch file upload, submit button)
- [x] T045 [P] Create EmbeddingResults.vue component in frontend/src/components/ (vector display, dimension info, processing time, success/failure counts for batches)
- [x] T046 Add embedding route to frontend/src/router/index.js: /embedding path to EmbeddingView
- [x] T047 Update frontend navigation in frontend/src/App.vue or frontend/src/layouts/MainLayout.vue to include Embedding link
- [x] T048 Implement model selection: fetch models on mount, populate t-select with model names and dimensions
- [x] T049 Implement single text submission: call embedSingle API, display vector result in EmbeddingResults
- [x] T050 Implement batch file upload: parse CSV/JSON file, call embedBatch API, display results with failure details
- [x] T051 Add loading states and error messages using TDesign components (t-loading, t-message)

**Checkpoint**: Full UI functional for single and batch operations

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Production readiness improvements

- [x] T052 [P] Add comprehensive error messages following FR-005 (invalid model, auth failure, timeout, dimension mismatch)
- [x] T053 [P] Verify all operational metrics logged per FR-014 (request counts, latencies, model usage, error rates, batch sizes)
- [x] T054 [P] Add request_id generation using uuid4 for all requests
- [x] T055 [P] Implement API key authentication middleware using X-API-Key header
- [x] T056 [P] Add CORS configuration for frontend-backend communication
- [x] T057 Test performance: verify <2s single query (SC-001), <30s for 100 docs (SC-002)
- [x] T058 Test dimension validation: send mock API response with wrong dimensions, verify immediate failure
- [x] T059 Test batch size limit: send 1001 documents, verify 413 error with clear message
- [x] T060 Test partial success: batch with 1 invalid document among valid ones, verify continued processing
- [x] T061 Validate quickstart.md examples work as documented
- [ ] T062 [P] Add database metadata tracking (optional): create embedding_requests and embedding_failures tables if SQLite integration desired
- [x] T063 Code review: verify constitution compliance (modular, multi-provider, JSON persistence, UX-focused, API standardized)
- [x] T064 [P] Implement authentication error detection in backend/src/api/embedding_routes.py: catch invalid/expired API key errors and return clear error message with FR-013 compliance

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (T004-T008) - Core MVP
- **User Story 3 (Phase 4)**: Depends on User Story 1 (T009-T017) - Extends single text with multi-model
- **User Story 2 (Phase 5)**: Depends on User Story 1 (T009-T017) - Batch processing builds on single
- **User Story 5 (Phase 6)**: Depends on Foundational (T004) - Enhances retry logic
- **User Story 4 (Phase 7)**: Depends on User Story 1 (T009-T017) - Info endpoints are independent
- **Frontend (Phase 8)**: Depends on backend endpoints (T013-T041)
- **Polish (Phase 9)**: Depends on core user stories (Phase 3-7)

### User Story Dependencies

```
Foundational (T004-T008)
    ↓
US1: Single Text (T009-T017) ← MVP BLOCKER
    ↓
    ├→ US3: Multi-Model (T018-T021) ← Extends US1
    ├→ US2: Batch (T022-T030) ← Builds on US1
    ├→ US4: Model Info (T037-T041) ← Independent
    └→ US5: Retries (T031-T036) ← Enhances error handling
```

### Within Each User Story

- **US1**: T009-T012 (service enhancements) can run in parallel → T013 (route) → T014-T016 (handler & persistence) → T017 (registration)
- **US3**: All tasks T018-T021 can run in parallel (testing different models)
- **US2**: T022-T025 (service) can run in parallel → T026 (route) → T027-T030 (handler & persistence)
- **US5**: T031-T035 can run in parallel → T036 (metadata)
- **US4**: T037-T038, T041 can run in parallel → T039-T040 (implementations)

### Parallel Opportunities

**Within Foundational Phase**:
- T004, T005, T006 (different files) can run in parallel
- T007, T008 depend on T006 (need models first)

**Within US1**:
- T009, T010, T011, T012 (different enhancements to same file) should be sequential OR use feature branches
- T015, T016 can run in parallel

**Within US2**:
- T022, T023, T024, T025 can be done in sequence (same file)
- T028, T029, T030 can run in parallel

**Across User Stories (if team capacity)**:
- After US1 complete: US2, US3, US4, US5 can all start in parallel by different developers

---

## Parallel Example: Foundational Phase

```bash
# Launch in parallel (different files):
Developer A: "Create retry utility in retry_utils.py" (T004)
Developer B: "Create logging utility in logging_utils.py" (T005)
Developer C: "Create Pydantic models in embedding_models.py" (T006)

# After T006 complete, launch next batch:
Developer A: "Create storage layer in embedding_storage.py" (T007)
Developer B: "Create error enums in embedding_models.py" (T008)
```

---

## Parallel Example: User Story 1

```bash
# Service enhancements (sequential in same file or use branches):
1. Add dimension validation (T009)
2. Wrap with retry logic (T010)
3. Add logging (T011)
4. Add empty text validation (T012)

# After service ready, parallel on different components:
Developer A: "Create API route" (T013)
Developer B: "Implement endpoint handler" (T014)
Developer C: "Add error middleware" (T015)
Developer D: "Implement persistence" (T016)
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 3 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T008) → CRITICAL
3. Complete Phase 3: User Story 1 (T009-T017) → MVP Core
4. Complete Phase 4: User Story 3 (T018-T021) → MVP Complete
5. **STOP and VALIDATE**: Test single text with all 4 models
6. Deploy/demo MVP

**MVP Deliverable**: Single query vectorization with 4 model options

### Incremental Delivery

1. **Sprint 1**: Setup + Foundational + US1 + US3 → MVP (single text, 4 models)
2. **Sprint 2**: US2 → Add batch processing (1-1000 docs)
3. **Sprint 3**: US5 → Add retry/reliability
4. **Sprint 4**: US4 + Frontend → Full UI integration
5. **Sprint 5**: Polish → Production ready

### Parallel Team Strategy

With 3 developers after Foundational phase:

1. **Team completes**: Setup + Foundational together
2. **After Foundational done**:
   - **Developer A**: User Story 1 (T009-T017) - Core single text
   - **Developer B**: User Story 3 (T018-T021) - Model validation (depends on US1 partially)
   - **Developer C**: Start User Story 4 setup (T037-T038) - Independent
3. **After US1 complete**:
   - **Developer A**: User Story 2 (T022-T030) - Batch processing
   - **Developer B**: User Story 5 (T031-T036) - Retry enhancements
   - **Developer C**: Complete User Story 4 (T039-T041) - Model endpoints
4. **After all backend done**:
   - **Team**: Frontend integration together (T042-T051)

---

## Task Summary

**Total Tasks**: 64

**By Phase**:
- Phase 1 (Setup): 3 tasks
- Phase 2 (Foundational): 5 tasks
- Phase 3 (US1 - Single Text): 9 tasks
- Phase 4 (US3 - Multi-Model): 4 tasks
- Phase 5 (US2 - Batch): 9 tasks
- Phase 6 (US5 - Retries): 6 tasks
- Phase 7 (US4 - Model Info): 5 tasks
- Phase 8 (Frontend): 10 tasks
- Phase 9 (Polish): 13 tasks

**By User Story**:
- US1 (Single Text - P1): 9 tasks → MVP Core
- US2 (Batch - P2): 9 tasks
- US3 (Multi-Model - P1): 4 tasks → MVP Critical
- US4 (Model Info - P3): 5 tasks
- US5 (Retries - P2): 6 tasks
- Foundational: 5 tasks (blocking)
- Setup: 3 tasks
- Frontend: 10 tasks
- Polish: 13 tasks

**Parallelizable**: 24 tasks marked [P] can run concurrently with other tasks

**Critical Path for MVP**: T001-T008 (Setup + Foundational) → T009-T017 (US1) → T018-T021 (US3) = 21 tasks

---

## Success Validation

After completing MVP (US1 + US3):

✅ **SC-001**: Single query returns in <2s  
✅ **SC-003**: All 4 models generate correct dimensions  
✅ **SC-005**: Clear error messages for invalid inputs  
✅ **SC-006**: Model switching via configuration  
✅ **SC-007**: 95% first-attempt success

After completing US2:

✅ **SC-002**: 100 docs in <30s

After completing US5:

✅ **SC-004**: 80% retry recovery rate

After completing all:

✅ **SC-008**: Operational metrics logging complete

---

## Notes

- **Constitution Alignment**: All tasks preserve modular architecture, multi-provider support, JSON persistence, UX focus, API standardization
- **Independent Testing**: Each user story can be tested independently after its checkpoint
- **Fail Fast**: Dimension validation and input validation happen immediately per design decisions
- **Partial Success**: US2 batch processing maximizes throughput per clarification decision
- **Exponential Backoff**: US5 implements 1s-32s with jitter per research findings
- **Performance**: Validate SC-001 (<2s) and SC-002 (<30s) during polish phase
- Commit frequently after each task or logical group
- Use feature branches for parallel work on same files
- Verify quickstart.md examples during T061
