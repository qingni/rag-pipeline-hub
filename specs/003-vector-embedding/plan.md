# Implementation Plan: Vector Embedding Module

**Branch**: `003-vector-embedding` | **Date**: 2025-12-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-vector-embedding/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a vector embedding service that converts text into numerical vectors using multiple embedding models (BGE-M3, Qwen3-Embedding-8B, Hunyuan-Embedding, Jina-Embeddings-v4). The module provides single and batch text vectorization capabilities with robust error handling, automatic retries with exponential backoff, and comprehensive operational logging. Results are persisted in JSON format per the constitution's requirement for result persistence across the document processing pipeline.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI 0.104.1, LangChain 0.3.15, LangChain-OpenAI 0.2.14, Pydantic 2.7.4  
**Storage**: JSON file persistence (per constitution requirement) + SQLite database for metadata tracking  
**Testing**: pytest 7.4.3, pytest-asyncio 0.21.1, httpx 0.25.2 for API testing  
**Target Platform**: Linux/macOS server, containerized deployment ready  
**Project Type**: Web (backend API + frontend UI)  
**Performance Goals**: <2s single query vectorization, <30s for 100-document batches, support 1000 docs/batch max  
**Constraints**: 95% first-attempt success rate, 80% retry recovery rate, 60s request timeout, exponential backoff for rate limiting  
**Scale/Scope**: Support 4 embedding models, handle concurrent requests, production-ready error handling and observability

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ I. 模块化架构
**Status**: PASS  
**Evidence**: Embedding module designed as independent service (`embedding_service.py`) with clear interface, supports plugin architecture for multiple model providers.

### ✅ II. 多提供商支持
**Status**: PASS  
**Evidence**: Supports 4 embedding models (BGE-M3, Qwen3-Embedding-8B, Hunyuan-Embedding, Jina-Embeddings-v4) through configurable model selection, extensible for future providers.

### ✅ III. 结果持久化 (NON-NEGOTIABLE)
**Status**: PASS  
**Evidence**: Module will persist vectorization results as JSON files with naming convention `{document_name}_{timestamp}.json` containing vectors and metadata.

### ✅ IV. 用户体验优先
**Status**: PASS  
**Evidence**: Frontend integration with Vue3 + TDesign follows existing UI patterns (left control panel + right content display), provides model selection, batch processing UI, and result visualization.

### ✅ V. API标准化
**Status**: PASS  
**Evidence**: RESTful API endpoints following FastAPI conventions, unified error handling, consistent response formats, clear API documentation.

**Gate Result**: ✅ **ALL CHECKS PASSED** - Proceed to Phase 0

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
# Web application structure (backend + frontend)

backend/
├── src/
│   ├── services/
│   │   └── embedding_service.py        # Core embedding service (already exists as reference)
│   ├── api/
│   │   └── embedding_routes.py         # NEW: API endpoints for embedding operations
│   ├── models/
│   │   └── embedding_models.py         # NEW: Pydantic models for requests/responses
│   ├── storage/
│   │   └── embedding_storage.py        # NEW: JSON persistence layer
│   └── utils/
│       ├── retry_utils.py              # NEW: Exponential backoff retry logic
│       └── logging_utils.py            # NEW: Operational metrics logging
├── tests/
│   ├── unit/
│   │   ├── test_embedding_service.py   # NEW: Service unit tests
│   │   └── test_retry_logic.py         # NEW: Retry mechanism tests
│   └── integration/
│       └── test_embedding_api.py       # NEW: API integration tests
└── results/
    └── embedding/                       # NEW: JSON results directory

frontend/
├── src/
│   ├── views/
│   │   └── EmbeddingView.vue           # NEW: Main embedding page
│   ├── components/
│   │   ├── EmbeddingPanel.vue          # NEW: Control panel (model selection, batch upload)
│   │   └── EmbeddingResults.vue        # NEW: Results display and visualization
│   └── services/
│       └── embeddingService.js         # NEW: API client for embedding endpoints
```

**Structure Decision**: Following existing web application structure with backend service layer pattern and frontend Vue3 component architecture. The embedding_service.py reference implementation will be enhanced with API layer, storage persistence, and frontend UI integration per constitution requirements.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**Status**: ✅ No violations - All constitution principles satisfied

**Post-Phase 1 Re-evaluation**:
- ✅ Modular architecture maintained (independent service with clear API)
- ✅ Multi-provider support implemented (4 embedding models, extensible)
- ✅ JSON result persistence designed (per-request files with metadata)
- ✅ User experience prioritized (Vue3 + TDesign UI integration)
- ✅ API standardization followed (RESTful FastAPI endpoints, OpenAPI spec)

No complexity violations identified. No justifications required.

---

## Phase 0: Research Findings

**Status**: ✅ COMPLETE  
**Output**: [research.md](./research.md)

**Key Decisions**:
1. Exponential backoff with jitter (1s-32s, 3 retries)
2. Partial success pattern for batch failures
3. Structured JSON logging (no text content)
4. Strict dimension validation (fail fast)
5. 1000 document batch limit
6. LangChain OpenAIEmbeddings wrapper with custom retry

All technical unknowns resolved. See research.md for detailed rationale.

---

## Phase 1: Design & Contracts

**Status**: ✅ COMPLETE

**Outputs**:
- [data-model.md](./data-model.md) - 7 core entities with validation rules
- [contracts/openapi.yaml](./contracts/openapi.yaml) - Complete API specification
- [quickstart.md](./quickstart.md) - Developer onboarding guide
- Agent context updated (CODEBUDDY.md)

**API Endpoints Designed**:
- `POST /api/v1/embedding/single` - Single text vectorization
- `POST /api/v1/embedding/batch` - Batch processing (max 1000)
- `GET /api/v1/models` - List available models
- `GET /api/v1/models/{model_name}` - Get model details
- `GET /api/v1/health` - Health check

**Data Entities**:
1. EmbeddingModel - Model configuration
2. EmbeddingRequest - Vectorization request
3. Vector - Numerical representation
4. EmbeddingResponse - Result wrapper
5. EmbeddingFailure - Error details
6. EmbeddingMetadata - Processing statistics
7. EmbeddingConfig - Configuration snapshot

---

## Phase 2: Task Breakdown

**Status**: ⏸️ DEFERRED - Use `/speckit.tasks` command

Phase 2 (task generation) is handled by a separate command. The planning phase ends here with all design artifacts completed.

**Next Steps**:
1. Run `/speckit.tasks` to break down implementation into concrete tasks
2. Tasks will reference data-model.md and openapi.yaml for implementation details
3. Each task will include acceptance criteria from spec.md

---

## Notes

**Design Philosophy**:
- **Fail fast**: Invalid inputs rejected immediately
- **Fail safe**: Transient errors handled with retries
- **Fail visible**: All failures logged with context
- **Partial success**: Maximize throughput, minimize waste

**Constitution Alignment**:
- Modular: Independent service with clear interface
- Multi-provider: 4 models, extensible design
- Persistent: JSON results per request
- UX-focused: Vue3 + TDesign integration
- Standardized API: RESTful FastAPI with OpenAPI spec

**Ready for Implementation**: All design artifacts complete, proceed to `/speckit.tasks`.

