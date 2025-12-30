<template>
  <div class="source-reference">
    <h4 class="section-title">
      <FileText :size="18" />
      引用来源
      <span class="source-count" v-if="displaySources.length > 0">({{ displaySources.length }})</span>
    </h4>
    
    <div class="source-list">
      <div 
        v-for="source in displaySources" 
        :key="source.index"
        class="source-item"
      >
        <div class="source-header">
          <span class="source-index">[{{ source.index }}]</span>
          <div class="source-info">
            <span class="source-file">{{ source.source_file }}</span>
            <span class="source-similarity">
              相似度: {{ formatSimilarity(source.similarity) }}
            </span>
          </div>
        </div>
        <div class="source-content" v-if="source.content">
          {{ truncateContent(source.content) }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { FileText } from 'lucide-vue-next'

const props = defineProps({
  sources: {
    type: Array,
    default: () => []
  }
})

// 只展示 Top 3
const displaySources = computed(() => {
  return props.sources.slice(0, 3)
})

function formatSimilarity(value) {
  return (value * 100).toFixed(1) + '%'
}

function truncateContent(content, maxLength = 200) {
  if (!content) return ''
  if (content.length <= maxLength) return content
  return content.substring(0, maxLength) + '...'
}
</script>

<style scoped>
.source-reference {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  position: relative;
  z-index: 1;
  flex-shrink: 0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 500;
  color: #1f2937;
  margin: 0 0 12px 0;
}

.source-count {
  font-size: 14px;
  font-weight: 400;
  color: #6b7280;
}

.source-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.source-item {
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.source-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.source-index {
  font-weight: 600;
  color: #6366f1;
  min-width: 32px;
}

.source-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.source-file {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.source-similarity {
  font-size: 12px;
  color: #6b7280;
}

.source-content {
  font-size: 13px;
  line-height: 1.6;
  color: #4b5563;
  background: white;
  padding: 10px 12px;
  border-radius: 6px;
  border-left: 3px solid #6366f1;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
