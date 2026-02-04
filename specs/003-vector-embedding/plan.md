# Implementation Plan: Vector Embedding Module

**Branch**: `003-vector-embedding` | **Date**: 2025-12-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-vector-embedding/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a vector embedding module that converts document chunks into vector representations using multiple embedding models (BGE-M3, Qwen3-Embedding-8B, Hunyuan-Embedding, Qwen3-VL-Embedding-8B). The module includes:
- Backend API endpoints for vectorizing chunking results and documents
- Database storage for embedding metadata with JSON file persistence for vectors
- Unified frontend interface at `/documents/embed` with automatic display of historical results
- Support for multiple embedding models with automatic retry and error handling
- Query APIs for retrieving and managing embedding history

## Technical Context

**Language/Version**: Python 3.11+ (backend), JavaScript/ES2020+ (frontend)
**Primary Dependencies**: 
- Backend: FastAPI 0.104+, SQLAlchemy 2.0+, LangChain 0.3+, langchain-openai 0.2+, OpenAI 1.109+
- Frontend: Vue 3.3+, TDesign Vue Next 1.13+, Vue Router 4.2+, Pinia 2.1+, Axios 1.6+
**Storage**: SQLite database (app.db) for metadata, JSON files for vector values
**Testing**: pytest 7.4+, pytest-asyncio, httpx (backend); Vite test framework (frontend)
**Target Platform**: Linux/macOS server (backend), Modern browsers (Chrome 90+, Firefox 88+, Safari 14+)
**Project Type**: Web application (separate backend and frontend)
**Performance Goals**: 
- Vectorization: <30s for 100 chunks under normal conditions
- Query API: <100ms for latest result query, <200ms for paginated list (10K records)
- Frontend display: <500ms to show historical results after document selection
**Constraints**: 
- Dual-write atomicity: <5s for 100 vectors (4096-dim) JSON+DB write
- No orphaned JSON files (rollback mechanism required)
- Maximum batch size: 1000 texts
- OpenAI-compatible API protocol required
**Scale/Scope**: 
- Support 4 embedding models with dimensions 768-4096
- Handle documents with 1000+ chunks per vectorization
- Store and query 10,000+ embedding result records

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Evidence |
|-----------|------------|----------|
| **I. 模块化架构** | ✅ PASS | Embedding module has independent service layer (`embedding_service.py`), clear API routes (`embedding_routes.py`, `embedding_query_routes.py`), and separate storage layer (`embedding_db.py`, `embedding_storage_dual.py`) |
| **II. 多提供商支持** | ✅ PASS | Supports 4 embedding models (BGE-M3, Qwen3-Embedding-8B, Hunyuan-Embedding, Qwen3-VL-Embedding-8B) via OpenAI-compatible protocol, allowing future provider additions |
| **III. 结果持久化 (NON-NEGOTIABLE)** | ✅ PASS | All embedding results stored as JSON files with naming convention `{document_id}_{timestamp}.json`, metadata stored in `embedding_results` database table with file path reference |
| **IV. 用户体验优先** | ✅ PASS | Frontend uses Vue3 + TDesign Vue Next, unified `/documents/embed` route, two-column layout (left: controls, right: results), automatic display of historical results on document selection |
| **V. API标准化** | ✅ PASS | FastAPI-based RESTful endpoints with standardized error handling, OpenAPI documentation, unified response format, health check endpoint |

**Gate Status**: ✅ **ALL GATES PASSED** - No violations, proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/003-vector-embedding/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── embedding-api.yaml          # OpenAPI spec for embedding endpoints
│   └── embedding-query-api.yaml    # OpenAPI spec for query endpoints
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   ├── embedding_models.py        # ✅ EXISTS - Error classes, embedding models config
│   │   └── embedding_result.py        # 🆕 NEW - EmbeddingResult ORM model
│   ├── services/
│   │   └── embedding_service.py       # ✅ EXISTS - Core embedding service with chunking support
│   ├── storage/
│   │   ├── embedding_db.py            # ✅ EXISTS - Database operations for embedding results
│   │   ├── embedding_storage.py       # ✅ EXISTS - JSON file storage for vectors
│   │   └── embedding_storage_dual.py  # ✅ EXISTS - Dual-write coordinator
│   ├── api/
│   │   ├── embedding_routes.py        # ✅ EXISTS - Vectorization endpoints
│   │   └── embedding_query_routes.py  # ✅ EXISTS - Query endpoints
│   └── main.py                        # ✅ MODIFY - Register embedding routes
└── tests/
    ├── integration/
    │   ├── test_embedding_api.py              # 🆕 NEW - API integration tests
    │   └── test_embedding_dual_write.py       # 🆕 NEW - Dual-write transaction tests
    └── unit/
        ├── test_embedding_service.py          # 🆕 NEW - Service layer unit tests
        └── test_embedding_storage.py          # 🆕 NEW - Storage layer unit tests

frontend/
├── src/
│   ├── pages/
│   │   └── DocumentEmbedding.vue      # 🆕 NEW - Unified embedding interface page
│   ├── components/
│   │   ├── DocumentSelector.vue       # 🆕 NEW - Document selector with chunking status
│   │   ├── EmbeddingModelSelector.vue # 🆕 NEW - Model selector with info panel
│   │   ├── EmbeddingResults.vue       # 🆕 NEW - Results display with metadata
│   │   └── EmbeddingHistory.vue       # 🆕 NEW - Historical results viewer
│   ├── services/
│   │   └── embedding.js               # 🆕 NEW - Embedding API client
│   ├── stores/
│   │   └── embedding.js               # 🆕 NEW - Pinia store for embedding state
│   └── router/
│       └── index.js                   # ✅ MODIFY - Add /documents/embed route
└── tests/
    └── embedding/
        ├── DocumentEmbedding.spec.js  # 🆕 NEW - Page component tests
        └── EmbeddingModels.spec.js    # 🆕 NEW - Model selector tests
```

**Structure Decision**: Web application structure with separate backend and frontend. Backend follows existing modular service-oriented pattern (services, models, storage, API layers). Frontend implements unified embedding interface using existing Vue3 + TDesign component library. New database migration required for `embedding_results` table.

## Complexity Tracking

> **No violations detected - this section intentionally left empty.**

All Constitution principles are satisfied without requiring complexity justifications. The implementation follows established patterns for modular architecture, multi-provider support, result persistence, user experience, and API standardization.

---

## Phase Completion Status

### ✅ Phase 0: Outline & Research - COMPLETE

**Artifacts Generated**:
- `research.md` - All technical decisions documented with rationales

**Research Topics Resolved**:
1. Database schema design for embedding results
2. Dual-write transaction strategy (JSON + DB)
3. Frontend state management for historical results
4. Model selector auto-switch behavior
5. Query API performance optimization
6. Error handling for partial vectorization failures
7. Frontend metadata display design

**Outcome**: All unknowns from Technical Context resolved. Ready for Phase 1.

---

### ✅ Phase 1: Design & Contracts - COMPLETE

**Artifacts Generated**:
- `data-model.md` - Complete entity definitions with validation rules
- `contracts/embedding-api.yaml` - OpenAPI 3.0 spec for vectorization endpoints
- `contracts/embedding-query-api.yaml` - OpenAPI 3.0 spec for query endpoints
- `quickstart.md` - Developer onboarding guide with step-by-step instructions
- `CODEBUDDY.md` - Updated agent context file (automated)

**Data Model Entities Defined**:
1. EmbeddingResult (database ORM model)
2. EmbeddingVectorFile (JSON file schema)
3. EmbeddingModel (configuration entity)
4. EmbeddingRequest variants (API request schemas)
5. EmbeddingResponse (API response schema)
6. EmbeddingQueryResponse (query API response)
7. DocumentSelectionState (frontend Pinia store)

**API Contracts**:
- 6 endpoints specified (vectorization + query + models + health)
- 15+ request/response schemas defined
- Error responses standardized
- Authentication patterns documented

**Outcome**: Design complete, contracts validated. Ready for Phase 2 (task breakdown via `/speckit.tasks`).

---

### 🔄 Phase 2: Task Breakdown - PENDING

**Next Command**: `/speckit.tasks`

This phase will generate `tasks.md` with implementation tasks organized by:
- Priority (P0/P1/P2/P3)
- Dependencies between tasks
- Estimated effort
- Acceptance criteria per task

**Not included in `/speckit.plan` output** - run `/speckit.tasks` separately to continue.

---

## Re-Validation of Constitution (Post-Design)

| Principle | Compliance | Evidence (Post-Design) |
|-----------|------------|------------------------|
| **I. 模块化架构** | ✅ PASS | Data model maintains separation: `embedding_service.py` (business logic), `embedding_db.py` (persistence), `embedding_routes.py` (API). Frontend components are modular (DocumentSelector, ModelSelector, Results display). |
| **II. 多提供商支持** | ✅ PASS | `EmbeddingModel` entity supports pluggable models via OpenAI-compatible protocol. Adding new model requires only config entry in `EMBEDDING_MODELS` dict. |
| **III. 结果持久化 (NON-NEGOTIABLE)** | ✅ PASS | `EmbeddingVectorFile` schema enforces JSON persistence. Database migration creates `embedding_results` table. Dual-write strategy ensures atomicity. |
| **IV. 用户体验优先** | ✅ PASS | Quickstart guide demonstrates Vue3 + TDesign implementation. Two-column layout specified. Historical result auto-display reduces user friction. |
| **V. API标准化** | ✅ PASS | OpenAPI contracts define standardized REST endpoints with consistent error handling. Health check endpoint follows best practices. |

**Final Gate Status**: ✅ **ALL GATES PASSED** - Design adheres to constitution.

---

## Summary

**Feature**: Vector Embedding Module  
**Branch**: `003-vector-embedding`  
**Status**: Phase 0 & Phase 1 COMPLETE

**What Was Delivered**:
1. ✅ Technical research with 7 key decisions documented
2. ✅ Complete data model with 7 entities, validation rules, and state machine
3. ✅ OpenAPI 3.0 contracts for 6 endpoints
4. ✅ Developer quickstart guide with troubleshooting
5. ✅ Updated agent context file (CODEBUDDY.md)

**What's Next**:
- Run `/speckit.tasks` to generate implementation task breakdown
- Implement backend database migration
- Develop API endpoints following contracts
- Build frontend components per design specs
- Write tests per quickstart guide

**Key Technical Decisions**:
- Dual-write strategy: JSON file first, then DB (with rollback)
- Database indexes: `(document_id, model)`, `created_at DESC`, `status`
- Frontend: Pinia store with automatic historical result display
- Performance: <30s for 100 chunks, <100ms for queries

---

**Planning Phase Complete** ✅  
Next step: `/speckit.tasks`
