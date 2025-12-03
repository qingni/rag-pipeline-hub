<template>
  <div class="document-preview">
    <div v-if="loading" class="text-center py-8">
      <div class="spinner mx-auto mb-2"></div>
      <p class="text-gray-600">加载预览...</p>
    </div>
    
    <div v-else-if="previewText" class="card">
      <h4 class="font-semibold mb-4">文档预览 (前{{ pageCount }}页)</h4>
      <div class="preview-content whitespace-pre-wrap text-sm text-gray-700">
        {{ previewText }}
      </div>
    </div>
    
    <div v-else class="card text-center py-8">
      <p class="text-gray-600">暂无预览</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
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

watch(() => props.documentId, async (newId) => {
  if (newId) {
    await loadPreview()
  }
}, { immediate: true })

async function loadPreview() {
  if (!props.documentId) return
  
  loading.value = true
  try {
    const result = await documentStore.getDocumentPreview(props.documentId, props.pages)
    previewText.value = result.preview_text
    pageCount.value = result.page_count
  } catch (err) {
    console.error('Preview load failed:', err)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.preview-content {
  max-height: 400px;
  overflow-y: auto;
}
</style>
