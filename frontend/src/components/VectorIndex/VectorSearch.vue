<template>
  <t-card title="向量搜索" :bordered="false">
    <template #subtitle>
      <t-space>
        <span>索引: {{ index.index_name }}</span>
        <t-tag theme="success" variant="light">{{ index.status }}</t-tag>
        <t-tag v-if="index.has_sparse" theme="warning" variant="light">稀疏向量</t-tag>
      </t-space>
    </template>

    <t-form
      ref="formRef"
      :data="searchData"
      label-width="100px"
      @submit="handleSearch"
    >
      <!-- 检索模式切换 -->
      <t-form-item label="检索模式">
        <t-radio-group v-model="searchMode" variant="default-filled">
          <t-radio-button value="dense">纯稠密检索</t-radio-button>
          <t-radio-button value="hybrid" :disabled="!index.has_sparse">
            混合检索
            <t-tooltip v-if="!index.has_sparse" content="当前索引未启用稀疏向量">
              <t-icon name="help-circle" size="14px" style="margin-left: 4px" />
            </t-tooltip>
          </t-radio-button>
        </t-radio-group>
      </t-form-item>

      <t-form-item label="查询向量" name="query_vector">
        <t-textarea
          v-model="vectorInput"
          placeholder="输入向量 (逗号分隔的数字，例如: 0.1, 0.2, 0.3, ...)"
          :autosize="{ minRows: 3, maxRows: 5 }"
        />
        <div class="form-tip">
          或者
          <t-button
            variant="text"
            theme="primary"
            size="small"
            @click="generateRandomVector"
          >
            生成随机向量
          </t-button>
        </div>
      </t-form-item>

      <!-- 混合检索独有参数 -->
      <template v-if="searchMode === 'hybrid'">
        <t-form-item label="查询文本">
          <t-textarea
            v-model="queryText"
            placeholder="输入原始查询文本（用于 Reranker 精排）"
            :autosize="{ minRows: 2, maxRows: 3 }"
          />
          <div class="form-tip">Reranker 需要原始文本来计算语义相关度</div>
        </t-form-item>

        <t-form-item label="粗排数量">
          <t-input-number
            v-model="hybridParams.top_n"
            :min="5"
            :max="100"
            style="width: 200px"
          />
          <span class="form-tip" style="margin-left: 8px">RRF 粗排候选集大小 (top_n)</span>
        </t-form-item>

        <t-form-item label="Reranker">
          <t-switch v-model="hybridParams.enable_reranker" />
          <span class="form-tip" style="margin-left: 8px">
            {{ hybridParams.enable_reranker ? '启用精排重排序' : '跳过精排，直接使用 RRF 粗排结果' }}
          </span>
          <t-tag
            v-if="rerankerStatus !== null"
            :theme="rerankerStatus ? 'success' : 'warning'"
            variant="light"
            size="small"
            style="margin-left: 8px"
          >
            {{ rerankerStatus ? 'Reranker 可用' : 'Reranker 不可用' }}
          </t-tag>
        </t-form-item>
      </template>

      <t-form-item label="返回数量" name="top_k">
        <t-input-number
          v-model="searchData.top_k"
          :min="1"
          :max="100"
          style="width: 200px"
        />
      </t-form-item>

      <t-form-item label="保存结果" name="save_result">
        <t-switch v-model="searchData.save_result" />
        <span class="form-tip" style="margin-left: 8px">
          保存搜索结果到文件
        </span>
      </t-form-item>

      <t-form-item>
        <t-space>
          <t-button
            theme="primary"
            type="submit"
            :loading="loading || hybridLoading"
            :disabled="!isVectorValid"
          >
            <template #icon><search-icon /></template>
            {{ searchMode === 'hybrid' ? '混合检索' : '搜索' }}
          </t-button>
          <t-button variant="outline" @click="handleReset">
            重置
          </t-button>
        </t-space>
      </t-form-item>
    </t-form>

    <!-- 搜索结果 -->
    <t-divider v-if="displayResults" />
    
    <div v-if="displayResults" class="search-results">
      <div class="result-header">
        <h3>搜索结果</h3>
        <t-space>
          <!-- 检索模式标签 -->
          <t-tag v-if="displayResults.search_mode" :theme="displayResults.search_mode === 'hybrid' ? 'warning' : 'primary'" variant="light">
            {{ displayResults.search_mode === 'hybrid' ? '混合检索' : '纯稠密检索' }}
          </t-tag>
          <t-tag theme="primary">
            找到 {{ displayResultCount }} 个结果
          </t-tag>
          <t-tag theme="success">
            耗时 {{ displayQueryTime }}ms
          </t-tag>
          <!-- Reranker 状态标签 -->
          <t-tag v-if="displayResults.reranker_available !== undefined" :theme="displayResults.reranker_available ? 'success' : 'default'" variant="light">
            {{ displayResults.reranker_available ? 'Reranker ✓' : 'Reranker ✗' }}
          </t-tag>
        </t-space>
      </div>

      <!-- 混合检索耗时详情 -->
      <div v-if="displayResults.rrf_time_ms || displayResults.reranker_time_ms" class="timing-detail">
        <t-space size="large">
          <span v-if="displayResults.rrf_time_ms" class="timing-item">
            <span class="timing-label">RRF 粗排:</span>
            <span class="timing-value">{{ displayResults.rrf_time_ms }}ms</span>
          </span>
          <span v-if="displayResults.reranker_time_ms" class="timing-item">
            <span class="timing-label">Reranker 精排:</span>
            <span class="timing-value">{{ displayResults.reranker_time_ms }}ms</span>
          </span>
          <span v-if="displayResults.total_candidates" class="timing-item">
            <span class="timing-label">候选集:</span>
            <span class="timing-value">{{ displayResults.total_candidates }} 条</span>
          </span>
        </t-space>
      </div>

      <t-table
        :data="displayResultData"
        :columns="displayColumns"
        row-key="vector_id"
        size="small"
        stripe
        :max-height="400"
      >
        <template #score="{ row }">
          <t-progress
            :percentage="(row.score * 100).toFixed(2)"
            :label="row.score.toFixed(4)"
            theme="success"
          />
        </template>

        <template #final_score="{ row }">
          <span class="score-value">{{ (row.final_score || 0).toFixed(4) }}</span>
        </template>

        <template #rrf_score="{ row }">
          <span class="score-value">{{ (row.rrf_score || 0).toFixed(4) }}</span>
        </template>

        <template #reranker_score="{ row }">
          <span v-if="row.reranker_score != null" class="score-value">
            {{ row.reranker_score.toFixed(4) }}
          </span>
          <span v-else class="score-na">N/A</span>
        </template>

        <template #search_mode_badge="{ row }">
          <t-tag
            :theme="row.search_mode === 'hybrid' ? 'warning' : 'primary'"
            variant="light"
            size="small"
          >
            {{ row.search_mode === 'hybrid' ? '混合' : '稠密' }}
          </t-tag>
        </template>

        <template #metadata="{ row }">
          <t-popup
            placement="left"
            :content="JSON.stringify(row.metadata, null, 2)"
          >
            <t-button variant="text" size="small">
              查看详情
            </t-button>
          </t-popup>
        </template>
      </t-table>
    </div>
  </t-card>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue';
import { SearchIcon } from 'tdesign-icons-vue-next';
import { storeToRefs } from 'pinia';
import { useVectorIndexStore } from '../../stores/vectorIndexStore';

const props = defineProps({
  index: {
    type: Object,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['search', 'hybrid-search']);

const vectorIndexStore = useVectorIndexStore();
const { searchResults, hybridSearchResults } = storeToRefs(vectorIndexStore);

const formRef = ref(null);
const vectorInput = ref('');
const searchMode = ref('dense');
const queryText = ref('');
const rerankerStatus = ref(null);

const searchData = reactive({
  query_vector: [],
  top_k: 10,
  save_result: false
});

const hybridParams = reactive({
  top_n: 20,
  enable_reranker: true,
  rrf_k: 60
});

// 混合检索加载状态
const hybridLoading = computed(() => vectorIndexStore.loading.hybridSearch);

// 纯稠密模式的列
const denseResultColumns = [
  {
    colKey: 'vector_id',
    title: '向量 ID',
    width: 300,
    ellipsis: true
  },
  {
    colKey: 'score',
    title: '相似度',
    width: 200,
    cell: 'score'
  },
  {
    colKey: 'metadata',
    title: '元数据',
    width: 150,
    cell: 'metadata'
  }
];

// 混合检索模式的列
const hybridResultColumns = [
  {
    colKey: 'vector_id',
    title: '向量 ID',
    width: 180,
    ellipsis: true
  },
  {
    colKey: 'search_mode_badge',
    title: '模式',
    width: 80,
    cell: 'search_mode_badge'
  },
  {
    colKey: 'rrf_score',
    title: 'RRF 分数',
    width: 110,
    cell: 'rrf_score'
  },
  {
    colKey: 'reranker_score',
    title: 'Reranker 分数',
    width: 130,
    cell: 'reranker_score'
  },
  {
    colKey: 'final_score',
    title: '最终分数',
    width: 110,
    cell: 'final_score'
  },
  {
    colKey: 'metadata',
    title: '元数据',
    width: 100,
    cell: 'metadata'
  }
];

// 根据模式选择显示列
const displayColumns = computed(() => {
  if (searchMode.value === 'hybrid' && hybridSearchResults.value) {
    return hybridResultColumns;
  }
  return denseResultColumns;
});

// 统一的显示结果
const displayResults = computed(() => {
  if (searchMode.value === 'hybrid' && hybridSearchResults.value) {
    return hybridSearchResults.value;
  }
  return searchResults.value;
});

const displayResultData = computed(() => {
  if (searchMode.value === 'hybrid' && hybridSearchResults.value) {
    return hybridSearchResults.value.data || [];
  }
  return searchResults.value?.results || [];
});

const displayResultCount = computed(() => {
  if (searchMode.value === 'hybrid' && hybridSearchResults.value) {
    return (hybridSearchResults.value.data || []).length;
  }
  return searchResults.value?.results_count || 0;
});

const displayQueryTime = computed(() => {
  if (searchMode.value === 'hybrid' && hybridSearchResults.value) {
    return hybridSearchResults.value.query_time_ms || 0;
  }
  return searchResults.value?.search_time_ms?.toFixed(2) || 0;
});

const isVectorValid = computed(() => {
  if (!vectorInput.value) return false;
  
  try {
    const vector = parseVector(vectorInput.value);
    return vector.length === props.index.dimension;
  } catch {
    return false;
  }
});

const parseVector = (input) => {
  const parts = input.split(',').map(s => s.trim()).filter(s => s);
  return parts.map(p => parseFloat(p));
};

const generateRandomVector = () => {
  const vector = Array.from(
    { length: props.index.dimension },
    () => (Math.random() - 0.5).toFixed(4)
  );
  vectorInput.value = vector.join(', ');
};

const handleSearch = async (e) => {
  e?.preventDefault();
  
  if (!isVectorValid.value) {
    return;
  }

  const vector = parseVector(vectorInput.value);

  if (searchMode.value === 'hybrid') {
    // 混合检索
    const hybridSearchData = {
      collection_name: props.index.index_name,
      query_text: queryText.value || '',
      query_dense_vector: vector,
      query_sparse_vector: null, // 由后端自动处理
      top_n: hybridParams.top_n,
      top_k: searchData.top_k,
      enable_reranker: hybridParams.enable_reranker,
      rrf_k: hybridParams.rrf_k
    };
    emit('hybrid-search', hybridSearchData);
  } else {
    // 纯稠密检索
    searchData.query_vector = vector;
    emit('search', { ...searchData });
  }
};

const handleReset = () => {
  vectorInput.value = '';
  queryText.value = '';
  searchData.query_vector = [];
  searchData.top_k = 10;
  searchData.save_result = false;
  hybridParams.top_n = 20;
  hybridParams.enable_reranker = true;
  hybridParams.rrf_k = 60;
  vectorIndexStore.clearSearchResults();
  vectorIndexStore.clearHybridSearchResults();
};

// 检查 Reranker 状态
const checkReranker = async () => {
  try {
    const health = await vectorIndexStore.checkRerankerHealth();
    rerankerStatus.value = health?.available || false;
  } catch {
    rerankerStatus.value = false;
  }
};

// 当索引变化时重置
watch(() => props.index, () => {
  handleReset();
  // 如果索引支持稀疏向量，自动切换到混合模式
  if (props.index?.has_sparse) {
    searchMode.value = 'hybrid';
  } else {
    searchMode.value = 'dense';
  }
});

// 切换到混合模式时检查 Reranker
watch(searchMode, (newMode) => {
  if (newMode === 'hybrid') {
    checkReranker();
  }
});

onMounted(() => {
  if (props.index?.has_sparse) {
    searchMode.value = 'hybrid';
    checkReranker();
  }
});
</script>

<style scoped>
.form-tip {
  margin-top: 4px;
  font-size: 12px;
  color: var(--td-text-color-placeholder);
}

.search-results {
  margin-top: 24px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.result-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.timing-detail {
  margin-bottom: 16px;
  padding: 8px 12px;
  background: var(--td-bg-color-container-hover);
  border-radius: 6px;
  font-size: 13px;
}

.timing-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.timing-label {
  color: var(--td-text-color-secondary);
}

.timing-value {
  font-weight: 500;
  font-family: monospace;
  color: var(--td-brand-color);
}

.score-value {
  font-family: monospace;
  font-weight: 500;
}

.score-na {
  font-size: 12px;
  color: var(--td-text-color-placeholder);
}

:deep(.t-progress) {
  width: 100%;
}
</style>
