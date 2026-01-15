<template>
  <div class="document-preview">
    <div v-if="loading" class="text-center py-8">
      <div class="spinner mx-auto mb-2"></div>
      <p class="text-gray-600">加载预览...</p>
    </div>
    
    <!-- 文档尚未加载 -->
    <div v-else-if="previewStatus === 'not_loaded'" class="status-card not-loaded">
      <t-icon name="file-unknown" size="48px" class="status-icon" />
      <p class="status-message">{{ statusMessage }}</p>
    </div>
    
    <!-- 文档正在加载中 -->
    <div v-else-if="previewStatus === 'processing'" class="status-card processing">
      <t-icon name="loading" size="48px" class="status-icon spinning" />
      <p class="status-message">{{ statusMessage }}</p>
    </div>
    
    <!-- 文档加载失败 -->
    <div v-else-if="previewStatus === 'error'" class="status-card error">
      <t-icon name="error-circle" size="48px" class="status-icon" />
      <p class="status-message">{{ statusMessage }}</p>
    </div>
    
    <!-- 正常预览 -->
    <div v-else-if="previewText" class="card">
      <div class="preview-header">
        <h4 class="font-semibold">文档预览 (共{{ pageCount }}页)</h4>
        <t-button 
          variant="text" 
          size="small" 
          @click="isExpanded = !isExpanded"
        >
          {{ isExpanded ? '收起' : '展开全部' }}
          <t-icon :name="isExpanded ? 'chevron-up' : 'chevron-down'" size="16px" />
        </t-button>
      </div>
      <!-- 如果是 Markdown 格式（包含图片或标题），渲染为 HTML -->
      <div 
        v-if="isMarkdown" 
        class="preview-content markdown-body text-sm text-gray-700" 
        :class="{ expanded: isExpanded }"
        v-html="renderedMarkdown"
      ></div>
      <!-- 否则显示纯文本 -->
      <div 
        v-else 
        class="preview-content whitespace-pre-wrap text-sm text-gray-700"
        :class="{ expanded: isExpanded }"
      >
        {{ previewText }}
      </div>
    </div>
    
    <div v-else class="status-card not-loaded">
      <t-icon name="file-unknown" size="48px" class="status-icon" />
      <p class="status-message">暂无预览内容</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { marked } from 'marked'
import { useDocumentStore } from '../../stores/document'

const props = defineProps({
  documentId: {
    type: String,
    default: null
  },
  pages: {
    type: Number,
    default: 3
  }
})

const documentStore = useDocumentStore()

const loading = ref(false)
const previewText = ref('')
const pageCount = ref(0)
const previewStatus = ref('')
const statusMessage = ref('')
const isExpanded = ref(false)

// 检测是否为 Markdown 格式（包含图片、标题等 Markdown 语法）
const isMarkdown = computed(() => {
  if (!previewText.value) return false
  // 检测常见的 Markdown 语法
  return /!\[.*?\]\(.*?\)|^#{1,6}\s|^\*\*|^\-\s|\|.*\|/m.test(previewText.value)
})

// 渲染 Markdown 为 HTML
const renderedMarkdown = computed(() => {
  if (!previewText.value) return ''
  try {
    return marked(previewText.value)
  } catch (e) {
    console.error('Markdown render error:', e)
    return previewText.value
  }
})

watch(() => props.documentId, async (newId) => {
  if (newId) {
    await loadPreview()
  } else {
    // 清空状态
    previewText.value = ''
    pageCount.value = 0
    previewStatus.value = ''
    statusMessage.value = ''
  }
}, { immediate: true })

async function loadPreview() {
  if (!props.documentId) return
  
  loading.value = true
  previewStatus.value = ''
  statusMessage.value = ''
  
  try {
    const result = await documentStore.getDocumentPreview(props.documentId, props.pages)
    previewText.value = result.preview_text || ''
    pageCount.value = result.page_count || 0
    previewStatus.value = result.status || ''
    statusMessage.value = result.message || ''
  } catch (err) {
    console.error('Preview load failed:', err)
    previewStatus.value = 'error'
    statusMessage.value = '加载预览失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.preview-content {
  max-height: 500px;
  overflow-y: auto;
  transition: max-height 0.3s ease;
}

.preview-content.expanded {
  max-height: none;
}

/* Markdown 渲染样式 */
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  font-weight: 600;
  margin-top: 1em;
  margin-bottom: 0.5em;
}

.markdown-body :deep(h1) { font-size: 1.5em; }
.markdown-body :deep(h2) { font-size: 1.3em; }
.markdown-body :deep(h3) { font-size: 1.1em; }

.markdown-body :deep(p) {
  margin-bottom: 0.75em;
  line-height: 1.6;
}

.markdown-body :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin: 0.5em 0;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 8px 12px;
  text-align: left;
}

.markdown-body :deep(th) {
  background-color: #f9fafb;
  font-weight: 600;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 1.5em;
  margin-bottom: 0.75em;
}

.markdown-body :deep(li) {
  margin-bottom: 0.25em;
}

.status-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  border-radius: 8px;
  background-color: #f9fafb;
}

.status-card.not-loaded {
  background-color: #f0f9ff;
}

.status-card.not-loaded .status-icon {
  color: #3b82f6;
}

.status-card.processing {
  background-color: #fefce8;
}

.status-card.processing .status-icon {
  color: #eab308;
}

.status-card.error {
  background-color: #fef2f2;
}

.status-card.error .status-icon {
  color: #ef4444;
}

.status-icon {
  margin-bottom: 16px;
}

.status-icon.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.status-message {
  color: #6b7280;
  font-size: 14px;
  text-align: center;
  margin: 0;
}
</style>
