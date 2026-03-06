# Quick Start: 文档分块功能开发指南

**Feature**: 002-doc-chunking  
**Date**: 2025-12-05  
**Target Audience**: Developers implementing this feature

## 📋 Prerequisites

### Required Knowledge
- Python 3.11+ and FastAPI basics
- Vue 3 Composition API and TypeScript
- SQLAlchemy ORM
- RESTful API design
- Async/await patterns in Python

### Required Tools
- Python 3.11+ with pip
- Node.js 18+ with npm
- Git
- IDE (VSCode recommended)
- API testing tool (Postman/curl)

### Required Dependencies (Already Installed)
```bash
# Backend
langchain-text-splitters==0.3.4  # Core chunking library
fastapi==0.104.1
sqlalchemy==2.0.23

# Frontend
vue@3.3.8
tdesign-vue-next@1.13.1
axios@1.6.2
```

---

## 🚀 Quick Setup (5 minutes)

### 1. Create Feature Branch
```bash
cd /path/to/rag-pipeline-hub
git checkout 002-doc-chunking  # Already created
```

### 2. Backend Setup
```bash
cd backend

# Chunking directories already exist in backend/results/
# Verify structure:
ls -la results/chunking
ls -la results/load
ls -la results/parse

# Create chunkers directory if not exists
mkdir -p src/providers/chunkers

# Verify dependencies
pip list | grep langchain-text-splitters
# Should show: langchain-text-splitters  0.3.4
```

### 3. Frontend Setup
```bash
cd frontend

# Verify Vue and TDesign installed
npm list vue tdesign-vue-next
# Should show both packages
```

### 4. Database Migration
```bash
cd backend

# Create migration for new tables
alembic revision -m "Add chunking tables"

# Edit migration file (auto-generated path shown by alembic)
# Copy schema from specs/002-doc-chunking/data-model.md

# Run migration
alembic upgrade head
```

---

## 📂 Project Structure

```
backend/src/
├── models/
│   ├── chunking_task.py          # ✨ NEW
│   ├── chunking_strategy.py      # ✨ NEW
│   ├── chunking_result.py        # ✨ NEW
│   └── document_chunk.py         # 📝 UPDATE
├── services/
│   └── chunking_service.py       # ✨ NEW (start here)
├── providers/chunkers/
│   ├── __init__.py               # ✨ NEW
│   ├── base_chunker.py           # ✨ NEW
│   ├── character_chunker.py      # ✨ NEW
│   ├── paragraph_chunker.py      # ✨ NEW
│   ├── heading_chunker.py        # ✨ NEW
│   └── semantic_chunker.py       # ✨ NEW
├── api/
│   └── chunking.py               # ✨ NEW
└── utils/
    ├── chunking_validators.py    # ✨ NEW
    └── chunking_helpers.py       # ✨ NEW

frontend/src/
├── views/
│   └── ChunkingView.vue          # ✨ NEW (main page)
├── components/chunking/
│   ├── DocumentSelector.vue      # ✨ NEW
│   ├── StrategySelector.vue      # ✨ NEW
│   ├── ParameterConfig.vue       # ✨ NEW
│   ├── ChunkList.vue             # ✨ NEW
│   └── HistoryList.vue           # ✨ NEW
├── services/
│   └── chunkingService.js        # ✨ NEW
└── stores/
    └── chunkingStore.js          # ✨ NEW
```

---

## 🏗️ Implementation Order (Recommended)

### Phase 1: Backend Core (Days 1-3)

#### Day 1: Data Models & Basic Service
```bash
# 1. Create data models (copy from data-model.md)
touch src/models/chunking_task.py
touch src/models/chunking_strategy.py
touch src/models/chunking_result.py

# 2. Create service skeleton
touch src/services/chunking_service.py
```

**Start with**: `chunking_service.py`
- Create `ChunkingService` class
- Implement `load_source_document()` method
- Test with existing JSON file from backend/results/load

#### Day 2: Chunking Strategies
```bash
# Create strategy files
mkdir -p src/providers/chunkers
touch src/providers/chunkers/{base,character,paragraph,heading,semantic}_chunker.py
```

**Implementation order**:
1. `base_chunker.py` - Abstract base class
2. `character_chunker.py` - Simplest, use LangChain's RecursiveCharacterTextSplitter
3. `paragraph_chunker.py` - Custom logic based on \n\n
4. `heading_chunker.py` - Regex-based heading detection
5. `semantic_chunker.py` - TF-IDF + cosine similarity

**Test each strategy**:
```python
# Quick test in Python shell
from src.providers.chunkers.character_chunker import CharacterChunker

chunker = CharacterChunker(chunk_size=1000, chunk_overlap=100)
text = "Your test text here..."
chunks = chunker.chunk(text)
print(f"Generated {len(chunks)} chunks")
```

#### Day 3: Queue Manager & API
```bash
touch src/api/chunking.py
```

1. Implement `ChunkingQueueManager` in service
2. Create API endpoints (refer to contracts/chunking-api.yaml)
3. Test with curl/Postman

**Quick API Test**:
```bash
# Start backend
cd backend
python -m src.main

# Test endpoint
curl -X POST http://localhost:8000/api/chunking/chunk \
  -H "Content-Type: application/json" \
  -d '{
    "source_file_path": "results/load/test_doc.json",
    "chunking_strategy": "character",
    "chunking_params": {"chunk_size": 1000, "chunk_overlap": 100}
  }'
```

**Note**: The `source_file_path` is now relative to the `backend/` directory since `results/` has been moved under `backend/`.

---

### Phase 2: Frontend UI (Days 4-6)

#### Day 4: Core Components
```bash
mkdir -p src/components/chunking
cd src/components/chunking
```

**Create components** (in order):
1. `DocumentSelector.vue` - Dropdown to select parsed documents
2. `StrategySelector.vue` - Radio buttons for 4 strategies
3. `ParameterConfig.vue` - Input fields for chunk_size, overlap

**Quick component test**:
```bash
npm run dev
# Navigate to http://localhost:5173/chunking (after adding route)
```

#### Day 5: Results Display
Create:
1. `ChunkList.vue` - Table/list showing all chunks
2. `ChunkDetail.vue` - Modal/panel for chunk details
3. `ChunkingProgress.vue` - Progress bar with polling

**TDesign Components to Use**:
- `t-select` for document selector
- `t-radio-group` for strategy
- `t-input-number` for parameters
- `t-table` for chunk list
- `t-dialog` for chunk details
- `t-progress` for progress bar

#### Day 6: History & Management
Create:
1. `HistoryList.vue` - Paginated table with filters
2. `CompareResults.vue` - Side-by-side comparison
3. `ExportDialog.vue` - Export format selection

---

### Phase 3: Integration & Testing (Days 7-8)

#### Day 7: End-to-End Testing
1. Test complete flow: Select doc → Choose strategy → Configure → Chunk → View results
2. Test all 4 strategies with different documents
3. Test error cases (invalid params, missing file, etc.)
4. Test queue behavior (submit 4 tasks, verify 3 running + 1 queued)

#### Day 8: Performance & Polish
1. Test with large documents (50k characters)
2. Verify timing meets success criteria (SC-002, SC-004)
3. Test pagination with 500+ records (SC-009)
4. Fix any UI bugs
5. Add loading states and error messages

---

## 🧪 Testing Strategy

### Unit Tests
```bash
cd backend
pytest tests/unit/test_character_chunker.py -v
pytest tests/unit/test_paragraph_chunker.py -v
pytest tests/unit/test_chunking_service.py -v
```

### Integration Tests
```bash
pytest tests/integration/test_chunking_api.py -v
```

### Manual Testing Checklist
- [ ] Character chunking with 1000 size, 100 overlap
- [ ] Paragraph chunking with 800 max size
- [ ] Heading chunking with structured document
- [ ] Heading chunking with no headings (should show error)
- [ ] Semantic chunking (should fallback if needed)
- [ ] Submit 4 concurrent tasks (verify queue)
- [ ] View history with filters
- [ ] Compare two results
- [ ] Export as JSON
- [ ] Export as CSV
- [ ] Delete result (verify JSON file removed)

---

## 🔍 Debugging Tips

### Backend Debugging
```python
# Add logging in service
import logging
logger = logging.getLogger(__name__)

# In ChunkingService
logger.info(f"Processing document: {document_name}")
logger.debug(f"Chunk params: {chunking_params}")
```

### Frontend Debugging
```javascript
// In chunkingStore.js
console.log('Submitting chunking request:', payload)
console.log('API response:', response.data)

// Vue DevTools
// Install Vue DevTools extension for browser
// Inspect component state and store
```

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'langchain_text_splitters'`
```bash
# Solution
cd backend
pip install langchain-text-splitters==0.3.4
```

**Issue**: Frontend can't connect to backend
```bash
# Check CORS settings in backend/src/main.py
# Should include:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Issue**: Database table not found
```bash
# Run migration
cd backend
alembic upgrade head

# If migration doesn't exist, create it
alembic revision -m "Add chunking tables"
```

---

## 📚 Key Files to Reference

### Specifications
- [spec.md](./spec.md) - Feature requirements
- [data-model.md](./data-model.md) - Database schema
- [research.md](./research.md) - Technical decisions
- [contracts/chunking-api.yaml](./contracts/chunking-api.yaml) - API contract

### Existing Code to Study
- `backend/src/services/loading_service.py` - Similar service pattern
- `backend/src/api/loading.py` - API endpoint pattern
- `frontend/src/views/LoadingView.vue` - UI layout pattern
- `frontend/src/components/loading/` - Component patterns

---

## ⚡ Quick Commands Reference

```bash
# Backend
cd backend
python -m src.main                    # Start server
pytest tests/ -v                      # Run all tests
pytest tests/unit/ -k chunking -v     # Run chunking tests only
alembic upgrade head                  # Run migrations

# Frontend
cd frontend
npm run dev                           # Start dev server
npm run build                         # Build for production

# Database
sqlite3 backend/app.db                # Open database
.schema chunking_tasks                # View table schema
SELECT * FROM chunking_results;       # Query results

# Git
git status                            # Check changes
git add .                             # Stage all
git commit -m "feat: implement chunking feature"
git push origin 002-doc-chunking      # Push to branch
```

---

## 🎯 Success Criteria Checklist

Before marking as complete, verify:

- [ ] **SC-001**: User completes flow in < 30 seconds
- [ ] **SC-002**: 10k char document chunks in < 5 seconds
- [ ] **SC-003**: 95%+ chunking accuracy (manual spot check)
- [ ] **SC-004**: 50k char document chunks in < 30 seconds
- [ ] **SC-005**: 90%+ user comprehension (internal test)
- [ ] **SC-006**: 100% JSON data integrity (validate with schema)
- [ ] **SC-007**: 100% parameter validation accuracy
- [ ] **SC-008**: Management ops respond in < 2 seconds
- [ ] **SC-009**: 500 record pagination responds in < 1 second

---

## 🤝 Getting Help

- **Spec Questions**: Refer to [spec.md](./spec.md) Clarifications section
- **API Questions**: Check [contracts/chunking-api.yaml](./contracts/chunking-api.yaml)
- **Data Questions**: See [data-model.md](./data-model.md)
- **Technical Questions**: Review [research.md](./research.md)

---

## 📝 Next Steps

After completing development:
1. Run `/speckit.tasks` to generate task breakdown
2. Create PR from `002-doc-chunking` to `main`
3. Update main README.md with chunking feature info
4. Document any deviations from spec

Happy coding! 🚀
