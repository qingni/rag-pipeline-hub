# RAG Framework

[中文版 README](README.md)

An end-to-end RAG framework for real-world workflows, covering document ingestion, chunking, embedding, index management, hybrid retrieval, and answer generation. The repository includes a FastAPI backend, a Vue 3 frontend, and a module-oriented documentation system under `documents/` and `specs/`.

## Highlights

- Multi-format document ingestion for `PDF / DOCX / XLSX / PPTX / HTML / CSV / TXT / Markdown / JSON / XML`
- `Docling Serve` as the primary high-quality parser with fallback loaders for resilience
- Multiple chunking strategies including fixed-size, recursive, semantic, and heading-based chunking
- Embedding workflows with batch processing, progress streaming, caching, and result management
- Vector index and Collection management with search, persistence, recovery, and recommendation APIs
- Hybrid retrieval with dense recall, sparse recall, `RRF` ranking, `Reranker`, and query enhancement
- Text generation with sync and streaming responses, source citations, history management, retry, and safe Markdown rendering

## Tech Stack

**Backend**
- Python 3.11
- FastAPI
- SQLAlchemy
- SQLite
- LangChain
- OpenAI-compatible LLM and embedding APIs
- Milvus

**Frontend**
- Vue 3
- Vite
- Pinia
- Vue Router
- TDesign
- Tailwind CSS
- markdown-it + DOMPurify

## Pipeline Overview

```text
Upload documents
  -> Parse documents (Docling Serve + fallback)
  -> Chunk documents
  -> Generate embeddings (cache + progress)
  -> Manage vector indexes / collections
  -> Run hybrid retrieval
  -> Generate answers (SSE / sources / history)
```

## Modules

| Module | Current capabilities |
|--------|----------------------|
| Document Loading | Upload, parsing, async tasks, loader recommendation, result querying |
| Document Chunking | Multiple chunking strategies, parameter recommendation, previews, parent-child chunk metadata |
| Vector Embedding | Document embedding, batch processing, caching, progress streaming, history, model recommendation |
| Vector Index | Index and Collection management, vector CRUD, statistics, persistence, recovery, recommendation |
| Search | Standard search, hybrid search, Collection listing, Reranker health check, history management |
| Generation | Non-streaming generation, SSE streaming, cancellation, source citation, history, clear-all history |

## Quick Start

### Requirements

- Python 3.11+
- Node.js 18+
- Docker or Colima for Milvus
- Access to an OpenAI-compatible LLM / embedding service

### 1. Clone the repository

```bash
git clone https://github.com/qingni/rag-framework-spec.git
cd rag-framework-spec
```

### 2. Configure environment variables

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Then update `backend/.env` with your model, database, Milvus, Docling, and API key settings.

### 3. Start Milvus

If you use Colima:

```bash
colima start
```

Then start Milvus:

```bash
./scripts/start_milvus.sh
```

### 4. Optionally start Docling Serve

If you want the high-quality document parsing path enabled:

```bash
./scripts/start_docling.sh
```

### 5. Start the backend

```bash
./scripts/start_backend.sh
```

Default backend endpoints:
- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`

### 6. Start the frontend

```bash
./scripts/start_frontend.sh
```

Default frontend URL:
- Web UI: `http://localhost:5173`

## API Overview

The current API surface mainly uses two prefixes:

- General business APIs: `/api/v1/*`
- Vector index APIs: `/api/vector-index/*`

Common endpoints:

| Module | Endpoint |
|--------|----------|
| Health | `GET /api/v1/health` |
| Document loading | `POST /api/v1/processing/load` |
| Chunking | `POST /api/v1/chunking/chunk` |
| Embedding | `POST /api/v1/embedding/embed_document` |
| Search | `POST /api/v1/search/hybrid` |
| Generation | `POST /api/v1/generation/generate` |
| Streaming generation | `POST /api/v1/generation/stream` |
| Vector index creation | `POST /api/vector-index/indexes` |

For the full API reference, check `http://localhost:8000/docs` or the module documents under `documents/`.

## Frontend Routes

The current frontend includes these main pages:

- `/documents/load`
- `/documents/chunk`
- `/documents/embed`
- `/index`
- `/search`
- `/generation`

## Repository Structure

```text
rag-framework-spec/
├── backend/                 # FastAPI backend
│   ├── src/
│   │   ├── api/             # Route layer
│   │   ├── services/        # Core business logic
│   │   ├── providers/       # Integrations for LLMs, Docling, etc.
│   │   ├── models/          # ORM models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── config/          # Settings and configuration
│   ├── results/             # Generated result files
│   └── tests/               # Backend tests
├── frontend/                # Vue 3 frontend
│   ├── src/
│   │   ├── views/           # Page views
│   │   ├── components/      # UI and feature components
│   │   ├── stores/          # Pinia stores
│   │   └── services/        # API clients
│   └── package.json
├── documents/               # Implementation-oriented module docs
├── specs/                   # Specifications and evolution notes
├── scripts/                 # Start/stop scripts
├── docker/                  # Deployment files such as Milvus
├── migrations/              # Database migrations
└── uploads/                 # Uploaded files
```

## Documentation

- [Document Loading](documents/load/README.md)
- [Document Chunking](documents/chunk/README.md)
- [Vector Embedding](documents/embedding/README.md)
- [Vector Index](documents/vector-index/README.md)
- [Search Overview](documents/search-query/01-%E6%A3%80%E7%B4%A2%E6%9F%A5%E8%AF%A2%E5%8A%9F%E8%83%BD%E6%A6%82%E8%BF%B0.md)
- [Text Generation](documents/generation/README.md)

If you want the formal feature specs and implementation planning materials, check the `specs/` directory.

## Development

Run backend tests:

```bash
cd backend
pytest
```

Build the frontend:

```bash
cd frontend
npm run build
```

Stop local services:

```bash
./scripts/stop_backend.sh
./scripts/stop_frontend.sh
./scripts/stop_milvus.sh
./scripts/stop_docling.sh
```

## License

[Apache License 2.0](LICENSE)
