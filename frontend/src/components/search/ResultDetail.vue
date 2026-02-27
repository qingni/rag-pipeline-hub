<template>
  <t-dialog
    v-model:visible="localVisible"
    header="文档详情"
    :footer="false"
    width="700px"
    placement="center"
  >
    <div v-if="result" class="result-detail">
      <!-- 相似度和检索信息 -->
      <div class="detail-header">
        <!-- 🆕 检索模式标签 -->
        <t-tag 
          v-if="result.search_mode"
          :theme="result.search_mode === 'hybrid' ? 'primary' : 'default'"
          size="medium"
        >
          {{ result.search_mode === 'hybrid' ? '混合检索' : '纯稠密检索' }}
        </t-tag>
        <t-tag 
          :theme="scoreTheme" 
          size="medium"
        >
          相似度: {{ result.similarity_percent || formatPercent(result.similarity_score) }}
        </t-tag>
        <span class="rank-info">排名 #{{ result.rank }}</span>
      </div>
      
      <!-- 🆕 精排分数详情 -->
      <div v-if="result.reranker_score != null || result.rrf_score != null" class="score-detail">
        <div class="score-row" v-if="result.reranker_score != null">
          <span class="score-label">Reranker 精排分数:</span>
          <span class="score-value highlight">{{ result.reranker_score.toFixed(6) }}</span>
        </div>
        <div class="score-row" v-if="result.rrf_score != null">
          <span class="score-label">RRF 融合分数:</span>
          <span class="score-value">{{ result.rrf_score.toFixed(6) }}</span>
        </div>
        <div class="score-row" v-if="result.similarity_score != null">
          <span class="score-label">原始相似度分数:</span>
          <span class="score-value">{{ result.similarity_score.toFixed(6) }}</span>
        </div>
      </div>
      
      <!-- 来源信息 -->
      <div class="source-info">
        <!-- 🆕 来源 Collection -->
        <div v-if="result.source_collection" class="info-row">
          <span class="label">来源 Collection:</span>
          <span class="value">{{ result.source_collection }}</span>
        </div>
        <div class="info-row">
          <span class="label">来源文档:</span>
          <span class="value">{{ result.source_document }}</span>
        </div>
        <div v-if="result.source_index && !result.source_collection" class="info-row">
          <span class="label">来源索引:</span>
          <span class="value">{{ result.source_index }}</span>
        </div>
        <div v-if="result.chunk_position !== null" class="info-row">
          <span class="label">片段位置:</span>
          <span class="value">#{{ result.chunk_position }}</span>
        </div>
        <div v-if="result.chunk_id" class="info-row">
          <span class="label">片段ID:</span>
          <span class="value mono">{{ result.chunk_id }}</span>
        </div>
      </div>
      
      <!-- 完整内容 -->
      <div class="content-section">
        <h4 class="section-title">完整内容</h4>
        <div class="content-box">
          {{ result.text_content }}
        </div>
      </div>
      
      <!-- 元数据 -->
      <div v-if="hasMetadata" class="metadata-section">
        <h4 class="section-title">元数据</h4>
        <div class="metadata-box">
          <pre>{{ formattedMetadata }}</pre>
        </div>
      </div>
    </div>
  </t-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  result: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:visible'])

const localVisible = ref(props.visible)

watch(() => props.visible, (val) => {
  localVisible.value = val
})

watch(localVisible, (val) => {
  emit('update:visible', val)
})

const scoreTheme = computed(() => {
  if (!props.result) return 'default'
  const score = props.result.similarity_score
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'primary'
  if (score >= 0.4) return 'warning'
  return 'default'
})

const hasMetadata = computed(() => {
  if (!props.result?.metadata) return false
  return Object.keys(props.result.metadata).length > 0
})

const formattedMetadata = computed(() => {
  if (!props.result?.metadata) return ''
  return JSON.stringify(props.result.metadata, null, 2)
})

function formatPercent(score) {
  if (score == null) return '0%'
  return (score * 100).toFixed(1) + '%'
}
</script>

<style scoped>
.result-detail {
  padding: 0.5rem 0;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.rank-info {
  color: #666;
  font-size: 0.875rem;
}

/* 🆕 精排分数详情 */
.score-detail {
  background: #f0f7ff;
  padding: 0.75rem 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  border-left: 3px solid #0052d9;
}

.score-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.25rem 0;
}

.score-label {
  color: #666;
  font-size: 0.875rem;
}

.score-value {
  font-family: monospace;
  font-size: 0.875rem;
  color: #333;
}

.score-value.highlight {
  color: #0052d9;
  font-weight: 600;
}

.source-info {
  background: #f5f7fa;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
}

.info-row {
  display: flex;
  margin-bottom: 0.5rem;
}

.info-row:last-child {
  margin-bottom: 0;
}

.label {
  width: 120px;
  color: #666;
  font-size: 0.875rem;
  flex-shrink: 0;
}

.value {
  flex: 1;
  color: #333;
  font-size: 0.875rem;
}

.value.mono {
  font-family: monospace;
  font-size: 0.75rem;
  color: #666;
}

.section-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.75rem;
}

.content-box {
  background: #fafafa;
  border: 1px solid #e5e5e5;
  border-radius: 4px;
  padding: 1rem;
  line-height: 1.8;
  color: #333;
  max-height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.metadata-section {
  margin-top: 1.5rem;
}

.metadata-box {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 1rem;
  max-height: 200px;
  overflow-y: auto;
}

.metadata-box pre {
  margin: 0;
  font-size: 0.75rem;
  color: #666;
  white-space: pre-wrap;
}
</style>
