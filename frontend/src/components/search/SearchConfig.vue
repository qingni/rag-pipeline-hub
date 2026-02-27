<template>
  <div class="search-config">
    <!-- 检索状态简要指示条 -->
    <div class="search-status-bar">
      <t-tag :theme="searchModeTheme" variant="light" size="small">
        {{ searchModeText }}
      </t-tag>
      <t-tag 
        v-if="rerankerHealth"
        :theme="rerankerHealth.available ? 'success' : 'warning'" 
        variant="outline"
        size="small"
      >
        Reranker {{ rerankerHealth.available ? '✓' : '✗' }}
      </t-tag>
    </div>

    <!-- 目标 Collection -->
    <div class="config-section">
      <label class="config-label">目标 Collection</label>
      <t-select
        v-model="localConfig.selectedCollectionIds"
        :options="collectionOptions"
        :loading="isLoadingCollections"
        placeholder="选择 Collection（可多选，最多5个）"
        multiple
        clearable
        filterable
        :max="5"
        @change="handleCollectionChange"
      />
      <p class="config-hint">不选择则搜索所有可用 Collection</p>
    </div>

    <!-- 🆕 Reranker 参数（混合检索模式下显示） -->
    <div v-if="showRerankerConfig" class="config-section">
      <label class="config-label">Reranker 参数</label>
      <div class="reranker-params">
        <div class="param-row">
          <span class="param-label">候选集大小 (Top-N)</span>
          <t-input-number
            v-model="localConfig.rerankerTopN"
            :min="10"
            :max="100"
            size="small"
            theme="column"
            class="config-input-number"
            @change="handleConfigChange"
          />
        </div>
        <div class="param-row">
          <span class="param-label">最终返回数 (Top-K)</span>
          <t-input-number
            v-model="localConfig.topK"
            :min="1"
            :max="100"
            size="small"
            theme="column"
            class="config-input-number"
            @change="handleConfigChange"
          />
        </div>
      </div>
      <p class="config-hint">Top-N: Reranker 精排候选集大小；Top-K: 最终返回给用户的结果数量</p>
    </div>
    
    <!-- 返回数量 (Top K) — 非混合模式下显示 -->
    <div v-if="!showRerankerConfig" class="config-section">
      <div class="config-header">
        <label class="config-label">返回数量 (Top K)</label>
        <t-input-number
          v-model="localConfig.topK"
          :min="1"
          :max="100"
          size="small"
          theme="column"
          class="config-input-number"
          @change="handleConfigChange"
        />
      </div>
      <t-slider
        v-model="localConfig.topK"
        :min="1"
        :max="100"
        :step="1"
        :marks="topKMarks"
        :tooltip-props="{ placement: 'top' }"
        @change="handleConfigChange"
      />
    </div>
    
    <!-- 相似度阈值 -->
    <div class="config-section">
      <div class="config-header">
        <label class="config-label">相似度阈值</label>
        <t-input-number
          v-model="localConfig.threshold"
          :min="0"
          :max="1"
          :step="0.05"
          :decimal-places="2"
          size="small"
          theme="column"
          class="config-input-number"
          @change="handleConfigChange"
        />
      </div>
      <t-slider
        v-model="localConfig.threshold"
        :min="0"
        :max="1"
        :step="0.05"
        :marks="thresholdMarks"
        :tooltip-props="{ placement: 'top' }"
        @change="handleConfigChange"
      />
      <p class="config-hint">只返回相似度高于此值的结果</p>
    </div>
    
    <!-- 度量类型（只读显示） -->
    <div class="config-section">
      <label class="config-label">度量类型</label>
      <div class="metric-type-display">
        <t-tag 
          v-if="displayMetricType" 
          :theme="metricTypeTheme"
          variant="light"
        >
          {{ metricTypeLabel }}
        </t-tag>
        <span v-else class="metric-type-hint">选择 Collection 后自动显示</span>
      </div>
      <p class="config-hint">度量类型由 Collection 创建时确定，运行时不可切换</p>
    </div>
    
    <!-- 重置按钮 -->
    <div class="config-actions">
      <t-button
        variant="outline"
        size="small"
        block
        @click="handleReset"
      >
        重置为默认
      </t-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  config: {
    type: Object,
    default: () => ({
      selectedIndexIds: [],
      selectedCollectionIds: [],
      topK: 10,
      threshold: 0.5,
      metricType: 'cosine',
      rerankerTopN: 20,
      rerankerTopK: null,
    })
  },
  availableIndexes: {
    type: Array,
    default: () => []
  },
  availableCollections: {
    type: Array,
    default: () => []
  },
  isLoadingIndexes: {
    type: Boolean,
    default: false
  },
  isLoadingCollections: {
    type: Boolean,
    default: false
  },
  // 🆕 当前检索模式（运行时结果更新）
  searchMode: {
    type: String,
    default: 'auto'
  },
  // 🆕 Reranker 健康状态
  rerankerHealth: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:config', 'reset'])

const localConfig = ref({ ...props.config })

watch(() => props.config, (newVal) => {
  localConfig.value = { ...newVal }
}, { deep: true })

// 🆕 Collection 选项（按逻辑知识库聚合，含 has_sparse 标识）
const collectionOptions = computed(() => {
  return props.availableCollections.map(col => ({
    label: `${col.name} (${col.document_count || 0} 文档, ${col.vector_count} 向量)${col.has_sparse ? ' 🔀' : ''}`,
    value: col.id,
    title: col.has_sparse ? '支持混合检索（含稀疏向量）' : '仅支持纯稠密检索'
  }))
})

// 🆕 检索模式显示文本
const searchModeText = computed(() => {
  const modeMap = {
    hybrid: '混合检索',
    dense_only: '稠密检索',
    auto: '自动检测'
  }
  return modeMap[props.searchMode] || '自动检测'
})

// 🆕 检索模式主题色
const searchModeTheme = computed(() => {
  if (props.searchMode === 'hybrid') return 'primary'
  if (props.searchMode === 'dense_only') return 'default'
  return 'default'
})

// 🆕 是否显示 Reranker 配置
const showRerankerConfig = computed(() => {
  // 有选中含稀疏向量的 Collection，或已执行过混合检索
  const hasSelectedSparse = props.availableCollections.some(
    col => localConfig.value.selectedCollectionIds.includes(col.id) && col.has_sparse
  )
  return hasSelectedSparse || props.searchMode === 'hybrid' || 
    (localConfig.value.selectedCollectionIds.length === 0 && props.availableCollections.some(c => c.has_sparse))
})

// 度量类型映射
const metricTypeMap = {
  cosine: { label: '余弦相似度 (Cosine)', theme: 'primary' },
  euclidean: { label: '欧氏距离 (Euclidean)', theme: 'warning' },
  dot_product: { label: '点积 (Dot Product)', theme: 'success' }
}

// 获取选中 Collection 的度量类型
const selectedMetricTypes = computed(() => {
  const collections = localConfig.value.selectedCollectionIds.length > 0
    ? props.availableCollections.filter(c => localConfig.value.selectedCollectionIds.includes(c.id))
    : props.availableCollections
  
  if (collections.length === 0) return []
  return [...new Set(collections.map(c => c.metric_type || 'cosine'))]
})

const displayMetricType = computed(() => {
  const types = selectedMetricTypes.value
  if (types.length === 0) return null
  if (types.length === 1) return types[0]
  return 'mixed'
})

const metricTypeLabel = computed(() => {
  const type = displayMetricType.value
  if (!type) return ''
  if (type === 'mixed') return '混合（多种度量类型）'
  return metricTypeMap[type]?.label || type
})

const metricTypeTheme = computed(() => {
  const type = displayMetricType.value
  if (!type || type === 'mixed') return 'default'
  return metricTypeMap[type]?.theme || 'default'
})

const topKMarks = { 1: '1', 50: '50', 100: '100' }
const thresholdMarks = { 0: '0', 0.5: '0.5', 1: '1' }

function handleCollectionChange() {
  // Collection 变更时，同步到 selectedIndexIds（向后兼容）
  localConfig.value.selectedIndexIds = [...localConfig.value.selectedCollectionIds]
  const types = selectedMetricTypes.value
  if (types.length === 1) {
    localConfig.value.metricType = types[0]
  }
  handleConfigChange()
}

function handleConfigChange() {
  emit('update:config', { ...localConfig.value })
}

function handleReset() {
  localConfig.value = {
    selectedIndexIds: [],
    selectedCollectionIds: [],
    topK: 10,
    threshold: 0.5,
    metricType: 'cosine',
    rerankerTopN: 20,
    rerankerTopK: null,
  }
  emit('reset')
  emit('update:config', { ...localConfig.value })
}
</script>

<style scoped>
.search-config {
  padding: 0.5rem 0;
}

.config-section {
  margin-bottom: 1.5rem;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.config-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #333;
  margin-bottom: 0.5rem;
}

.config-header .config-label {
  margin-bottom: 0;
}

.config-input-number {
  width: 90px;
}

.config-hint {
  font-size: 0.75rem;
  color: #999;
  margin-top: 0.5rem;
}

.config-actions {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e5e5;
}

/* 检索状态简要指示条 */
.search-status-bar {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 1rem;
  padding: 0.4rem 0;
}

/* 🆕 Reranker 参数 */
.reranker-params {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.param-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.param-label {
  font-size: 0.8rem;
  color: #666;
}

/* 度量类型显示样式 */
.metric-type-display {
  margin-top: 0.5rem;
  min-height: 32px;
  display: flex;
  align-items: center;
}

.metric-type-hint {
  font-size: 0.875rem;
  color: #999;
  font-style: italic;
}

/* 滑块样式优化 */
:deep(.t-slider) {
  margin: 0.5rem 0;
}

:deep(.t-slider__marks-text) {
  font-size: 0.75rem;
  color: #999;
}

:deep(.t-input-number.t-size-s) {
  height: 28px;
}

:deep(.t-input-number .t-input) {
  text-align: center;
}
</style>
