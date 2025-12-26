<template>
  <div class="search-config">
    <!-- 目标索引 -->
    <div class="config-section">
      <label class="config-label">目标索引</label>
      <t-select
        v-model="localConfig.selectedIndexIds"
        :options="indexOptions"
        :loading="isLoadingIndexes"
        placeholder="选择索引（可多选）"
        multiple
        clearable
        filterable
        @change="handleIndexChange"
      />
      <p class="config-hint">不选择则搜索所有可用索引</p>
    </div>
    
    <!-- 返回数量 (Top K) -->
    <div class="config-section">
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
        <span v-else class="metric-type-hint">选择索引后自动显示</span>
      </div>
      <p class="config-hint">度量类型由索引创建时确定，搜索时自动使用索引的度量类型</p>
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
      topK: 10,
      threshold: 0.5,
      metricType: 'cosine'
    })
  },
  availableIndexes: {
    type: Array,
    default: () => []
  },
  isLoadingIndexes: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:config', 'reset'])

const localConfig = ref({ ...props.config })

watch(() => props.config, (newVal) => {
  localConfig.value = { ...newVal }
}, { deep: true })

const indexOptions = computed(() => {
  return props.availableIndexes.map(idx => ({
    label: `${idx.name} (${idx.vector_count} 向量)`,
    value: idx.id
  }))
})

// 度量类型映射
const metricTypeMap = {
  cosine: { label: '余弦相似度 (Cosine)', theme: 'primary' },
  euclidean: { label: '欧氏距离 (Euclidean)', theme: 'warning' },
  dot_product: { label: '点积 (Dot Product)', theme: 'success' }
}

// 获取选中索引的度量类型
const selectedIndexMetricTypes = computed(() => {
  if (localConfig.value.selectedIndexIds.length === 0) {
    // 未选择索引时，显示所有索引的度量类型（如果都一样）
    if (props.availableIndexes.length === 0) return []
    const types = [...new Set(props.availableIndexes.map(idx => idx.metric_type || 'cosine'))]
    return types
  }
  
  // 获取选中索引的度量类型
  const types = props.availableIndexes
    .filter(idx => localConfig.value.selectedIndexIds.includes(idx.id))
    .map(idx => idx.metric_type || 'cosine')
  
  return [...new Set(types)]
})

// 显示的度量类型
const displayMetricType = computed(() => {
  const types = selectedIndexMetricTypes.value
  if (types.length === 0) return null
  if (types.length === 1) return types[0]
  return 'mixed' // 多个不同的度量类型
})

// 度量类型标签
const metricTypeLabel = computed(() => {
  const type = displayMetricType.value
  if (!type) return ''
  if (type === 'mixed') return '混合（多种度量类型）'
  return metricTypeMap[type]?.label || type
})

// 度量类型主题色
const metricTypeTheme = computed(() => {
  const type = displayMetricType.value
  if (!type || type === 'mixed') return 'default'
  return metricTypeMap[type]?.theme || 'default'
})

const topKMarks = {
  1: '1',
  50: '50',
  100: '100'
}

const thresholdMarks = {
  0: '0',
  0.5: '0.5',
  1: '1'
}

function handleIndexChange() {
  // 索引变更时，自动更新 metricType（用于历史记录保存）
  const types = selectedIndexMetricTypes.value
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
    topK: 10,
    threshold: 0.5,
    metricType: 'cosine'
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

/* 输入框数字样式 */
:deep(.t-input-number.t-size-s) {
  height: 28px;
}

:deep(.t-input-number .t-input) {
  text-align: center;
}
</style>
