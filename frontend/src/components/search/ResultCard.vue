<template>
  <t-card class="result-card" :bordered="true" hover-shadow>
    <template #header>
      <div class="card-header">
        <div class="rank-badge">
          <span class="rank-number">#{{ result.rank }}</span>
          <!-- 🆕 检索模式标签 -->
          <t-tag 
            v-if="result.search_mode"
            :theme="searchModeTheme" 
            variant="light"
            size="small"
          >
            {{ searchModeLabel }}
          </t-tag>
        </div>
        <div class="score-info">
          <!-- 🆕 优先显示 reranker_score，否则 rrf_score，否则 similarity -->
          <t-tag 
            v-if="result.reranker_score != null"
            theme="success" 
            variant="light"
            size="small"
          >
            精排: {{ formatScore(result.reranker_score) }}
          </t-tag>
          <t-tag 
            v-if="result.rrf_score != null"
            theme="primary" 
            variant="light"
            size="small"
          >
            RRF: {{ formatScore(result.rrf_score) }}
          </t-tag>
          <t-tag 
            :theme="scoreTheme" 
            variant="light"
            size="small"
          >
            相似度: {{ result.similarity_percent || formatPercent(result.similarity_score) }}
          </t-tag>
        </div>
      </div>
    </template>
    
    <div class="card-content">
      <!-- 文本内容区域 -->
      <div class="text-content-wrapper">
        <p v-if="displayText" class="text-summary">{{ displayText }}</p>
        <p v-else class="text-empty">暂无文本内容</p>
        <!-- 🆕 展开/收起完整内容 -->
        <t-button
          v-if="hasFullContent && isCollapsed"
          variant="text"
          theme="primary"
          size="small"
          @click="isCollapsed = false"
        >
          展开全文
        </t-button>
        <t-button
          v-if="hasFullContent && !isCollapsed"
          variant="text"
          theme="default"
          size="small"
          @click="isCollapsed = true"
        >
          收起
        </t-button>
      </div>
      
      <!-- 元信息区域 -->
      <div class="meta-info">
        <!-- 🆕 来源 Collection -->
        <div v-if="result.source_collection" class="meta-item" :title="result.source_collection">
          <folder-icon class="meta-icon" />
          <span class="meta-label">Collection:</span>
          <span class="meta-value">{{ formatName(result.source_collection, 40) }}</span>
        </div>
        <div class="meta-item" :title="result.source_document">
          <file-icon class="meta-icon" />
          <span class="meta-label">文档:</span>
          <span class="meta-value">{{ formatName(result.source_document || '未知文档', 30) }}</span>
        </div>
        <div v-if="result.source_index && !result.source_collection" class="meta-item" :title="result.source_index">
          <folder-icon class="meta-icon" />
          <span class="meta-label">索引:</span>
          <span class="meta-value">{{ formatName(result.source_index, 40) }}</span>
        </div>
        <div v-if="result.chunk_position !== null && result.chunk_position !== undefined" class="meta-item">
          <location-icon class="meta-icon" />
          <span class="meta-label">片段:</span>
          <span class="meta-value">#{{ result.chunk_position }}</span>
        </div>
      </div>
    </div>
    
    <template #footer>
      <div class="card-footer">
        <t-button 
          variant="text" 
          theme="primary"
          size="small"
          @click="handleViewDetail"
        >
          <template #icon>
            <browse-icon />
          </template>
          查看详情
        </t-button>
      </div>
    </template>
  </t-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { FileIcon, FolderIcon, LocationIcon, BrowseIcon } from 'tdesign-icons-vue-next'

const props = defineProps({
  result: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['view-detail'])

const isCollapsed = ref(true)

const scoreTheme = computed(() => {
  const score = props.result.similarity_score
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'primary'
  if (score >= 0.4) return 'warning'
  return 'default'
})

// 🆕 检索模式主题色
const searchModeTheme = computed(() => {
  return props.result.search_mode === 'hybrid' ? 'primary' : 'default'
})

// 🆕 检索模式标签
const searchModeLabel = computed(() => {
  return props.result.search_mode === 'hybrid' ? '混合' : '稠密'
})

// 🆕 是否有完整内容（用于展开/收起）
const hasFullContent = computed(() => {
  const full = props.result.text_content || ''
  const summary = props.result.text_summary || ''
  return full.length > 200 && summary && full !== summary
})

// 🆕 展示文本：根据收起状态显示摘要或完整内容
const displayText = computed(() => {
  if (!isCollapsed.value && props.result.text_content) {
    return props.result.text_content
  }
  return props.result.text_summary || props.result.text_content || ''
})

function formatScore(score) {
  if (score == null) return ''
  return score.toFixed(4)
}

function formatPercent(score) {
  if (score == null) return '0%'
  return (score * 100).toFixed(1) + '%'
}

function formatName(name, maxLen = 30) {
  if (!name) return ''
  if (name.length > maxLen) {
    return name.substring(0, maxLen - 3) + '...'
  }
  return name
}

function handleViewDetail() {
  emit('view-detail', props.result)
}
</script>

<style scoped>
.result-card {
  margin-bottom: 1rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rank-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.rank-number {
  font-weight: 600;
  color: #666;
  font-size: 0.875rem;
}

.score-info {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.card-content {
  padding: 0.5rem 0;
}

.text-content-wrapper {
  background-color: #f8f9fa;
  border-radius: 6px;
  padding: 12px 16px;
  margin-bottom: 1rem;
  border-left: 3px solid #0052d9;
}

.text-summary {
  color: #333;
  line-height: 1.7;
  margin: 0;
  font-size: 0.9rem;
  word-break: break-word;
}

.text-empty {
  color: #999;
  font-style: italic;
  margin: 0;
}

.meta-info {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  padding-top: 0.5rem;
  border-top: 1px solid #eee;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.8rem;
  color: #666;
  max-width: 100%;
}

.meta-icon {
  font-size: 0.9rem;
  color: #0052d9;
  flex-shrink: 0;
}

.meta-label {
  color: #999;
  flex-shrink: 0;
}

.meta-value {
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-footer {
  display: flex;
  justify-content: flex-end;
}
</style>
