# rag-framework-spec Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-17

## Active Technologies
- Python 3.11 (后端) + Vue 3 + Vite (前端) + FastAPI 0.104.1, pymilvus 2.3.4, faiss-cpu 1.7.4, TDesign Vue Next, Pinia (004-vector-index)
- PostgreSQL 14+ (元数据) + Milvus/FAISS (向量数据) + JSON (结果持久化) (004-vector-index)
- SQLite/PostgreSQL (搜索历史) + Milvus/FAISS (向量检索) (005-search-query)
- Python 3.11 (后端) + Vue 3 + Vite (前端) + FastAPI 0.104.1, langchain-openai, TDesign Vue Next, Pinia (006-text-generation)
- SQLite/PostgreSQL (生成历史) (006-text-generation)
- Python 3.11 (后端) + JavaScript ES2020+ (前端) + FastAPI 0.104.1, Docling, PyMuPDF, python-docx, openpyxl, python-pptx, pandas, BeautifulSoup4, ebooklib, Vue 3, Vite, TDesign Vue Nex (001-document-processing-opt)
- SQLite/PostgreSQL (元数据) + JSON (结果持久化) (001-document-processing-opt)
- Python 3.11 (后端) + JavaScript ES2020+ (前端) + FastAPI 0.104.1, LangChain (SemanticChunker), sentence-transformers, Vue 3, Vite, TDesign Vue Next, Pinia (002-doc-chunking-opt)
- Python 3.11 (Backend), TypeScript/JavaScript (Frontend with Vue 3) (004-vector-index-opt)
- Milvus 2.x (向量数据库), SQLite/PostgreSQL (元数据) (004-vector-index-opt)

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
- 004-vector-index-opt: Added Python 3.11 (Backend), TypeScript/JavaScript (Frontend with Vue 3)
- 002-doc-chunking-opt: Added Python 3.11 (后端) + JavaScript ES2020+ (前端) + FastAPI 0.104.1, LangChain (SemanticChunker), sentence-transformers, Vue 3, Vite, TDesign Vue Next, Pinia
- 001-document-processing-opt: Added Python 3.11 (后端) + JavaScript ES2020+ (前端) + FastAPI 0.104.1, Docling, PyMuPDF, python-docx, openpyxl, python-pptx, pandas, BeautifulSoup4, ebooklib, Vue 3, Vite, TDesign Vue Nex


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
