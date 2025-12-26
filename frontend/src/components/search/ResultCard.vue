<template>
  <t-card class="result-card" :bordered="true" hover-shadow>
    <template #header>
      <div class="card-header">
        <div class="rank-badge">
          <span class="rank-number">#{{ result.rank }}</span>
        </div>
        <div class="score-info">
          <t-tag 
            :theme="scoreTheme" 
            variant="light"
            size="small"
          >
            相似度: {{ result.similarity_percent }}
          </t-tag>
        </div>
      </div>
    </template>
    
    <div class="card-content">
      <!-- 文本内容区域 -->
      <div class="text-content-wrapper">
        <p v-if="result.text_summary" class="text-summary">{{ result.text_summary }}</p>
        <p v-else class="text-empty">暂无文本内容</p>
      </div>
      
      <!-- 元信息区域 -->
      <div class="meta-info">
        <div class="meta-item" :title="result.source_document">
          <file-icon class="meta-icon" />
          <span class="meta-label">文档:</span>
          <span class="meta-value">{{ formatDocumentName(result.source_document) }}</span>
        </div>
        <div v-if="result.source_index" class="meta-item" :title="result.source_index">
          <folder-icon class="meta-icon" />
          <span class="meta-label">索引:</span>
          <span class="meta-value">{{ formatIndexName(result.source_index) }}</span>
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
import { computed } from 'vue'
import { FileIcon, FolderIcon, LocationIcon, BrowseIcon } from 'tdesign-icons-vue-next'

const props = defineProps({
  result: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['view-detail'])

const scoreTheme = computed(() => {
  const score = props.result.similarity_score
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'primary'
  if (score >= 0.4) return 'warning'
  return 'default'
})

function formatDocumentName(name) {
  if (!name || name === '未知文档') return '未知文档'
  // 如果名称太长，截断显示
  if (name.length > 30) {
    return name.substring(0, 27) + '...'
  }
  return name
}

function formatIndexName(name) {
  if (!name) return ''
  // 如果名称太长，截断显示
  if (name.length > 40) {
    return name.substring(0, 37) + '...'
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
  gap: 0.25rem;
}

.rank-number {
  font-weight: 600;
  color: #666;
  font-size: 0.875rem;
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
