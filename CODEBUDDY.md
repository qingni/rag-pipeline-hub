# rag-framework-spec Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-17

## Active Technologies
- Python 3.11 (后端) + Vue 3 + Vite (前端) + FastAPI 0.104.1, pymilvus 2.3.4, faiss-cpu 1.7.4, TDesign Vue Next, Pinia (004-vector-index)
- PostgreSQL 14+ (元数据) + Milvus/FAISS (向量数据) + JSON (结果持久化) (004-vector-index)
- SQLite/PostgreSQL (搜索历史) + Milvus/FAISS (向量检索) (005-search-query)
- Python 3.11 (后端) + Vue 3 + Vite (前端) + FastAPI 0.104.1, langchain-openai, TDesign Vue Next, Pinia (006-text-generation)
- SQLite/PostgreSQL (生成历史) (006-text-generation)

- Python 3.11+ (backend), JavaScript/ES2020+ (frontend) (003-vector-embedding)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+ (backend), JavaScript/ES2020+ (frontend): Follow standard conventions

## Recent Changes
- 006-text-generation: Added Python 3.11 (后端) + Vue 3 + Vite (前端) + FastAPI 0.104.1, langchain-openai, TDesign Vue Next, Pinia
- 005-search-query: Added Python 3.11 (后端) + Vue 3 + Vite (前端) + FastAPI 0.104.1, pymilvus 2.3.4, faiss-cpu 1.7.4, TDesign Vue Next, Pinia
- 004-vector-index: Added Python 3.11 (后端) + Vue 3 + Vite (前端) + FastAPI 0.104.1, pymilvus 2.3.4, faiss-cpu 1.7.4, TDesign Vue Next, Pinia


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
