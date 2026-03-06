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
        <t-button
          theme="primary"
          variant="outline"
          size="small"
          @click="$emit('retry')"
        >
          <template #icon>
            <RotateCw :size="14" />
          </template>
          重试
        </t-button>
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
import { MessageSquare, Clock, Hash, AlertCircle, Sparkles, RotateCw } from 'lucide-vue-next'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

defineEmits(['retry'])

const md = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: false,
  typographer: true,
})

const defaultLinkRender = md.renderer.rules.link_open ||
  function (tokens, idx, options, _env, self) {
    return self.renderToken(tokens, idx, options)
  }

md.renderer.rules.link_open = function (tokens, idx, options, env, self) {
  tokens[idx].attrSet('target', '_blank')
  tokens[idx].attrSet('rel', 'noopener noreferrer')
  return defaultLinkRender(tokens, idx, options, env, self)
}

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

const renderedContent = computed(() => {
  if (!props.content) return ''

  const raw = md.render(props.content)

  const clean = DOMPurify.sanitize(raw, {
    ALLOWED_TAGS: [
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'p', 'br', 'hr',
      'ul', 'ol', 'li',
      'blockquote',
      'pre', 'code',
      'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'strong', 'em', 'del', 's',
      'a', 'img',
      'span', 'div', 'sup', 'sub',
    ],
    ALLOWED_ATTR: [
      'href', 'target', 'rel', 'src', 'alt', 'title',
      'class', 'id',
    ],
  })

  return clean.replace(
    /(\S)\[(\d+)\]/g,
    '$1<span class="source-ref">[$2]</span>'
  )
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
  line-height: 1.8;
  color: #374151;
  font-size: 14px;
  word-break: break-word;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  color: #1f2937;
  font-weight: 600;
  margin: 20px 0 10px;
  line-height: 1.4;
}

.markdown-content :deep(h1) { font-size: 1.5em; }
.markdown-content :deep(h2) { font-size: 1.3em; }
.markdown-content :deep(h3) { font-size: 1.15em; }
.markdown-content :deep(h4) { font-size: 1.05em; }

.markdown-content :deep(p) {
  margin: 8px 0;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  padding-left: 24px;
  margin: 8px 0;
}

.markdown-content :deep(li) {
  margin: 4px 0;
}

.markdown-content :deep(li > ul),
.markdown-content :deep(li > ol) {
  margin: 2px 0;
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid #6366f1;
  padding: 8px 16px;
  margin: 12px 0;
  background: #f9fafb;
  color: #4b5563;
  border-radius: 0 8px 8px 0;
}

.markdown-content :deep(blockquote p) {
  margin: 4px 0;
}

.markdown-content :deep(hr) {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 16px 0;
}

.markdown-content :deep(code) {
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
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
  font-size: 13px;
  line-height: 1.6;
}

.markdown-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 13px;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 8px 12px;
  text-align: left;
}

.markdown-content :deep(th) {
  background: #f9fafb;
  font-weight: 600;
  color: #374151;
}

.markdown-content :deep(tr:hover td) {
  background: #f9fafb;
}

.markdown-content :deep(a) {
  color: #6366f1;
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 0.2s;
}

.markdown-content :deep(a:hover) {
  border-bottom-color: #6366f1;
}

.markdown-content :deep(img) {
  max-width: 100%;
  border-radius: 8px;
  margin: 8px 0;
}

.markdown-content :deep(strong) {
  font-weight: 600;
  color: #1f2937;
}

.markdown-content :deep(del),
.markdown-content :deep(s) {
  color: #9ca3af;
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
