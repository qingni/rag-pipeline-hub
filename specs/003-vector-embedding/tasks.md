# Implementation Tasks: Vector Embedding Module

**Feature**: 003-vector-embedding  
**Branch**: `003-vector-embedding`  
**Generated**: 2025-12-16  
**Status**: Ready for Implementation  

---

## 📋 Task Organization

### 任务分组逻辑
- **Phase 0**: 环境准备与依赖安装
- **Phase 1**: 数据库存储层实现
- **Phase 2**: 核心向量化服务增强
- **Phase 3**: API路由层实现
- **Phase 4**: 前端统一界面开发
- **Phase 5**: 测试与验证
- **Phase 6**: 文档与交付

### 估时方法
- **Simple**: 0.5-1天 (基础CRUD、配置修改)
- **Medium**: 1-2天 (复杂业务逻辑、API设计)
- **Complex**: 2-3天 (双写事务、前端完整页面、集成测试)

### 优先级定义
- **P0**: 阻塞性任务,必须最先完成
- **P1**: 核心功能,主流程必需
- **P2**: 重要功能,用户体验相关
- **P3**: 增强功能,可后续迭代

---

## Phase 0: 环境准备 (0.5天)

### Task 0.1: 依赖安装与配置验证
**Priority**: P0  
**Estimate**: 0.5天  
**Type**: Setup  
**Assignee**: Backend Developer  

**Description**:
确保开发环境已安装所有必需依赖,验证API连接可用性。

**Acceptance Criteria**:
- [ ] Python依赖已安装: `httpx`, `tenacity`, `sqlalchemy`
- [ ] 前端依赖已验证: Vue 3, TDesign Vue Next, Pinia
- [ ] 环境变量已配置: `EMBEDDING_API_BASE_URL`, `EMBEDDING_API_KEY`
- [ ] 连接测试通过: 能成功调用配置的 API endpoint 的 `/v1/models` 接口

**Implementation Steps**:
1. 更新 `backend/requirements.txt`:
   ```txt
   httpx>=0.25.0
   tenacity>=8.2.0
   sqlalchemy>=2.0.0
   ```
2. 创建环境配置文件 `backend/.env.example`:
   ```bash
   # 注意：请勿在代码中硬编码内部 API 地址
   EMBEDDING_API_BASE_URL=https://your-embedding-api-endpoint.com
   EMBEDDING_API_KEY=your-api-key-here
   EMBEDDING_RESULTS_DIR=./results/embedding
   ```
3. 运行依赖安装: `pip install -r backend/requirements.txt`
4. 编写连接测试脚本 `backend/scripts/test_embedding_api.py`

**Files**:
- `backend/requirements.txt` (modify)
- `backend/.env.example` (create)
- `backend/scripts/test_embedding_api.py` (create)

**Dependencies**: None

---

## Phase 1: 数据库存储层 (2天)

### Task 1.1: 创建EmbeddingResult数据模型
**Priority**: P0  
**Estimate**: 0.5天  
**Type**: Backend - Database  
**Assignee**: Backend Developer  
**Status**: ✅ COMPLETED

**Description**:
实现 `embedding_results` 表的SQLAlchemy ORM模型,包含所有字段约束和索引定义。

**Acceptance Criteria**:
- [X] ORM模型包含12个字段(result_id, document_id, model, status等)
- [X] 实现CHECK约束: status枚举, model枚举
- [X] 定义3个索引: `idx_embedding_doc_model`, `idx_embedding_created_at`, `idx_embedding_status`
- [X] 单元测试覆盖模型验证逻辑

**Implementation Steps**:
1. 创建 `backend/src/models/embedding_models.py`
2. 定义 `EmbeddingResult` SQLAlchemy模型:
   ```python
   class EmbeddingResult(Base):
       __tablename__ = 'embedding_results'
       
       result_id = Column(String, primary_key=True)
       document_id = Column(String, nullable=False)
       chunking_result_id = Column(String)
       model = Column(String, nullable=False)
       status = Column(String, nullable=False)
       # ... other 7 fields
       
       __table_args__ = (
           Index('idx_doc_model', 'document_id', 'model'),
           Index('idx_created_at', 'created_at'),
           Index('idx_status', 'status'),
           CheckConstraint("status IN ('SUCCESS', 'FAILED', 'PARTIAL_SUCCESS')"),
           CheckConstraint("model IN ('bge-m3', 'qwen3-embedding-8b', 'hunyuan-embedding', 'jina-embeddings-v4')")
       )
   ```
3. 创建数据库迁移脚本(如使用Alembic)
4. 编写单元测试 `backend/tests/unit/test_embedding_models.py`

**Files**:
- `backend/src/models/embedding_models.py` (create)
- `backend/tests/unit/test_embedding_models.py` (create)

**Dependencies**: Task 0.1

**Related Requirements**: FR-021, data-model.md Section 1

---

### Task 1.2: 实现数据库查询层
**Priority**: P1  
**Estimate**: 1天  
**Type**: Backend - Database  
**Assignee**: Backend Developer  
**Status**: ✅ COMPLETED

**Description**:
实现所有数据库查询操作,包括按ID查询、按文档查询、列表查询(带分页和过滤)。

**Acceptance Criteria**:
- [X] `get_by_result_id()` 方法实现
- [X] `get_latest_by_document()` 方法(支持model过滤)
- [X] `list_results()` 方法(支持分页、状态过滤、日期范围)
- [X] 查询性能满足要求: <100ms (10k记录)
- [X] 单元测试覆盖所有查询方法 (27/27 tests passed)

**Implementation Steps**:
1. 创建 `backend/src/storage/embedding_db.py`
2. 实现查询方法:
   ```python
   class EmbeddingResultDB:
       def get_by_result_id(self, result_id: str) -> Optional[EmbeddingResult]:
           return session.query(EmbeddingResult).filter_by(result_id=result_id).first()
       
       def get_latest_by_document(self, document_id: str, model: Optional[str] = None) -> Optional[EmbeddingResult]:
           query = session.query(EmbeddingResult).filter_by(document_id=document_id)
           if model:
               query = query.filter_by(model=model)
           return query.order_by(EmbeddingResult.created_at.desc()).first()
       
       def list_results(self, filters: dict, page: int, page_size: int) -> Tuple[List[EmbeddingResult], int]:
           # Implement pagination + filtering logic
           pass
   ```
3. 编写性能测试验证索引效果
4. 编写单元测试 `backend/tests/unit/test_embedding_db.py`

**Files**:
- `backend/src/storage/embedding_db.py` (create)
- `backend/tests/unit/test_embedding_db.py` (create)

**Dependencies**: Task 1.1

**Related Requirements**: FR-025, FR-026, FR-027, research.md Section 2

---

### Task 1.3: 实现双写存储服务
**Priority**: P0  
**Estimate**: 1.5天  
**Type**: Backend - Storage  
**Assignee**: Backend Developer  
**Status**: ✅ COMPLETED

**Description**:
实现JSON文件+数据库的原子双写操作,包含事务回滚逻辑和并发控制。

**Acceptance Criteria**:
- [X] `save_with_database()` 方法实现三步原子操作
- [X] JSON写入失败时,不创建数据库记录
- [X] 数据库写入失败时,自动删除JSON文件(回滚)
- [X] JSON文件按日期组织: `results/embedding/YYYY-MM-DD/`
- [X] 实现行级锁防止并发更新同一document+model记录(NFR-003)
- [X] 集成测试验证事务完整性和并发安全

**Implementation Steps**:
1. 创建 `backend/src/services/embedding_storage.py`
2. 实现双写逻辑(含并发控制):
   ```python
   from sqlalchemy import select
   from sqlalchemy.orm import Session
   
   def save_embedding_result(result_data: dict, vectors: List[dict], session: Session) -> EmbeddingResult:
       json_path = None
       try:
           # Step 0: Acquire row-level lock for concurrent safety (NFR-003)
           if result_data.get('document_id'):
               existing = session.execute(
                   select(EmbeddingResult)
                   .where(
                       EmbeddingResult.document_id == result_data['document_id'],
                       EmbeddingResult.model == result_data['model']
                   )
                   .with_for_update()  # Row-level lock
               ).scalar_one_or_none()
           
           # Step 1: Write JSON file
           json_path = self._write_json_file(vectors, result_data['result_id'])
           
           # Step 2: Write/update database record
           if existing:
               # FR-024: Update existing record
               for key, value in result_data.items():
                   setattr(existing, key, value)
               existing.json_file_path = self._get_relative_path(json_path)
               db_record = existing
           else:
               db_record = EmbeddingResult(
                   **result_data,
                   json_file_path=self._get_relative_path(json_path)
               )
               session.add(db_record)
           
           session.commit()
           return db_record
           
       except DatabaseError as e:
           session.rollback()
           # Step 3: Rollback - delete JSON file
           if json_path and os.path.exists(json_path):
               os.remove(json_path)
           raise StorageError(f"Database write failed: {e}")
   ```
3. 实现JSON文件写入方法 `_write_json_file()`
4. 编写集成测试验证并发场景
5. 编写并发测试模拟多线程同时更新同一document+model

**Files**:
- `backend/src/services/embedding_storage.py` (create)
- `backend/tests/integration/test_embedding_storage.py` (create)
- `backend/tests/integration/test_concurrent_updates.py` (create)

**Dependencies**: Task 1.1, Task 1.2

**Related Requirements**: FR-022, FR-023, FR-024, NFR-003, research.md Section 1

---

## Phase 2: 核心服务增强 (2.5天)

### Task 2.1: 扩展embedding_service支持分块向量化
**Priority**: P1  
**Estimate**: 1天  
**Type**: Backend - Service  
**Assignee**: Backend Developer  

**Description**:
在现有 `embedding_service.py` 基础上,新增从分块结果文件读取并批量向量化的功能。

**Acceptance Criteria**:
- [ ] 实现 `vectorize_from_chunking_result()` 方法
- [ ] 实现 `vectorize_from_document()` 方法(自动选择最新分块结果)
- [ ] 支持按chunking strategy过滤
- [ ] 返回向量顺序与输入chunk顺序一致(FR-020)
- [ ] 单元测试覆盖两种向量化模式

**Implementation Steps**:
1. 修改 `backend/src/services/embedding_service.py`
2. 添加方法:
   ```python
   def vectorize_from_chunking_result(self, chunking_result_id: str, model: str) -> dict:
       # Load chunks from JSON file
       chunks = self._load_chunks_from_result(chunking_result_id)
       
       # Batch vectorize
       vectors = await self._batch_vectorize(chunks, model)
       
       # Prepare response with source info
       return {
           "chunking_result_id": chunking_result_id,
           "model": model,
           "vectors": vectors
       }
   
   def vectorize_from_document(self, document_id: str, model: str, strategy: Optional[str] = None) -> dict:
       # Find latest chunking result
       chunking_result = self._find_latest_chunking_result(document_id, strategy)
       return self.vectorize_from_chunking_result(chunking_result.id, model)
   ```
3. 实现 `_load_chunks_from_result()` 辅助方法
4. 编写单元测试验证chunk顺序

**Files**:
- `backend/src/services/embedding_service.py` (modify)
- `backend/tests/unit/test_embedding_service.py` (modify)

**Dependencies**: Task 0.1

**Related Requirements**: FR-001, FR-002, FR-003, research.md Section 6

---

### Task 2.2: 实现异步API调用与重试机制
**Priority**: P1  
**Estimate**: 1天  
**Type**: Backend - Service  
**Assignee**: Backend Developer  

**Description**:
使用httpx实现异步API调用,集成tenacity实现指数退避重试,并添加操作日志记录。

**Acceptance Criteria**:
- [ ] 使用 `httpx.AsyncClient` 替代同步请求
- [ ] 实现重试策略: 初始1s, 最大32s, jitter±25%, 最多3次
- [ ] API超时设置为60秒
- [ ] 速率限制错误自动重试
- [ ] 实现操作日志: 记录请求数、延迟、使用的模型、错误率(FR-017)
- [ ] 单元测试模拟失败重试场景

**Implementation Steps**:
1. 在 `embedding_service.py` 中添加异步API方法:
   ```python
   from tenacity import retry, wait_exponential_jitter, stop_after_attempt
   import logging
   import time
   
   logger = logging.getLogger(__name__)
   
   @retry(
       wait=wait_exponential_jitter(initial=1, max=32, jitter=0.25),
       stop=stop_after_attempt(3),
       retry=retry_if_exception_type(httpx.HTTPStatusError)
   )
   async def _call_embedding_api(self, texts: List[str], model: str) -> List[List[float]]:
       start_time = time.time()
       try:
           async with httpx.AsyncClient(timeout=60.0) as client:
               response = await client.post(
                   f"{self.api_base_url}/v1/embeddings",
                   headers={"Authorization": f"Bearer {self.api_key}"},
                   json={"input": texts, "model": model}
               )
               response.raise_for_status()
               latency = time.time() - start_time
               
               # FR-017: Log operational metrics
               logger.info(f"Embedding request successful", extra={
                   "model": model,
                   "batch_size": len(texts),
                   "latency_ms": latency * 1000,
                   "status": "success"
               })
               
               return [item["embedding"] for item in response.json()["data"]]
       except Exception as e:
           latency = time.time() - start_time
           logger.error(f"Embedding request failed", extra={
               "model": model,
               "batch_size": len(texts),
               "latency_ms": latency * 1000,
               "error": str(e),
               "status": "failed"
           })
           raise
   ```
2. 添加日志聚合中间件记录请求计数和错误率
3. 实现维度验证逻辑(Task 2.3)
4. 编写单元测试模拟网络失败

**Files**:
- `backend/src/services/embedding_service.py` (modify)
- `backend/src/middleware/logging_middleware.py` (create for request counting)
- `backend/tests/unit/test_embedding_api_retry.py` (create)

**Dependencies**: Task 2.1

**Related Requirements**: FR-010, FR-011, FR-017, research.md Section 3

---

### Task 2.3: 实现向量维度验证
**Priority**: P1  
**Estimate**: 0.5天  
**Type**: Backend - Service  
**Assignee**: Backend Developer  

**Description**:
在接收API响应后立即验证向量维度是否与模型预期一致,失败快速报错。

**Acceptance Criteria**:
- [ ] 定义 `EXPECTED_DIMENSIONS` 配置字典
- [ ] 在 `_call_embedding_api()` 返回后立即验证
- [ ] 维度不匹配时抛出 `DimensionMismatchError`
- [ ] 错误消息包含: 模型名、期望维度、实际维度
- [ ] 单元测试覆盖维度不匹配场景

**Implementation Steps**:
1. 在 `embedding_service.py` 添加配置:
   ```python
   EXPECTED_DIMENSIONS = {
       "bge-m3": 1024,
       "qwen3-embedding-8b": 4096,
       "hunyuan-embedding": 1024,
       "jina-embeddings-v4": 2048
   }
   ```
2. 实现验证方法:
   ```python
   def _validate_dimensions(self, vectors: List[List[float]], model: str):
       expected = EXPECTED_DIMENSIONS[model]
       for idx, vec in enumerate(vectors):
           actual = len(vec)
           if actual != expected:
               raise DimensionMismatchError(
                   f"Vector {idx}: expected {expected} for '{model}', got {actual}"
               )
   ```
3. 在 `_call_embedding_api()` 返回前调用验证
4. 编写单元测试

**Files**:
- `backend/src/services/embedding_service.py` (modify)
- `backend/src/exceptions.py` (create `DimensionMismatchError`)
- `backend/tests/unit/test_dimension_validation.py` (create)

**Dependencies**: Task 2.2

**Related Requirements**: FR-014, research.md Section 5

---

## Phase 3: API路由层 (2天)

### Task 3.1: 实现向量化API端点
**Priority**: P1  
**Estimate**: 1天  
**Type**: Backend - API  
**Assignee**: Backend Developer  

**Description**:
实现3个向量化端点: 按分块结果、按文档、单文本/批量文本(仅后端)。

**Acceptance Criteria**:
- [ ] `POST /embedding/from-chunking-result` 实现
- [ ] `POST /embedding/from-document` 实现
- [ ] `POST /embedding/single` 实现(后端API only)
- [ ] `POST /embedding/batch` 实现(后端API only, 最大1000条)
- [ ] 所有端点返回统一JSON格式
- [ ] 集成Task 1.3的双写存储逻辑

**Implementation Steps**:
1. 修改 `backend/src/api/embedding_routes.py`
2. 定义Pydantic请求/响应模型:
   ```python
   class VectorizationFromChunkingRequest(BaseModel):
       chunking_result_id: str
       model: str
   
   class VectorizationResponse(BaseModel):
       request_id: str
       document_id: str
       model: str
       status: Literal['SUCCESS', 'FAILED', 'PARTIAL_SUCCESS']
       vectors: List[VectorResult]
       json_file_path: str
   ```
3. 实现路由处理器:
   ```python
   @router.post("/from-chunking-result", response_model=VectorizationResponse)
   async def vectorize_chunking_result(request: VectorizationFromChunkingRequest):
       result = await embedding_service.vectorize_from_chunking_result(
           request.chunking_result_id, request.model
       )
       # Save to storage (dual-write)
       saved = embedding_storage.save_embedding_result(result['metadata'], result['vectors'])
       return VectorizationResponse(**saved.to_dict())
   ```
4. 编写集成测试

**Files**:
- `backend/src/api/embedding_routes.py` (modify)
- `backend/tests/integration/test_embedding_api.py` (create)

**Dependencies**: Task 2.1, Task 2.2, Task 1.3

**Related Requirements**: FR-001 to FR-005, contracts/embedding.openapi.yaml

---

### Task 3.2: 实现查询API端点
**Priority**: P2  
**Estimate**: 1天  
**Type**: Backend - API  
**Assignee**: Backend Developer  

**Description**:
实现3个查询端点: 按result_id查询、按document_id查询、列表查询(带分页)。

**Acceptance Criteria**:
- [ ] `GET /embedding/results/{result_id}` 实现
- [ ] `GET /embedding/results/by-document/{document_id}` 实现(支持model过滤)
- [ ] `GET /embedding/results` 实现(支持分页、状态过滤、日期范围)
- [ ] 返回格式符合OpenAPI契约
- [ ] 集成测试验证查询性能(<100ms)

**Implementation Steps**:
1. 创建 `backend/src/api/embedding_query_routes.py`
2. 定义响应模型:
   ```python
   class EmbeddingResultDetail(BaseModel):
       result_id: str
       document_id: str
       model: str
       status: str
       successful_count: int
       # ... other 7 fields
   
   class EmbeddingResultListResponse(BaseModel):
       results: List[EmbeddingResultDetail]
       pagination: dict
   ```
3. 实现路由:
   ```python
   @router.get("/results/{result_id}", response_model=EmbeddingResultDetail)
   async def get_result_by_id(result_id: str):
       result = embedding_db.get_by_result_id(result_id)
       if not result:
           raise HTTPException(404, "Result not found")
       return EmbeddingResultDetail.from_orm(result)
   
   @router.get("/results", response_model=EmbeddingResultListResponse)
   async def list_results(page: int = 1, page_size: int = 20, status: str = None):
       results, total = embedding_db.list_results(filters={'status': status}, page, page_size)
       return {
           "results": [EmbeddingResultDetail.from_orm(r) for r in results],
           "pagination": {
               "total_count": total,
               "current_page": page,
               "page_size": page_size
           }
       }
   ```
4. 编写集成测试

**Files**:
- `backend/src/api/embedding_query_routes.py` (create)
- `backend/tests/integration/test_embedding_query_api.py` (create)

**Dependencies**: Task 1.2

**Related Requirements**: FR-025 to FR-027, contracts/embedding-query.openapi.yaml

---

### Task 3.3: 实现健康检查端点
**Priority**: P2  
**Estimate**: 0.5天  
**Type**: Backend - API  
**Assignee**: Backend Developer  

**Description**:
实现 `/health` 端点,验证服务状态、API连接、模型可用性。

**Acceptance Criteria**:
- [ ] 返回结构化JSON: `{"status": "healthy|degraded|unhealthy", ...}`
- [ ] 验证API endpoint可达性(5秒超时)
- [ ] 验证至少一个模型可用
- [ ] 验证API认证有效性
- [ ] 单元测试覆盖三种状态

**Implementation Steps**:
1. 在 `embedding_routes.py` 添加健康检查:
   ```python
   @router.get("/health")
   async def health_check():
       try:
           # Test API connectivity
           async with httpx.AsyncClient(timeout=5.0) as client:
               response = await client.get(f"{API_BASE_URL}/v1/models")
               models = response.json().get("data", [])
           
           return {
               "status": "healthy",
               "service": "up",
               "api_connectivity": True,
               "models_available": [m["id"] for m in models],
               "authentication": "valid",
               "timestamp": datetime.utcnow().isoformat()
           }
       except Exception as e:
           return {
               "status": "degraded",
               "service": "up",
               "api_connectivity": False,
               "error": str(e)
           }
   ```
2. 编写单元测试模拟各种状态

**Files**:
- `backend/src/api/embedding_routes.py` (modify)
- `backend/tests/unit/test_health_check.py` (create)

**Dependencies**: Task 0.1

**Related Requirements**: NFR-001

---

## Phase 4: 前端开发 (3天)

### Task 4.1: 创建统一向量化页面路由
**Priority**: P1  
**Estimate**: 0.5天  
**Type**: Frontend - Routing  
**Assignee**: Frontend Developer  

**Description**:
在Vue Router中配置 `/documents/embed` 路由,移除旧的文本向量化路由。

**Acceptance Criteria**:
- [ ] 路由配置: `{ path: '/documents/embed', component: VectorEmbed }`
- [ ] 导航菜单显示单一入口: "文档向量化"
- [ ] 旧路由 `/embeddings` 已移除或重定向
- [ ] 路由守卫验证用户已登录

**Implementation Steps**:
1. 修改 `frontend/src/router/index.js`:
   ```javascript
   {
     path: '/documents/embed',
     name: 'VectorEmbed',
     component: () => import('@/views/VectorEmbed.vue'),
     meta: { requiresAuth: true }
   }
   ```
2. 修改导航菜单 `frontend/src/components/Navigation.vue`:
   ```vue
   <t-menu-item value="embed">
     <template #icon><DocumentIcon /></template>
     文档向量化
   </t-menu-item>
   ```
3. 删除或重定向旧路由

**Files**:
- `frontend/src/router/index.js` (modify)
- `frontend/src/components/Navigation.vue` (modify)

**Dependencies**: None

**Related Requirements**: FR-029, FR-030

---

### Task 4.2: 实现文档选择器组件
**Priority**: P1  
**Estimate**: 1天  
**Type**: Frontend - Component  
**Assignee**: Frontend Developer  

**Description**:
实现文档选择下拉框,仅显示已分块文档,格式化显示"文档名 · 已分块 · 日期"。

**Acceptance Criteria**:
- [ ] 调用 `GET /documents?status=chunked` API获取数据
- [ ] 下拉选项格式: `{name} · 已分块 · {date}`
- [ ] 未分块文档完全不显示
- [ ] 空状态提示: "暂无已分块文档,请先对文档进行分块处理"
- [ ] 单元测试覆盖数据加载与格式化

**Implementation Steps**:
1. 创建 `frontend/src/components/embedding/DocumentSelector.vue`:
   ```vue
   <template>
     <t-select
       v-model="selectedDocId"
       placeholder="选择已分块的文档"
       :loading="loading"
       @change="handleSelect"
     >
       <t-option
         v-for="doc in chunkedDocs"
         :key="doc.id"
         :value="doc.id"
         :label="formatDocLabel(doc)"
       />
       <template #empty>
         <div class="empty-state">
           暂无已分块文档,请先对文档进行分块处理
         </div>
       </template>
     </t-select>
   </template>
   
   <script setup>
   import { ref, onMounted } from 'vue'
   import { fetchChunkedDocuments } from '@/services/documentApi'
   
   const chunkedDocs = ref([])
   const loading = ref(false)
   
   onMounted(async () => {
     loading.value = true
     chunkedDocs.value = await fetchChunkedDocuments()
     loading.value = false
   })
   
   function formatDocLabel(doc) {
     const date = new Date(doc.latest_chunking.created_at).toLocaleDateString()
     return `${doc.name} · 已分块 · ${date}`
   }
   </script>
   ```
2. 编写单元测试

**Files**:
- `frontend/src/components/embedding/DocumentSelector.vue` (create)
- `frontend/tests/components/DocumentSelector.test.js` (create)

**Dependencies**: Task 4.1

**Related Requirements**: FR-031, FR-032, FR-039

---

### Task 4.3: 实现模型选择器组件
**Priority**: P1  
**Estimate**: 1天  
**Type**: Frontend - Component  
**Assignee**: Frontend Developer  

**Description**:
实现模型选择下拉框,显示"模型名 · 维度维 · 简述",选中后显示详细信息面板。

**Acceptance Criteria**:
- [ ] 调用 `GET /embedding/models` API获取模型列表
- [ ] 下拉选项格式: `BGE-M3 · 1024维 · 多语言支持`
- [ ] 选中后显示详情面板: 维度、提供商、多语言支持、最大批次
- [ ] 支持响应式布局
- [ ] 单元测试覆盖模型加载与详情显示

**Implementation Steps**:
1. 创建 `frontend/src/components/embedding/ModelSelector.vue`:
   ```vue
   <template>
     <div class="model-selector">
       <t-select
         v-model="selectedModel"
         placeholder="选择向量模型"
         @change="handleModelChange"
       >
         <t-option
           v-for="model in models"
           :key="model.name"
           :value="model.name"
           :label="formatModelLabel(model)"
         />
       </t-select>
       
       <t-card v-if="selectedModelInfo" class="model-info">
         <template #header>模型详情</template>
         <div>维度: {{ selectedModelInfo.dimension }}维</div>
         <div>提供商: {{ selectedModelInfo.provider }}</div>
         <div>多语言: {{ selectedModelInfo.supports_multilingual ? '是' : '否' }}</div>
         <div>最大批次: {{ selectedModelInfo.max_batch_size }}</div>
       </t-card>
     </div>
   </template>
   
   <script setup>
   import { ref, computed } from 'vue'
   import { fetchModels } from '@/services/embeddingApi'
   
   const models = ref([])
   const selectedModel = ref(null)
   
   const selectedModelInfo = computed(() => 
     models.value.find(m => m.name === selectedModel.value)
   )
   
   function formatModelLabel(model) {
     return `${model.name} · ${model.dimension}维 · ${model.description.split('，')[0]}`
   }
   </script>
   ```
2. 编写单元测试

**Files**:
- `frontend/src/components/embedding/ModelSelector.vue` (create)
- `frontend/tests/components/ModelSelector.test.js` (create)

**Dependencies**: Task 3.1 (需要 `/embedding/models` API)

**Related Requirements**: FR-033, FR-034

---

### Task 4.4: 实现向量化主页面
**Priority**: P1  
**Estimate**: 1.5天  
**Type**: Frontend - Page  
**Assignee**: Frontend Developer  

**Description**:
组装完整的向量化页面,包含两列布局、Pinia状态管理、触发向量化按钮。

**Acceptance Criteria**:
- [ ] 两列布局: 左侧(文档选择+模型配置+按钮),右侧(结果展示)
- [ ] 按钮状态: 未选择文档时禁用,向量化中显示loading
- [ ] 点击按钮调用 `POST /embedding/from-document` API
- [ ] 结果通过Pinia store共享给结果组件
- [ ] 错误处理: Toast提示API错误
- [ ] 集成测试验证完整流程

**Implementation Steps**:
1. 创建 `frontend/src/views/VectorEmbed.vue`:
   ```vue
   <template>
     <div class="vector-embed-page">
       <t-row :gutter="16">
         <!-- Left Column -->
         <t-col :span="6">
           <t-space direction="vertical" size="large">
             <DocumentSelector v-model="selectedDocId" />
             <ModelSelector v-model="selectedModel" />
             <t-button
               theme="primary"
               block
               :disabled="!canStartVectorization"
               :loading="isVectorizing"
               @click="startVectorization"
             >
               开始向量化
             </t-button>
           </t-space>
         </t-col>
         
         <!-- Right Column -->
         <t-col :span="18">
           <EmbeddingResults />
         </t-col>
       </t-row>
     </div>
   </template>
   
   <script setup>
   import { ref, computed } from 'vue'
   import { useEmbeddingStore } from '@/stores/embedding'
   import DocumentSelector from '@/components/embedding/DocumentSelector.vue'
   import ModelSelector from '@/components/embedding/ModelSelector.vue'
   import EmbeddingResults from '@/components/embedding/EmbeddingResults.vue'
   
   const store = useEmbeddingStore()
   const selectedDocId = ref(null)
   const selectedModel = ref(null)
   const isVectorizing = ref(false)
   
   const canStartVectorization = computed(() => 
     selectedDocId.value && selectedModel.value
   )
   
   async function startVectorization() {
     isVectorizing.value = true
     try {
       await store.startVectorization(selectedDocId.value, selectedModel.value)
     } catch (error) {
       MessagePlugin.error(`向量化失败: ${error.message}`)
     } finally {
       isVectorizing.value = false
     }
   }
   </script>
   ```
2. 创建Pinia store `frontend/src/stores/embedding.js`
3. 编写集成测试

**Files**:
- `frontend/src/views/VectorEmbed.vue` (create)
- `frontend/src/stores/embedding.js` (create)
- `frontend/tests/integration/VectorEmbed.test.js` (create)

**Dependencies**: Task 4.2, Task 4.3

**Related Requirements**: FR-035, FR-036, FR-038

---

### Task 4.5: 增强结果展示组件
**Priority**: P2  
**Estimate**: 1天  
**Type**: Frontend - Component  
**Assignee**: Frontend Developer  

**Description**:
在现有 `EmbeddingResults.vue` 基础上,添加文档源信息展示。

**Acceptance Criteria**:
- [ ] 顶部显示: 文档名称、分块数量、向量维度
- [ ] 保留现有热力图、统计卡片、分页功能
- [ ] 空状态优化: 显示"请选择文档并开始向量化"
- [ ] 响应式布局适配移动端

**Implementation Steps**:
1. 修改 `frontend/src/components/embedding/EmbeddingResults.vue`:
   ```vue
   <template>
     <div class="embedding-results">
       <!-- Document Source Info -->
       <t-card v-if="currentResult" class="source-info">
         <t-descriptions>
           <t-descriptions-item label="文档名称">{{ currentResult.document_name }}</t-descriptions-item>
           <t-descriptions-item label="分块数量">{{ currentResult.total_chunks }}</t-descriptions-item>
           <t-descriptions-item label="向量维度">{{ currentResult.vector_dimension }}维</t-descriptions-item>
         </t-descriptions>
       </t-card>
       
       <!-- Existing visualizations -->
       <StatisticsCards v-if="currentResult" :vectors="currentResult.vectors" />
       <HeatmapView v-if="currentResult" :vectors="currentResult.vectors" />
       
       <!-- Empty state -->
       <t-empty v-else description="请选择文档并开始向量化" />
     </div>
   </template>
   
   <script setup>
   import { computed } from 'vue'
   import { useEmbeddingStore } from '@/stores/embedding'
   
   const store = useEmbeddingStore()
   const currentResult = computed(() => store.currentResult)
   </script>
   ```
2. 更新单元测试

**Files**:
- `frontend/src/components/embedding/EmbeddingResults.vue` (modify)
- `frontend/tests/components/EmbeddingResults.test.js` (modify)

**Dependencies**: Task 4.4

**Related Requirements**: FR-037

---

## Phase 5: 测试与验证 (2天)

### Task 5.1: 端到端集成测试
**Priority**: P1  
**Estimate**: 1天  
**Type**: Testing  
**Assignee**: QA Engineer / Full-stack Developer  

**Description**:
编写覆盖完整工作流的E2E测试: 文档选择 → 模型选择 → 向量化 → 结果展示。

**Acceptance Criteria**:
- [ ] 测试场景1: 成功向量化100个chunks
- [ ] 测试场景2: 部分chunks失败(PARTIAL_SUCCESS)
- [ ] 测试场景3: 文档无分块结果(404错误)
- [ ] 测试场景4: API超时重试
- [ ] 测试场景5: 双写事务回滚验证
- [ ] 测试场景6: 并发请求处理(NFR-003验证)
- [ ] 测试场景7: 操作日志完整性验证(FR-017)

**Implementation Steps**:
1. 使用pytest + httpx.AsyncClient编写后端E2E测试:
   ```python
   @pytest.mark.asyncio
   async def test_full_vectorization_workflow():
       # Prepare test document with chunking result
       doc = create_test_document_with_chunks(chunk_count=100)
       
       # Call vectorization API
       response = await client.post(
           "/embedding/from-document",
           json={"document_id": doc.id, "model": "bge-m3"}
       )
       assert response.status_code == 200
       
       # Verify database record
       result = db.query(EmbeddingResult).filter_by(document_id=doc.id).first()
       assert result.status == "SUCCESS"
       assert result.successful_count == 100
       
       # Verify JSON file exists
       assert os.path.exists(result.json_file_path)
   
   @pytest.mark.asyncio
   async def test_concurrent_requests():
       """Test NFR-003: Concurrent requests without data corruption"""
       doc = create_test_document_with_chunks(chunk_count=50)
       
       # Launch 5 concurrent requests for same document+model
       tasks = [
           client.post("/embedding/from-document", 
                      json={"document_id": doc.id, "model": "bge-m3"})
           for _ in range(5)
       ]
       responses = await asyncio.gather(*tasks)
       
       # Verify only one final record exists (no race condition)
       results = db.query(EmbeddingResult).filter_by(
           document_id=doc.id, model="bge-m3"
       ).all()
       assert len(results) == 1, "Concurrent updates should not create duplicates"
   
   def test_operational_logging():
       """Test FR-017: Log completeness"""
       with mock.patch('logging.Logger.info') as mock_logger:
           # Trigger vectorization
           response = client.post("/embedding/from-document", 
                                  json={"document_id": "test", "model": "bge-m3"})
           
           # Verify log contains required metrics
           log_calls = [call.kwargs['extra'] for call in mock_logger.call_args_list]
           assert any('latency_ms' in log for log in log_calls)
           assert any('batch_size' in log for log in log_calls)
           assert any('model' in log for log in log_calls)
   ```
2. 使用Playwright编写前端E2E测试
3. 编写性能测试验证NFR-004(5秒内完成100向量双写)

**Files**:
- `backend/tests/e2e/test_vectorization_workflow.py` (create)
- `backend/tests/e2e/test_concurrent_safety.py` (create)
- `backend/tests/e2e/test_logging.py` (create)
- `frontend/tests/e2e/vectorization.spec.js` (create)

**Dependencies**: All Phase 1-4 tasks

**Related Requirements**: User Story 1, User Story 2, User Story 3, NFR-003, FR-017

---

### Task 5.2: 性能测试与优化
**Priority**: P2  
**Estimate**: 1天  
**Type**: Testing  
**Assignee**: Backend Developer  

**Description**:
验证系统性能指标,优化慢查询和批处理逻辑。

**Acceptance Criteria**:
- [ ] 查询性能: 按document_id查询 <100ms (10k记录)
- [ ] 列表查询: 分页查询 <200ms
- [ ] 双写性能: 100个4096维向量 <5秒
- [ ] 向量化性能: 100个chunks <30秒
- [ ] 性能测试报告生成

**Implementation Steps**:
1. 使用Locust编写负载测试脚本:
   ```python
   from locust import HttpUser, task, between
   
   class EmbeddingUser(HttpUser):
       wait_time = between(1, 3)
       
       @task
       def vectorize_document(self):
           self.client.post(
               "/embedding/from-document",
               json={"document_id": "test-doc", "model": "bge-m3"}
           )
       
       @task(3)  # More frequent
       def query_latest(self):
           self.client.get("/embedding/results/by-document/test-doc")
   ```
2. 使用pytest-benchmark测试关键路径:
   ```python
   def test_database_query_performance(benchmark):
       result = benchmark(embedding_db.get_latest_by_document, "doc-123")
       assert result is not None
   ```
3. 分析慢查询,优化索引策略
4. 生成性能报告

**Files**:
- `backend/tests/performance/locustfile.py` (create)
- `backend/tests/performance/test_benchmarks.py` (create)
- `docs/performance-report.md` (create)

**Dependencies**: Task 5.1

**Related Requirements**: NFR-004, SC-016, SC-017

---

## Phase 6: 文档与交付 (1天)

### Task 6.1: API文档生成
**Priority**: P2  
**Estimate**: 0.5天  
**Type**: Documentation  
**Assignee**: Backend Developer  

**Description**:
使用OpenAPI规范生成Swagger文档,提供交互式API测试界面。

**Acceptance Criteria**:
- [ ] Swagger UI可访问: `http://localhost:8000/docs`
- [ ] 所有端点包含请求/响应示例
- [ ] 错误码文档完整(400, 404, 500等)
- [ ] 支持"Try it out"在线测试

**Implementation Steps**:
1. 在 `backend/main.py` 配置Swagger:
   ```python
   from fastapi import FastAPI
   from fastapi.openapi.utils import get_openapi
   
   app = FastAPI(
       title="RAG Framework - Embedding API",
       version="1.0.0",
       docs_url="/docs",
       redoc_url="/redoc"
   )
   ```
2. 为所有路由添加docstrings和response_model
3. 验证Swagger UI渲染正确

**Files**:
- `backend/main.py` (modify)
- `backend/src/api/*.py` (add docstrings)

**Dependencies**: Task 3.1, Task 3.2

**Related Requirements**: NFR-002

---

### Task 6.2: 用户手册与开发者指南
**Priority**: P3  
**Estimate**: 0.5天  
**Type**: Documentation  
**Assignee**: Technical Writer / Developer  

**Description**:
编写面向最终用户的操作手册和开发者集成指南。

**Acceptance Criteria**:
- [ ] 用户手册包含: 如何选择文档、如何选择模型、如何解读结果
- [ ] 开发者指南包含: API调用示例、错误处理、性能优化建议
- [ ] 包含常见问题FAQ
- [ ] 截图/动图演示关键操作

**Implementation Steps**:
1. 编写 `docs/user-guide.md`:
   - 功能介绍
   - 分步操作指南(带截图)
   - 结果解读说明
2. 编写 `docs/developer-guide.md`:
   - API集成示例(Python/JavaScript)
   - 错误码参考表
   - 性能调优建议
3. 编写 `docs/faq.md`:
   - "为什么我的文档不显示?" → 需先分块
   - "如何选择合适的模型?" → 根据维度和语言需求
   - "向量化失败怎么办?" → 查看error_message字段

**Files**:
- `docs/user-guide.md` (create)
- `docs/developer-guide.md` (create)
- `docs/faq.md` (create)

**Dependencies**: Task 5.1 (需要完整功能验证)

**Related Requirements**: User Story 3 (用户体验)

---

## 📊 Summary Statistics

### 任务总览
- **总任务数**: 19个
- **总估时**: 13.5天 (~2.7周)
- **优先级分布**:
  - P0 (阻塞性): 4个任务 (3.5天)
  - P1 (核心功能): 10个任务 (8天)
  - P2 (重要功能): 4个任务 (3天)
  - P3 (增强功能): 1个任务 (0.5天)

### 按阶段分布
| Phase | 任务数 | 估时 | 关键里程碑 |
|-------|--------|------|-----------|
| Phase 0 | 1 | 0.5天 | 环境就绪 |
| Phase 1 | 3 | 3天 | 数据库存储完成 |
| Phase 2 | 3 | 2.5天 | 核心服务就绪 |
| Phase 3 | 3 | 2天 | API完整可用 |
| Phase 4 | 5 | 4.5天 | 前端功能上线 |
| Phase 5 | 2 | 2天 | 测试通过 |
| Phase 6 | 2 | 1天 | 文档交付 |

### 关键路径 (Critical Path)
```
Task 0.1 → Task 1.1 → Task 1.2 → Task 1.3 → Task 2.1 → Task 2.2 → Task 3.1 → Task 4.4 → Task 5.1
```
关键路径总时长: **10.5天**

### 并行机会
- **Phase 1**: Task 1.1完成后,Task 1.2 和 Task 2.1 可并行开发
- **Phase 3**: Task 3.1 和 Task 3.2 可并行开发(不同团队成员)
- **Phase 4**: Task 4.2 和 Task 4.3 可并行开发

### 资源需求
- **Backend Developer**: 2人 × 10天
- **Frontend Developer**: 1人 × 5天
- **QA Engineer**: 1人 × 2天(可兼任)
- **Technical Writer**: 0.5人 × 1天(可兼任)

---

## 🚀 Getting Started

### 建议开发顺序
1. **Week 1 (Day 1-5)**: 
   - Backend团队完成 Phase 0-2 (数据库+核心服务)
   - Frontend团队完成 Task 4.1-4.2 (路由+文档选择器)

2. **Week 2 (Day 6-10)**:
   - Backend团队完成 Phase 3 (API层)
   - Frontend团队完成 Task 4.3-4.5 (模型选择+主页面+结果)

3. **Week 3 (Day 11-13)**:
   - 全团队协作完成 Phase 5-6 (测试+文档)

### 第一个任务
**立即开始**: Task 0.1 - 依赖安装与配置验证  
**负责人**: Backend Lead  
**预计完成**: 0.5天  

---

## 📝 Notes

### 风险提示
1. **API依赖风险**: 外部embedding API不稳定可能阻塞Task 2.2,建议提前验证连接
2. **性能瓶颈**: 4096维向量双写可能超时,Task 5.2性能测试需提前进行
3. **前后端协调**: Task 4.4依赖Task 3.1 API就绪,需做好接口联调计划

### 质量门禁
- **Phase 1结束**: 数据库schema通过code review,索引性能验证通过
- **Phase 3结束**: 所有API端点通过OpenAPI contract测试
- **Phase 5结束**: 覆盖率 >80%, 性能指标达标(SC-016/017)

### 迭代计划
- **MVP范围**: 完成P0 + P1任务(核心功能)
- **V1.1增强**: 完成P2任务(查询API、结果展示优化)
- **V1.2完善**: 完成P3任务(文档、健康检查)
