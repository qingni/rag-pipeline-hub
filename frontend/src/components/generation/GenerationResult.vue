<template>
  <div class="generation-result">
    <div class="result-header">
      <h4 class="result-title">
        <MessageSquare :size="18" />
        生成结果
      </h4>
      <div class="result-meta" v-if="tokenUsage || processingTime">
        <span v-if="processingTime" class="meta-item">
          <Clock :size="14" />
          {{ formatTime(processingTime) }}
        </span>
        <span v-if="tokenUsage" class="meta-item">
          <Hash :size="14" />
          {{ tokenUsage.total_tokens }} tokens
        </span>
      </div>
    </div>
    
    <div class="result-content">
      <!-- 加载状态 -->
      <div v-if="loading && !content" class="loading-state">
        <t-loading size="small" />
        <span>正在生成回答...</span>
      </div>
      
      <!-- 错误状态 -->
      <div v-else-if="error" class="error-state">
        <AlertCircle :size="20" />
        <span>{{ error }}</span>
      </div>
      
      <!-- 空状态 -->
      <div v-else-if="!content" class="empty-state">
        <Sparkles :size="32" />
        <p>输入问题并点击"生成回答"开始</p>
      </div>
      
      <!-- 内容展示 -->
      <div v-else class="content-area">
        <div class="markdown-content" v-html="renderedContent"></div>
        <div v-if="loading" class="streaming-indicator">
          <span class="cursor">▋</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { MessageSquare, Clock, Hash, AlertCircle, Sparkles } from 'lucide-vue-next'

const props = defineProps({
  content: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: null
  },
  tokenUsage: {
    type: Object,
    default: null
  },
  processingTime: {
    type: Number,
    default: null
  }
})

// 简单的 Markdown 渲染和引用标记高亮
const renderedContent = computed(() => {
  if (!props.content) return ''
  
  let html = props.content
    // 转义 HTML
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // 代码块
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
    // 行内代码
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // 粗体
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // 斜体
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    // 引用标记高亮 [1], [2], etc.
    .replace(/\[(\d+)\]/g, '<span class="source-ref">[$1]</span>')
    // 换行
    .replace(/\n/g, '<br>')
  
  return html
})

function formatTime(ms) {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`
  }
  return `${(ms / 1000).toFixed(1)}s`
}
</script>

<style scoped>
.generation-result {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  height: 400px;
  min-height: 200px;
  max-height: 400px;
  position: relative;
  z-index: 1;
  flex-shrink: 0;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.result-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 500;
  color: #1f2937;
  margin: 0;
}

.result-meta {
  display: flex;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #6b7280;
}

.result-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.loading-state,
.error-state,
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #6b7280;
}

.error-state {
  color: #ef4444;
}

.empty-state {
  color: #9ca3af;
}

.content-area {
  flex: 1;
  overflow-y: auto;
}

.markdown-content {
  line-height: 1.7;
  color: #374151;
}

.markdown-content :deep(code) {
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 0.9em;
}

.markdown-content :deep(pre) {
  background: #1f2937;
  color: #e5e7eb;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
}

.markdown-content :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

.markdown-content :deep(.source-ref) {
  display: inline-block;
  background: #eef2ff;
  color: #6366f1;
  padding: 0 4px;
  border-radius: 4px;
  font-weight: 500;
  font-size: 0.85em;
  cursor: pointer;
  transition: background-color 0.2s;
}

.markdown-content :deep(.source-ref:hover) {
  background: #e0e7ff;
}

.streaming-indicator {
  display: inline;
}

.cursor {
  animation: blink 1s infinite;
  color: #6366f1;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>
