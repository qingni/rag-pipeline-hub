# Tasks: 文档分块功能

**Input**: Design documents from `/specs/002-doc-chunking/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/chunking-api.yaml

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/src/`
- **Frontend**: `frontend/src/`
- **Results**: `results/chunking/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and directory structure for chunking module

- [X] T001 Create chunking results directory at `results/chunking/`
- [X] T002 [P] Create backend providers directory structure at `backend/src/providers/chunkers/`
- [X] T003 [P] Create frontend chunking components directory at `frontend/src/components/chunking/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Database Schema

- [X] T004 Create database migration for chunking tables using alembic
- [X] T005 [P] Create ChunkingTask model in `backend/src/models/chunking_task.py`
- [X] T006 [P] Create ChunkingStrategy model in `backend/src/models/chunking_strategy.py`
- [X] T007 [P] Create ChunkingResult model in `backend/src/models/chunking_result.py`
- [X] T008 [P] Create DocumentChunk model in `backend/src/models/document_chunk.py`

### Core Service Infrastructure

- [ ] T009 Create base chunker abstract class in `backend/src/providers/chunkers/base_chunker.py`
- [ ] T010 Create ChunkingService class skeleton in `backend/src/services/chunking_service.py`
- [ ] T011 Implement source document loading method in ChunkingService
- [ ] T012 Create chunking parameter validator in `backend/src/utils/chunking_validators.py`
- [ ] T013 Create chunking helper utilities in `backend/src/utils/chunking_helpers.py`

### API Foundation

- [ ] T014 Create API router skeleton in `backend/src/api/chunking.py`
- [ ] T015 Implement GET /api/documents/parsed endpoint
- [ ] T016 Implement GET /api/chunking/strategies endpoint
- [ ] T017 Seed database with 4 default chunking strategies

### Frontend Foundation

- [ ] T018 [P] Create chunking service API client in `frontend/src/services/chunkingService.js`
- [ ] T019 [P] Create chunking Pinia store in `frontend/src/stores/chunkingStore.js`
- [ ] T020 Add chunking route to `frontend/src/router/index.js`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - 基于加载结果的文档分块 (Priority: P1) 🎯 MVP

**Goal**: 用户可以选择已解析的文档，应用分块策略，查看分块结果，并保存分块数据供下游模块使用

**Independent Test**: 加载已保存的文档解析JSON结果，选择按段落分块策略，配置块大小为500字符、重叠度为50字符，查看分块预览，并验证生成的分块JSON文件格式正确、包含所有必需字段

### Chunking Strategies Implementation

- [ ] T021 [P] [US1] Implement CharacterChunker in `backend/src/providers/chunkers/character_chunker.py`
- [ ] T022 [P] [US1] Implement ParagraphChunker in `backend/src/providers/chunkers/paragraph_chunker.py`
- [ ] T023 [P] [US1] Create chunker factory in `backend/src/providers/chunkers/__init__.py`

### Core Chunking Logic

- [ ] T024 [US1] Implement chunk processing logic in ChunkingService
- [ ] T025 [US1] Implement JSON result file generation in ChunkingService
- [ ] T026 [US1] Implement database persistence for chunking results
- [ ] T027 [US1] Implement statistics calculation in ChunkingService

### Backend API Endpoints

- [ ] T028 [US1] Implement POST /api/chunking/chunk endpoint
- [ ] T029 [US1] Implement GET /api/chunking/task/{task_id} endpoint
- [ ] T030 [US1] Implement GET /api/chunking/result/{result_id} endpoint

### Frontend Components - Document Selection & Strategy

- [ ] T031 [P] [US1] Create DocumentSelector component in `frontend/src/components/chunking/DocumentSelector.vue`
- [ ] T032 [P] [US1] Create StrategySelector component in `frontend/src/components/chunking/StrategySelector.vue`
- [ ] T033 [P] [US1] Create ParameterConfig component in `frontend/src/components/chunking/ParameterConfig.vue`
- [ ] T033a [US1] Implement real-time chunk count estimation in ParameterConfig component

### Frontend Components - Results Display

- [ ] T034 [P] [US1] Create ChunkingProgress component in `frontend/src/components/chunking/ChunkingProgress.vue`
- [ ] T035 [P] [US1] Create ChunkList component in `frontend/src/components/chunking/ChunkList.vue`
- [ ] T036 [P] [US1] Create ChunkDetail component in `frontend/src/components/chunking/ChunkDetail.vue`

### Frontend Main View

- [ ] T037 [US1] Create ChunkingView main page in `frontend/src/views/ChunkingView.vue`
- [ ] T038 [US1] Integrate all components into ChunkingView with left panel layout
- [ ] T039 [US1] Implement real-time parameter preview display
- [ ] T040 [US1] Implement task status polling logic

### Integration

- [ ] T041 [US1] Wire up API calls in chunking store
- [ ] T042 [US1] Implement error handling and user feedback messages
- [ ] T043 [US1] Add loading states for all async operations

**Checkpoint**: At this point, User Story 1 should be fully functional - users can select documents, apply character/paragraph chunking, configure parameters with real-time chunk count preview, view results, and saved JSON files should match the schema

---

## Phase 4: User Story 2 - 多种分块策略支持 (Priority: P2)

**Goal**: 用户可以根据不同的文档类型和使用场景，选择最适合的分块策略（按标题、按语义），并理解每种策略的适用场景和降级机制

**Independent Test**: 使用同一文档分别应用按标题分块（验证标题层级识别）和按语义分块（验证语义边界识别或自动降级），对比各策略的分块结果，验证元数据中的降级标记和错误提示

### Advanced Chunking Strategies

- [ ] T044 [P] [US2] Create HeadingDetector class in `backend/src/utils/chunking_helpers.py`
- [ ] T045 [P] [US2] Implement HeadingChunker in `backend/src/providers/chunkers/heading_chunker.py`
- [ ] T046 [US2] Implement SemanticChunker with TF-IDF similarity in `backend/src/providers/chunkers/semantic_chunker.py`

### Strategy Validation & Fallback

- [ ] T047 [US2] Implement heading structure detection in HeadingChunker
- [ ] T048 [US2] Add heading structure validation before chunking
- [ ] T049 [US2] Implement semantic chunking fallback mechanism
- [ ] T050 [US2] Add fallback metadata recording to chunks

### Frontend Strategy Enhancements

- [ ] T051 [US2] Update StrategySelector to include heading and semantic options
- [ ] T052 [US2] Add strategy description tooltips in StrategySelector
- [ ] T053 [US2] Implement strategy-specific parameter fields in ParameterConfig
- [ ] T054 [US2] Add fallback status display in ChunkDetail metadata

### API Updates

- [ ] T055 [US2] Implement POST /api/chunking/preview endpoint for strategy testing
- [ ] T056 [US2] Update chunking validation to check heading structure for heading strategy
- [ ] T057 [US2] Add strategy recommendation logic based on document structure

**Checkpoint**: At this point, all 4 chunking strategies work independently - heading strategy shows error for unstructured docs, semantic strategy falls back gracefully, and users see appropriate feedback

---

## Phase 5: User Story 3 - 分块结果管理和导出 (Priority: P3)

**Goal**: 用户可以管理已生成的分块结果，查看历史记录，对比不同策略的效果，删除不需要的数据，导出结果供外部使用

**Independent Test**: 查看分块历史列表（验证分页和过滤功能），选择两个不同策略的分块结果进行对比（验证统计对比显示），删除测试用的分块数据（验证JSON文件和数据库记录同步删除），导出分块JSON和CSV文件（验证格式完整性）

### Queue Management System

- [ ] T058 [US3] Create ChunkingQueueManager class in ChunkingService
- [ ] T059 [US3] Implement asyncio queue with max 3 concurrent tasks
- [ ] T060 [US3] Implement task queuing logic
- [ ] T061 [US3] Implement GET /api/chunking/queue endpoint

### History & Pagination Backend

- [ ] T062 [US3] Implement paginated history query in ChunkingService
- [ ] T063 [US3] Add filtering logic (document_name, strategy, created_at)
- [ ] T064 [US3] Add sorting logic with multiple fields
- [ ] T065 [US3] Implement GET /api/chunking/history endpoint with pagination

### Comparison & Export Backend

- [ ] T066 [P] [US3] Implement comparison logic in ChunkingService
- [ ] T067 [P] [US3] Implement POST /api/chunking/compare endpoint
- [ ] T068 [P] [US3] Implement JSON export in ChunkingService
- [ ] T069 [P] [US3] Implement CSV export with streaming in ChunkingService
- [ ] T070 [US3] Implement GET /api/chunking/export/{result_id} endpoint

### Delete Functionality

- [ ] T071 [US3] Implement result deletion logic in ChunkingService (DB + file)
- [ ] T072 [US3] Implement DELETE /api/chunking/result/{result_id} endpoint
- [ ] T073 [US3] Add cascade delete for related chunks

### Frontend History Components

- [ ] T074 [P] [US3] Create HistoryList component with pagination in `frontend/src/components/chunking/HistoryList.vue`
- [ ] T075 [P] [US3] Create CompareResults component in `frontend/src/components/chunking/CompareResults.vue`
- [ ] T076 [P] [US3] Create ExportDialog component in `frontend/src/components/chunking/ExportDialog.vue`

### Frontend History Integration

- [ ] T077 [US3] Add history tab to ChunkingView
- [ ] T078 [US3] Implement pagination controls in HistoryList
- [ ] T079 [US3] Implement filter inputs (document name, strategy, date range)
- [ ] T080 [US3] Implement sorting controls (by date, chunks, processing time)
- [ ] T081 [US3] Implement multi-select for comparison
- [ ] T082 [US3] Implement delete confirmation dialog
- [ ] T083 [US3] Wire up export download functionality

### Queue Status Display

- [ ] T084 [US3] Add queue status panel to ChunkingView
- [ ] T085 [US3] Implement queue polling for real-time updates
- [ ] T086 [US3] Display running tasks and queued tasks count

**Checkpoint**: All user stories are now independently functional - history management works with 500+ records, comparison shows statistical differences, exports work in both formats, queue management prevents overload

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final validation

### Error Recovery & Partial Results

- [ ] T087 [P] Implement partial result saving on errors
- [ ] T088 [P] Add error position tracking in ChunkingService
- [ ] T089 Add partial status display in frontend

### Performance Optimization

- [ ] T090 [P] Add database indexes for common queries (document_name, created_at)
- [ ] T091 [P] Optimize chunk loading with lazy loading for large results
- [ ] T092 Test pagination performance with 500+ records
- [ ] T093 Verify 10k character document chunks in < 5 seconds
- [ ] T094 Verify 50k character document chunks in < 30 seconds

### Documentation & Validation

- [ ] T095 [P] Update main README.md with chunking feature documentation
- [ ] T096 [P] Add API documentation comments to all endpoints
- [ ] T097 Run quickstart.md validation checklist
- [ ] T098 Verify all Success Criteria (SC-001 through SC-009)
- [ ] T099 Manual testing of all edge cases from spec.md

### Code Quality

- [ ] T100 [P] Add docstrings to all service methods
- [ ] T101 [P] Add type hints to all Python functions
- [ ] T102 Code cleanup and refactoring for maintainability
- [ ] T103 [P] Frontend component prop validation
- [ ] T104 Security review (input validation, file path sanitization)
- [ ] T105 [P] Create parameter validation test suite covering all edge cases (chunk_size boundaries, overlap > size, negative values, etc.)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1 (P1): Can start after Phase 2 - No dependencies on other stories
  - US2 (P2): Can start after Phase 2 - Extends US1 strategies but independently testable
  - US3 (P3): Can start after Phase 2 - Manages US1/US2 results but independently testable
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Foundation required ✓ | No dependencies on other stories
  - Delivers: Basic chunking with character & paragraph strategies
  - MVP Ready: Yes - can deploy after this story alone
  
- **User Story 2 (P2)**: Foundation required ✓ | No dependencies on other stories
  - Delivers: Advanced strategies (heading & semantic)
  - MVP Ready: Yes - each strategy works independently
  
- **User Story 3 (P3)**: Foundation required ✓ | No dependencies on other stories
  - Delivers: History management, comparison, export, queue
  - MVP Ready: Yes - can manage results from any strategy

### Within Each User Story

**User Story 1**:
1. Strategies (T021-T023) - Parallel ✓
2. Core logic (T024-T027) - Sequential (depends on strategies)
3. API endpoints (T028-T030) - Parallel after core logic ✓
4. Frontend components (T031-T036) - All parallel ✓
5. Main view (T037-T043) - Sequential (needs components)

**User Story 2**:
1. Advanced strategies (T044-T046) - Can run in parallel ✓
2. Validation & fallback (T047-T050) - Sequential
3. Frontend updates (T051-T054) - Parallel ✓
4. API updates (T055-T057) - Parallel ✓

**User Story 3**:
1. Queue manager (T058-T061) - Sequential
2. History backend (T062-T065) - Sequential (but parallel with queue)
3. Comparison & Export (T066-T070) - All parallel ✓
4. Delete (T071-T073) - Sequential
5. Frontend components (T074-T076) - All parallel ✓
6. Integration (T077-T086) - Sequential (needs components)

### Parallel Opportunities

**Setup Phase**:
- T002 (backend dirs) + T003 (frontend dirs) = Parallel ✓

**Foundational Phase**:
- T005-T008 (all models) = Parallel ✓
- T018 (API client) + T019 (store) = Parallel ✓

**User Story 1**:
- T021 + T022 (chunkers) = Parallel ✓
- T028 + T029 + T030 (endpoints) = Parallel ✓
- T031 + T032 + T033 (selectors) = Parallel ✓
- T034 + T035 + T036 (results display) = Parallel ✓

**User Story 2**:
- T044 + T045 (heading) + T046 (semantic) = Parallel ✓
- T051 + T052 + T053 + T054 (frontend) = Parallel ✓
- T055 + T056 + T057 (API) = Parallel ✓

**User Story 3**:
- T066 + T067 (compare) + T068 + T069 (export) = Parallel ✓
- T074 + T075 + T076 (frontend components) = Parallel ✓
- T087 + T088 (error recovery) = Parallel ✓
- T090 + T091 (performance) = Parallel ✓
- T095 + T096 (docs) = Parallel ✓
- T100 + T101 + T103 (code quality) = Parallel ✓

---

## Parallel Example: User Story 1 Core Implementation

```bash
# After Phase 2 complete, launch multiple tasks simultaneously:

# Backend - Strategies (all independent files)
Task T021: "Implement CharacterChunker in backend/src/providers/chunkers/character_chunker.py"
Task T022: "Implement ParagraphChunker in backend/src/providers/chunkers/paragraph_chunker.py"

# Frontend - Components (all independent files)
Task T031: "Create DocumentSelector component in frontend/src/components/chunking/DocumentSelector.vue"
Task T032: "Create StrategySelector component in frontend/src/components/chunking/StrategySelector.vue"
Task T033: "Create ParameterConfig component in frontend/src/components/chunking/ParameterConfig.vue"
Task T034: "Create ChunkingProgress component in frontend/src/components/chunking/ChunkingProgress.vue"
Task T035: "Create ChunkList component in frontend/src/components/chunking/ChunkList.vue"
Task T036: "Create ChunkDetail component in frontend/src/components/chunking/ChunkDetail.vue"

# Result: 8 tasks completed simultaneously instead of sequentially
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (3 tasks, ~10 minutes)
2. Complete Phase 2: Foundational (17 tasks, ~2-3 days)
   - **GATE**: Must be 100% complete before proceeding
3. Complete Phase 3: User Story 1 (23 tasks, ~3-4 days)
   - Delivers: Basic chunking with 2 strategies (character, paragraph)
   - Users can: Select doc → Configure params → Chunk → View results
4. **STOP and VALIDATE**: 
   - Test with real documents
   - Verify JSON output format
   - Check SC-001, SC-002, SC-003, SC-006
5. **MVP READY**: Can deploy/demo basic chunking functionality

### Incremental Delivery

1. **Foundation** (Phase 1 + 2) → Database ready, API skeleton ready
2. **MVP** (+ Phase 3) → Basic chunking works, 2 strategies available
3. **Full Strategies** (+ Phase 4) → All 4 strategies, fallback logic, previews
4. **Production Ready** (+ Phase 5) → History, comparison, export, queue management
5. **Polished** (+ Phase 6) → Performance optimized, fully documented

### Parallel Team Strategy

With 3 developers after Foundational phase completion:

**Week 1**:
- Developer A: User Story 1 backend (T021-T030)
- Developer B: User Story 1 frontend (T031-T043)
- Developer C: User Story 2 strategies (T044-T050)

**Week 2**:
- Developer A: User Story 3 backend (T058-T073)
- Developer B: User Story 2 frontend (T051-T057)
- Developer C: User Story 3 frontend (T074-T086)

**Week 3**:
- All: Phase 6 polish and testing (T087-T104)

---

## Task Count Summary

- **Phase 1 (Setup)**: 3 tasks
- **Phase 2 (Foundational)**: 17 tasks
- **Phase 3 (US1 - MVP)**: 24 tasks (includes T033a for real-time preview)
- **Phase 4 (US2 - Advanced Strategies)**: 14 tasks
- **Phase 5 (US3 - Management)**: 29 tasks
- **Phase 6 (Polish)**: 19 tasks (includes T105 for validation test suite)

**Total**: 106 tasks

### Tasks per User Story

- **User Story 1 (P1)**: 24 implementation tasks (MVP, includes real-time preview)
- **User Story 2 (P2)**: 14 implementation tasks
- **User Story 3 (P3)**: 29 implementation tasks

### Parallel Opportunities Identified

- **Setup**: 2/3 tasks can run in parallel
- **Foundational**: 8/17 tasks can run in parallel
- **User Story 1**: 12/24 tasks can run in parallel
- **User Story 2**: 10/14 tasks can run in parallel
- **User Story 3**: 17/29 tasks can run in parallel
- **Polish**: 11/19 tasks can run in parallel

**Total Parallelizable**: 60/106 tasks (~57%)

---

## Notes

- [P] marker indicates tasks that can run in parallel (different files, no blocking dependencies)
- [US1], [US2], [US3] labels map tasks to user stories from spec.md for traceability
- Each user story is independently completable and testable after foundational phase
- MVP can be achieved with just Phase 1 + 2 + 3 (44 tasks, ~1 week with 1-2 developers)
- Foundational phase is the critical path - invest time to complete it correctly
- Tests are not included as spec.md does not explicitly request TDD approach
- All file paths are exact and match the project structure from plan.md
- Success criteria validation (SC-001 through SC-009) happens in Phase 6
- Commit after each task or logical group for clean git history
