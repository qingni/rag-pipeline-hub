# Tasks: 文本生成功能优化

**Input**: Design documents from `/specs/006-text-generation/`
**Prerequisites**: plan.md (required), spec.md (required)

**Note**: 本分支为优化分支，基于现有实现进行修改，任务按优化项组织而非用户故事。

## Format: `[ID] [P?] [OPT] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[OPT]**: 优化项标识 (OPT1=Collection选择器, OPT2=Token截断, OPT3=引用格式)
- Include exact file paths in descriptions

---

## Phase 1: 后端优化

**Purpose**: Token 截断策略和引用格式 Prompt 优化

### OPT2: Token 截断策略

- [X] T001 [OPT2] 在 `backend/src/services/generation_service.py` 中新增 `_truncate_context_by_token_budget()` 方法
- [X] T002 [OPT2] 在 `generate()` 方法中调用 token 截断，在 `_build_prompt()` 前应用
- [X] T003 [OPT2] 在 `generate_stream()` 方法中调用 token 截断，在 `_build_prompt()` 前应用

### OPT3: 引用格式 Prompt 优化

- [X] T004 [P] [OPT3] 更新 `backend/src/services/generation_service.py` 中的 `SYSTEM_PROMPT_TEMPLATE`，明确引用格式要求

**Checkpoint**: 后端优化完成，可独立测试 token 截断和引用格式

---

## Phase 2: 前端优化

**Purpose**: Collection 选择器修复

### OPT1: 修改 generationStore.js

- [X] T005 [OPT1] 在 `frontend/src/stores/generationStore.js` 中将导入从 `getAvailableIndexes` 改为 `getAvailableCollections`
- [X] T006 [OPT1] 重命名状态变量 `availableIndexes` → `availableCollections`
- [X] T007 [OPT1] 重命名状态变量 `selectedIndexIds` → `selectedCollectionIds`
- [X] T008 [OPT1] 重命名函数 `loadAvailableIndexes()` → `loadAvailableCollections()`
- [X] T009 [OPT1] 更新 `retrieveContext()` 中的参数 `index_ids` → `collection_ids`
- [X] T010 [OPT1] 更新 return 语句中的导出变量名

### OPT1: 修改 GenerationConfig.vue

- [X] T011 [OPT1] 在 `frontend/src/components/generation/GenerationConfig.vue` 中更新 props: `indexIds` → `collectionIds`, `availableIndexes` → `availableCollections`
- [X] T012 [OPT1] 更新下拉选项渲染：显示 `name`, `document_count`, `vector_count`
- [X] T013 [OPT1] 更新标签文案："知识库索引" → "知识库"
- [X] T014 [OPT1] 更新 emit 事件名：`update:indexIds` → `update:collectionIds`

### OPT1: 修改 Generation.vue

- [X] T015 [OPT1] 在 `frontend/src/views/Generation.vue` 中更新 storeToRefs 变量名
- [X] T016 [OPT1] 更新 GenerationConfig 组件 props 绑定
- [X] T017 [OPT1] 更新 onMounted 中的函数调用

**Checkpoint**: 前端优化完成，Collection 选择器应正确显示知识库列表

---

## Phase 3: 集成验证

**Purpose**: 端到端验证所有优化项

- [X] T018 验证 Collection 选择器显示知识库名称（而非文档索引名）
- [X] T019 验证选择 Collection 后检索 + 生成流程正常
- [X] T020 验证大量检索结果被正确截断（不报 token 超限错误）
- [X] T021 验证生成回答包含内联引用 [1][2] 和末尾参考来源列表

---

## Phase 4: 当前实现同步补充

**Purpose**: 同步近期已落地但尚未记录到 tasks 的能力补充

- [X] T022 [P] 在 `backend/src/api/generation.py` 中补齐 `DELETE /history/clear`，支持全部历史软删除
- [X] T023 [P] 在 `frontend/src/components/generation/GenerationResult.vue` 中增加失败后的重试交互入口
- [X] T024 [P] 在 `frontend/src/views/Generation.vue` 中接入重试处理及历史刷新/删除/清空成功失败提示
- [X] T025 [P] 在 `frontend/src/components/generation/GenerationResult.vue` 中实现 Markdown 富文本渲染与引用高亮
- [X] T026 [P] 在 `frontend/package.json` 中引入 `markdown-it`、`dompurify` 以支持安全渲染
- [X] T027 [P] 在 `frontend/src/stores/generationStore.js` 中补充清空历史后的页码状态重置

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (后端) ─┐
               ├─→ Phase 3 (集成验证)
Phase 2 (前端) ─┘
```

### 任务依赖

**后端任务链**:
```
T001 → T002 → T003 (顺序执行)
T004 (可并行)
```

**前端任务链**:
```
T005 → T006 → T007 → T008 → T009 → T010 (顺序执行，同一文件)
T011, T012, T013, T014 (可并行，但同一文件，建议顺序)
T015 → T016 → T017 (顺序执行，同一文件)
```

### Parallel Opportunities

- Phase 1 和 Phase 2 **可并行**执行（后端和前端独立）
- T004 和 T001-T003 **可并行**执行（不同代码段）
- T011-T014 同一文件，顺序执行

---

## 详细代码变更

### T001: 新增 `_truncate_context_by_token_budget()` 方法

**文件**: `backend/src/services/generation_service.py`

**位置**: 在 `_build_prompt()` 方法后添加

```python
def _truncate_context_by_token_budget(
    self,
    context: List[ContextItem],
    model: str,
    question: str,
    max_tokens: int,
) -> List[ContextItem]:
    """按 token 预算截断上下文，保留高相关性内容。
    
    Args:
        context: 上下文列表（假设已按相关性排序）
        model: 模型名称
        question: 用户问题
        max_tokens: 回答预留 token 数
        
    Returns:
        截断后的上下文列表
    """
    if not context:
        return context
    
    model_info = GENERATION_MODELS.get(model)
    if not model_info:
        return context
    
    max_context_tokens = model_info["context_length"]
    
    # 预算 = 模型最大上下文 - 系统 prompt (~500) - 问题 - 回答预留
    system_prompt_tokens = 500
    question_tokens = self.estimate_tokens(question)
    reserved_output = max_tokens
    
    budget = max_context_tokens - system_prompt_tokens - question_tokens - reserved_output
    
    # 安全边界：至少保留 10% buffer
    budget = int(budget * 0.9)
    
    if budget <= 0:
        return []
    
    # 从高相关性到低相关性累加
    selected = []
    used_tokens = 0
    
    for item in context:
        item_tokens = self.estimate_tokens(item.content)
        if used_tokens + item_tokens <= budget:
            selected.append(item)
            used_tokens += item_tokens
        else:
            break
    
    return selected
```

---

### T002-T003: 调用 token 截断

**文件**: `backend/src/services/generation_service.py`

**在 `generate()` 方法中**，找到：
```python
# Build prompts
system_prompt, user_prompt = self._build_prompt(
    request.question,
    request.context
)
```

**修改为**：
```python
# Truncate context by token budget
truncated_context = self._truncate_context_by_token_budget(
    request.context,
    request.model,
    request.question,
    request.max_tokens,
)

# Build prompts
system_prompt, user_prompt = self._build_prompt(
    request.question,
    truncated_context
)
```

**在 `generate_stream()` 方法中**，同样位置做相同修改。

---

### T004: 更新 SYSTEM_PROMPT_TEMPLATE

**文件**: `backend/src/services/generation_service.py`

**找到**：
```python
SYSTEM_PROMPT_TEMPLATE = """你是一个智能问答助手。请基于以下参考资料回答用户的问题。
...
```

**替换为**：
```python
SYSTEM_PROMPT_TEMPLATE = """你是一个智能问答助手。请基于以下参考资料回答用户的问题。

## 参考资料

{context}

## 回答要求

1. 基于参考资料给出准确、详细的回答
2. 在引用参考资料时，必须在相关内容后使用 [1]、[2] 等编号标注来源
3. 在回答的末尾，必须附上参考来源列表，格式如下：

**参考来源:**
[1] 文档名1
[2] 文档名2

4. 如果参考资料不足以回答问题，请明确说明
5. 回答应该条理清晰，易于理解
6. 即使只引用了一个来源，也要在末尾列出"""
```

---

### T005-T010: 修改 generationStore.js

**文件**: `frontend/src/stores/generationStore.js`

**T005 - 修改导入**:
```javascript
// 原来
import { getAvailableIndexes, executeSearch } from '../services/searchApi'

// 改为
import { getAvailableCollections, executeHybridSearch } from '../services/searchApi'
```

**T006-T007 - 修改状态变量**:
```javascript
// 原来
const availableIndexes = ref([])
const selectedIndexIds = ref([])

// 改为
const availableCollections = ref([])
const selectedCollectionIds = ref([])
```

**T008 - 修改函数名**:
```javascript
// 原来
async function loadAvailableIndexes() {
  isLoadingIndexes.value = true
  try {
    const response = await getAvailableIndexes()
    if (response.success) {
      availableIndexes.value = response.data || []
    }
  } ...
}

// 改为
async function loadAvailableCollections() {
  isLoadingIndexes.value = true
  try {
    const response = await getAvailableCollections()
    if (response.success) {
      availableCollections.value = response.data || []
    }
  } ...
}
```

**T009 - 修改检索参数**:
```javascript
// 在 retrieveContext() 中
// 原来
const params = {
  query_text: query,
  index_ids: selectedIndexIds.value,
  ...
}
const response = await executeSearch(params)

// 改为
const params = {
  query_text: query,
  collection_ids: selectedCollectionIds.value,
  ...
}
const response = await executeHybridSearch(params)
```

**T010 - 修改导出**:
```javascript
return {
  // 改为
  availableCollections,
  selectedCollectionIds,
  loadAvailableCollections,
  ...
}
```

---

### T011-T014: 修改 GenerationConfig.vue

**文件**: `frontend/src/components/generation/GenerationConfig.vue`

**T011 - 修改 props**:
```javascript
// 原来
indexIds: { type: Array, default: () => [] },
availableIndexes: { type: Array, default: () => [] },

// 改为
collectionIds: { type: Array, default: () => [] },
availableCollections: { type: Array, default: () => [] },
```

**T12 - 修改下拉选项**:
```vue
<!-- 原来 -->
<t-option
  v-for="index in availableIndexes"
  :key="index.id"
  :value="index.id"
  :label="index.name"
>
  <div class="index-option">
    <div class="index-name">{{ index.name }}</div>
    <div class="index-desc">
      {{ index.vector_count || 0 }} 向量 · {{ index.dimension }}维
    </div>
  </div>
</t-option>

<!-- 改为 -->
<t-option
  v-for="collection in availableCollections"
  :key="collection.id"
  :value="collection.id"
  :label="collection.name"
>
  <div class="collection-option">
    <div class="collection-name">{{ collection.name }}</div>
    <div class="collection-desc">
      {{ collection.document_count || 0 }} 文档 · {{ collection.vector_count || 0 }} 向量
    </div>
  </div>
</t-option>
```

**T13 - 修改标签文案**:
```vue
<!-- 原来 -->
<label class="config-label">
  <span>知识库索引</span>
  ...
</label>
<t-select ... placeholder="选择知识库索引（可多选）">

<!-- 改为 -->
<label class="config-label">
  <span>知识库</span>
  ...
</label>
<t-select ... placeholder="选择知识库（可多选）">
```

**T14 - 修改 emit 和 computed**:
```javascript
// 原来
const selectedIndexIds = computed({
  get: () => props.indexIds,
  set: (value) => emit('update:indexIds', value)
})

// 改为
const selectedCollectionIds = computed({
  get: () => props.collectionIds,
  set: (value) => emit('update:collectionIds', value)
})
```

---

### T015-T017: 修改 Generation.vue

**文件**: `frontend/src/views/Generation.vue`

**T15 - 修改 storeToRefs**:
```javascript
// 原来
const {
  availableIndexes,
  selectedIndexIds,
  ...
} = storeToRefs(store)

// 改为
const {
  availableCollections,
  selectedCollectionIds,
  ...
} = storeToRefs(store)
```

**T16 - 修改 GenerationConfig props**:
```vue
<!-- 原来 -->
<GenerationConfig 
  v-model:indexIds="selectedIndexIds"
  :available-indexes="availableIndexes"
  ...
/>

<!-- 改为 -->
<GenerationConfig 
  v-model:collectionIds="selectedCollectionIds"
  :available-collections="availableCollections"
  ...
/>
```

**T17 - 修改 onMounted**:
```javascript
// 原来
onMounted(() => {
  store.loadModels()
  store.loadAvailableIndexes()
})

// 改为
onMounted(() => {
  store.loadModels()
  store.loadAvailableCollections()
})
```

---

## Notes

- [P] 任务可并行执行
- 后端和前端 Phase 可并行开发
- 每个任务完成后建议 commit
- Phase 3 验证需要同时启动前后端服务
