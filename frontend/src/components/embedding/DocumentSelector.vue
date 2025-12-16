<template>
  <div class="document-selector">
    <label class="selector-label">选择文档</label>
    <t-select
      v-model="localSelectedDocument"
      :options="formattedDocuments"
      placeholder="请选择已分块的文档"
      :disabled="loading || documents.length === 0"
      clearable
      filterable
      @change="handleChange"
    >
      <template v-if="documents.length === 0" #empty>
        <div class="empty-state">
          <FileX :size="32" class="empty-icon" />
          <p class="empty-text">暂无已分块文档</p>
          <p class="empty-hint">请先对文档进行分块处理</p>
        </div>
      </template>
    </t-select>
    
    <!-- 已选文档信息 -->
    <div v-if="selectedDocInfo" class="document-info">
      <div class="info-row">
        <span class="info-label">文档名称:</span>
        <span class="info-value">{{ selectedDocInfo.filename }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">上传时间:</span>
        <span class="info-value">{{ formatDateTime(selectedDocInfo.upload_time) }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">文件大小:</span>
        <span class="info-value">{{ formatFileSize(selectedDocInfo.size_bytes) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch, ref } from 'vue'
import { FileX } from 'lucide-vue-next'

const props = defineProps({
  documents: {
    type: Array,
    default: () => []
  },
  modelValue: {
    type: String,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const localSelectedDocument = ref(props.modelValue)

// 格式化文档选项: "DocumentName · 已分块 · YYYY-MM-DD"
const formattedDocuments = computed(() => {
  return props.documents.map(doc => ({
    label: formatDocumentLabel(doc),
    value: doc.id
  }))
})

const selectedDocInfo = computed(() => {
  if (!localSelectedDocument.value) return null
  return props.documents.find(doc => doc.id === localSelectedDocument.value)
})

function formatDocumentLabel(doc) {
  const uploadDate = new Date(doc.upload_time)
  const dateStr = uploadDate.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
  return `${doc.filename} · 已分块 · ${dateStr}`
}

function formatDateTime(dateString) {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function handleChange(value) {
  emit('update:modelValue', value)
}

// 同步外部变化
watch(() => props.modelValue, (newValue) => {
  localSelectedDocument.value = newValue
})
</script>

<style scoped>
.document-selector {
  margin-bottom: 1.5rem;
}

.selector-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 0.5rem;
}

.empty-state {
  text-align: center;
  padding: 2rem 1rem;
}

.empty-icon {
  color: #9ca3af;
  margin: 0 auto 0.75rem;
}

.empty-text {
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  margin: 0 0 0.25rem;
}

.empty-hint {
  font-size: 12px;
  color: #9ca3af;
  margin: 0;
}

.document-info {
  margin-top: 1rem;
  padding: 1rem;
  background-color: #f9fafb;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  font-size: 13px;
}

.info-row:not(:last-child) {
  border-bottom: 1px solid #e5e7eb;
}

.info-label {
  color: #6b7280;
  font-weight: 500;
}

.info-value {
  color: #111827;
  text-align: right;
  word-break: break-all;
}
</style>
