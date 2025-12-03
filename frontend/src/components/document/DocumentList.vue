<template>
  <div class="document-list">
    <div class="flex justify-between items-center mb-4">
      <h3 class="text-lg font-semibold">文档列表</h3>
      <button 
        class="btn-secondary text-sm"
        @click="refresh"
        :disabled="loading"
      >
        <span v-if="!loading">刷新</span>
        <span v-else class="spinner inline-block w-4 h-4"></span>
      </button>
    </div>
    
    <div v-if="loading && documents.length === 0" class="text-center py-8">
      <div class="spinner mx-auto mb-2"></div>
      <p class="text-gray-600">加载中...</p>
    </div>
    
    <div v-else-if="documents.length === 0" class="text-center py-8">
      <p class="text-gray-600">暂无文档</p>
    </div>
    
    <div v-else class="space-y-2">
      <div
        v-for="doc in documents"
        :key="doc.id"
        class="card p-4 hover:shadow-lg transition-shadow cursor-pointer"
        :class="{ 'ring-2 ring-primary-500': selectedId === doc.id }"
        @click="selectDocument(doc)"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <h4 class="font-semibold text-gray-900">{{ doc.filename }}</h4>
            <div class="flex items-center gap-4 mt-2 text-sm text-gray-600">
              <span>{{ formatFileSize(doc.size_bytes) }}</span>
              <span>{{ doc.format.toUpperCase() }}</span>
              <span>{{ formatDate(doc.upload_time) }}</span>
            </div>
          </div>
          
          <div class="ml-4">
            <span
              class="px-3 py-1 rounded-full text-xs font-semibold"
              :class="getStatusClass(doc.status)"
            >
              {{ getStatusText(doc.status) }}
            </span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Pagination -->
    <div v-if="totalPages > 1" class="flex justify-center items-center gap-2 mt-6">
      <button
        class="btn-secondary text-sm"
        :disabled="currentPage === 1"
        @click="goToPage(currentPage - 1)"
      >
        上一页
      </button>
      
      <span class="text-sm text-gray-600">
        第 {{ currentPage }} / {{ totalPages }} 页
      </span>
      
      <button
        class="btn-secondary text-sm"
        :disabled="currentPage === totalPages"
        @click="goToPage(currentPage + 1)"
      >
        下一页
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useDocumentStore } from '../../stores/document'

const documentStore = useDocumentStore()

const selectedId = ref(null)

const documents = computed(() => documentStore.documents)
const loading = computed(() => documentStore.loading)
const currentPage = computed(() => documentStore.currentPage)
const totalDocuments = computed(() => documentStore.totalDocuments)
const pageSize = computed(() => documentStore.pageSize)

const totalPages = computed(() => Math.ceil(totalDocuments.value / pageSize.value))

const emit = defineEmits(['select'])

onMounted(() => {
  documentStore.fetchDocuments()
})

function selectDocument(doc) {
  selectedId.value = doc.id
  emit('select', doc)
}

function refresh() {
  documentStore.fetchDocuments(currentPage.value)
}

function goToPage(page) {
  documentStore.fetchDocuments(page)
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

function formatDate(dateString) {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

function getStatusClass(status) {
  const classes = {
    uploaded: 'bg-blue-100 text-blue-800',
    processing: 'bg-yellow-100 text-yellow-800',
    ready: 'bg-green-100 text-green-800',
    error: 'bg-red-100 text-red-800'
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}

function getStatusText(status) {
  const texts = {
    uploaded: '已上传',
    processing: '处理中',
    ready: '就绪',
    error: '错误'
  }
  return texts[status] || status
}
</script>
