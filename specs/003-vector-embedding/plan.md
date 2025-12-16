# Implementation Plan: Vector Embedding Module

**Branch**: `003-vector-embedding` | **Date**: 2025-12-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-vector-embedding/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

**Primary Requirement**: Implement a unified vector embedding module that converts document chunks into vector representations using multiple embedding models (BGE-M3, Qwen3-Embedding-8B, Hunyuan-Embedding, Jina-Embeddings-v4) with automatic retrieval from chunking results, robust error handling, and a streamlined frontend interface at `/documents/embed`.

**Technical Approach**: 
- Backend: Extend existing `EmbeddingService` with chunking result integration, expose APIs at `/embedding/from-chunking-result` and `/embedding/from-document`
- Frontend: Refactor to single unified page at `/documents/embed` with intelligent document filtering (show only chunked documents), automatic latest result selection, and two-column layout
- Integration: Connect to existing chunking storage, filter documents by chunking status, persist results per spec FR-019

## Technical Context

**Language/Version**: Python 3.9+ (backend), ES6+ (frontend)
**Primary Dependencies**: 
- Backend: FastAPI 0.104.1, LangChain 0.3.15, langchain-openai 0.2.14, SQLAlchemy 2.0.23, Pydantic 2.7.4
- Frontend: Vue 3.3.8, Vue Router 4.2.5, Pinia 2.1.7, TDesign Vue Next 1.13.1, Axios 1.6.2
**Storage**: PostgreSQL (via SQLAlchemy) for metadata, JSON files for embedding results
**Testing**: pytest 7.4.3, pytest-asyncio 0.21.1 (backend), unit tests via Vite (frontend)
**Target Platform**: Linux/macOS server (backend), Modern browsers (Chrome/Firefox/Safari)
**Project Type**: Web application (FastAPI backend + Vue 3 frontend)
**Performance Goals**: 
- Process 100 chunks within 30 seconds (batch parallel processing, not sequential chunk-by-chunk; assumes normal API latency <300ms per chunk)
- Single text vectorization <1s response time
- Frontend page load <2s
- 95% success rate for valid requests (24h rolling window, min 100 requests)
**Constraints**: 
- Max 1000 documents per batch request
- Max 3 retry attempts with exponential backoff
- 60s default request timeout
- Document selector must filter 100% of unchunked documents
**Scale/Scope**: 
- Support 4 embedding models (see spec FR-006 for complete list)
- Handle documents with 50-500 chunks
- Frontend: 2 core pages (unified embedding interface + results display)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Core Principles Compliance

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. 模块化架构** | ✅ PASS | Feature implemented as independent embedding module with dedicated service layer (`embedding_service.py`), storage layer (`embedding_storage.py`), and API routes (`embedding_routes.py`). Clear interface separation between modules. |
| **II. 多提供商支持** | ✅ PASS | Supports 4 embedding models (BGE-M3, Qwen3-Embedding-8B, Hunyuan-Embedding, Jina-Embeddings-v4) via OpenAI-compatible protocol. Extensible model registry pattern allows adding new providers. |
| **III. 结果持久化 (NON-NEGOTIABLE)** | ✅ PASS | All embedding results saved as JSON files with standardized naming (`{document_name}_{timestamp}.json`). Includes source traceability (chunking result ID or document ID). |
| **IV. 用户体验优先** | ✅ PASS | Frontend uses Vue3 + TDesign Vue Next. Unified `/documents/embed` page with two-column layout (left: controls, right: results). Smart document filtering, automatic result selection. |
| **V. API标准化** | ✅ PASS | RESTful API design under `/embedding` prefix. Standardized error handling, unified response format, health check endpoint. OpenAPI documentation. |

### ✅ Technical Stack Compliance

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| **Frontend: Vue3 + Vite + TDesign** | ✅ PASS | Vue 3.3.8, Vite 5.0.4, TDesign Vue Next 1.13.1 confirmed in `package.json` |
| **Frontend: Vue Router 4** | ✅ PASS | Vue Router 4.2.5, single route `/documents/embed` |
| **Frontend: Pinia** | ✅ PASS | Pinia 2.1.7, state managed via `stores/embedding.js` |
| **Backend: FastAPI** | ✅ PASS | FastAPI 0.104.1, async route handlers |
| **Backend: Service Layer Pattern** | ✅ PASS | Dedicated `embedding_service.py` with business logic isolation |
| **Backend: JSON Storage** | ✅ PASS | `embedding_storage.py` handles JSON persistence |

### 🔍 Constitution Re-Check Required After Phase 1

✅ **Phase 1 Constitution Re-Check Completed**

| Check Item | Status | Evidence |
|------------|--------|----------|
| **Data model alignment** | ✅ PASS | Entities align with existing chunking schema (ChunkingResult, ChunkingTask, Chunk). No conflicts detected. |
| **API contract compatibility** | ✅ PASS | RESTful API design follows existing patterns (`/embedding` prefix mirrors `/documents`, `/chunking`). OpenAPI schema compatible with downstream consumers. |
| **Storage naming convention** | ✅ PASS | File naming follows constitution pattern: `{document_name}_{timestamp}.json` (e.g., `research_paper_20251215_103045.json`) |
| **Result persistence** | ✅ PASS | JSON format with complete source traceability (document_id, result_id), metadata, and config snapshot. |
| **Integration dependencies** | ✅ PASS | Successfully integrates with existing Document, ChunkingResult, ChunkingTask, and Chunk models without schema changes. |

**Conclusion**: All constitution principles maintained after Phase 1 design. No violations introduced.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Web application structure (backend + frontend detected)

backend/
├── src/
│   ├── api/
│   │   └── embedding_routes.py          # API endpoints: /single, /batch, /from-chunking-result, /from-document
│   ├── models/
│   │   ├── embedding_models.py          # Pydantic request/response models, error types
│   │   ├── chunking_result.py           # Database model for chunking results
│   │   ├── chunking_task.py             # Database model for chunking tasks
│   │   └── chunk.py                     # Database model for individual chunks
│   ├── services/
│   │   └── embedding_service.py         # Core embedding logic, model management, retry handling
│   ├── storage/
│   │   ├── embedding_storage.py         # JSON result persistence
│   │   └── database.py                  # SQLAlchemy session management
│   └── utils/
│       ├── logging_utils.py             # Operational metrics logging
│       └── retry_utils.py               # Exponential backoff implementation
└── tests/
    ├── test_embedding_service.py        # Service layer unit tests
    ├── test_embedding_routes.py         # API integration tests
    └── test_embedding_storage.py        # Storage layer tests

frontend/
├── src/
│   ├── views/
│   │   └── DocumentEmbedding.vue        # Unified embedding interface at /documents/embed
│   ├── components/
│   │   └── embedding/
│   │       ├── DocumentSelector.vue     # Document dropdown with chunking status filter
│   │       ├── ModelSelector.vue        # Model selection with detailed info
│   │       └── EmbeddingResults.vue     # Results display panel
│   ├── stores/
│   │   └── embedding.js                 # Pinia state: selected document/model, results
│   ├── services/
│   │   └── embeddingService.js          # API client for embedding endpoints
│   └── router/
│       └── index.js                     # Route configuration (single /documents/embed entry)
└── tests/
    └── components/
        └── embedding/
            └── DocumentEmbedding.spec.js
```

**Structure Decision**: Selected **Web application** structure due to presence of both backend (FastAPI) and frontend (Vue 3) directories. Backend follows service-oriented architecture with clear separation of concerns (api/models/services/storage/utils). Frontend follows component-driven architecture with centralized state management via Pinia.

## Complexity Tracking

**No constitution violations detected.** All design decisions align with established principles:
- Modular architecture maintained
- Multi-provider support via model registry
- JSON persistence with source traceability
- Vue3 + TDesign frontend stack
- FastAPI backend with service layer pattern

No additional complexity justification required.

---

## Phase 0: Research (✅ COMPLETED)

**Status**: All unknowns resolved

**Generated Artifacts**:
- `research.md` - Technical research and design decisions

**Key Decisions Made**:
1. **Document Filtering**: Backend API filter parameter `?has_chunking_result=true`
2. **Model Display**: Two-stage progressive disclosure (compact dropdown + detail panel)
3. **Result Selection**: Latest active result with optional strategy filter
4. **Retry Strategy**: Validated existing implementation (3 retries, exponential backoff, jitter)
5. **Storage Format**: JSON with source traceability section
6. **State Management**: Normalized Pinia store with computed getters

---

## Phase 1: Design & Contracts (✅ COMPLETED)

**Status**: Data model and API contracts generated

**Generated Artifacts**:
- `data-model.md` - Complete entity definitions, relationships, validation rules
- `contracts/api-contract.yaml` - OpenAPI 3.0 specification with all endpoints
- `quickstart.md` - Developer quickstart guide with examples
- `CODEBUDDY.md` - Updated agent context file

**Key Deliverables**:
1. **8 Core Entities**: EmbeddingModel, EmbeddingRequest (4 variants), Vector, EmbeddingFailure, EmbeddingResult (2 variants), EmbeddingMetadata, BatchMetadata, EmbeddingConfig
2. **6 API Endpoints**: 
   - POST `/embedding/single` (backend-only)
   - POST `/embedding/batch` (backend-only)
   - POST `/embedding/from-chunking-result` (primary frontend)
   - POST `/embedding/from-document` (primary frontend)
   - GET `/embedding/models`
   - GET `/embedding/health`
3. **Data Integrity**: 14 validation rules, 4 invariants, 4 relationship rules, 5 state transition rules
4. **Integration Points**: Connects to existing Document, ChunkingResult, ChunkingTask, Chunk entities

**Constitution Re-Check**: ✅ All principles maintained

---

## Phase 2: Task Breakdown (⏸️ NOT STARTED)

**Note**: Phase 2 (task generation) is handled by the `/speckit.tasks` command, not `/speckit.plan`.

**Next Steps for Implementation Team**:
1. Run `/speckit.tasks` to generate detailed task breakdown from plan
2. Review generated `tasks.md` for sprint planning
3. Assign tasks to developers
4. Begin implementation following task sequence

---

## Summary

**Plan Generation Complete**: ✅

| Phase | Status | Artifacts |
|-------|--------|-----------|
| **Phase 0: Research** | ✅ Complete | research.md |
| **Phase 1: Design** | ✅ Complete | data-model.md, contracts/api-contract.yaml, quickstart.md |
| **Phase 2: Tasks** | ⏸️ Pending | Run `/speckit.tasks` command |

**Branch**: `003-vector-embedding`  
**Plan Path**: `/Users/qingli/Desktop/AI/RAG/rag-framework-spec/specs/003-vector-embedding/plan.md`

**Constitution Compliance**: ✅ All principles validated

**Ready for Implementation**: ✅ Yes (pending task breakdown generation)
