# RAG Pipeline Hub

[中文说明](README_CN.md)

An end-to-end RAG framework for real-world workflows, covering document ingestion, chunking, embedding, index management, hybrid retrieval, and answer generation. The repository includes a FastAPI backend, a Vue 3 frontend, and a module-oriented documentation system under `documents/` and `specs/`.

![Homepage](docs/images/homepage.png)

## Highlights

- Supports 20+ document formats including `PDF / DOCX / DOC / XLSX / XLS / PPTX / PPT / HTML / CSV / TXT / Markdown / JSON / XML / RST / LOG`
- `Docling Serve` as the primary high-quality parser with fallback loaders for resilience
- Multiple chunking strategies including character-based, paragraph, semantic, heading-based, hybrid, and parent-child chunking; built-in **smart recommendation engine** that analyzes document features (heading structure, code ratio, format, length, etc.) to automatically suggest the best strategy and parameters with confidence scores and reasoning
- Supports `bge-m3`, `qwen3-embedding-8b`, `qwen3-vl-embedding-8b` (multimodal) embedding models; built-in **model recommendation** that uses layered decision-making based on document language, domain, and multimodal features to suggest the most suitable model, with support for batch recommendation and outlier document detection
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
  -> Chunk documents (character/paragraph/semantic/heading/hybrid/parent-child + smart recommendation)
  -> Generate embeddings (smart model recommendation + cache + progress)
  -> Manage vector indexes / collections
  -> Run hybrid retrieval
  -> Generate answers (SSE / sources / history)
```

## Modules

| Module | Current capabilities |
|--------|----------------------|
| Document Loading | Upload, parsing, async tasks, loader recommendation, result querying |
| Document Chunking | Multiple chunking strategies, **smart strategy & parameter recommendation** (based on document feature analysis), previews, parent-child chunk metadata |
| Vector Embedding | Document embedding, **smart model recommendation** (layered decision-making on language/domain/multimodal features), batch processing, caching, progress streaming, history |
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
git clone https://github.com/qingni/rag-pipeline-hub.git
cd rag-pipeline-hub
```

### 2. Configure environment variables

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Start by configuring the variables below. In most cases, you can keep the other values from `.env.example` unchanged and tune them later if needed.

**Backend `backend/.env`**

| Key | Required | Description | Recommended local value |
|-----|----------|-------------|-------------------------|
| `DATABASE_URL` | No | Application database connection string; SQLite works out of the box for local development | `sqlite:///./app.db` |
| `MILVUS_HOST` | Yes | Milvus service host | `localhost` |
| `MILVUS_PORT` | Yes | Milvus service port | `19530` |
| `EMBEDDING_API_KEY` | Yes | API key for the embedding service | Your actual API key |
| `EMBEDDING_API_BASE_URL` | Yes | Base URL of your embedding service | Your OpenAI-compatible embedding endpoint |
| `EMBEDDING_DEFAULT_MODEL` | Recommended | Default embedding model | `qwen3-embedding-8b` |
| `RERANKER_API_KEY` | Optional | Required only if you enable reranker-based re-ranking | Leave empty if unused |
| `RERANKER_API_BASE_URL` | Optional | Base URL of the reranker service | Leave empty if unused |
| `RERANKER_MODEL` | Optional | Reranker model name | `qwen3-reranker-4b` |
| `DOCLING_SERVE_ENABLED` | Optional | Whether to enable high-quality Docling Serve parsing | Set to `false` if Docling is not used locally |
| `DOCLING_SERVE_URL` | Optional | Docling Serve endpoint | `http://localhost:5001` |
| `DOCLING_SERVE_API_KEY` | Optional | Docling Serve auth key | Leave empty if auth is disabled |
| `FRONTEND_ALLOWED_ORIGINS` | Recommended | Allowed frontend origins for backend CORS | `http://localhost:5173,http://localhost:4173` |

**Frontend `frontend/.env`**

| Key | Required | Description | Recommended local value |
|-----|----------|-------------|-------------------------|
| `VITE_API_BASE_URL` | Yes | Base URL used by the frontend to call backend APIs | `http://localhost:8000/api/v1` |
| `VITE_UPLOAD_MAX_SIZE` | No | Frontend upload size limit in bytes | `52428800` |
| `VITE_ENABLE_OLLAMA` | No | Frontend feature flag | Keep the default |
| `VITE_ENABLE_HUGGINGFACE` | No | Frontend feature flag | Keep the default |

If you only want to **get the project running locally for the first time**, make sure at least these 5 values are set correctly:

- `MILVUS_HOST`
- `MILVUS_PORT`
- `EMBEDDING_API_KEY`
- `EMBEDDING_API_BASE_URL`
- `VITE_API_BASE_URL`

If you want better parsing and retrieval quality, you can additionally configure:

- `RERANKER_API_KEY` / `RERANKER_API_BASE_URL`
- `DOCLING_SERVE_ENABLED` / `DOCLING_SERVE_URL`

### 3. Start Milvus

If you use Colima, the recommended way is to run the built-in helper script first:

```bash
./scripts/start_colima.sh
```

This script checks and starts Colima automatically, and is intended for local macOS development.

If you already manage Colima yourself, you can also run:

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
| Embedding | `POST /api/v1/embedding/from-document` |
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
rag-pipeline-hub/
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
