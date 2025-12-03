<template>
  <div class="document-list">
    <div class="flex justify-between items-center mb-4">
      <h3 class="text-lg font-semibold">
        文档列表 
        <span class="text-sm text-gray-500 font-normal ml-2">
          (共 {{ totalDocuments }} 个文档)
        </span>
      </h3>
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
    
    <div v-else-if="documents.length === 0" class="text-center py-8 bg-gray-50 rounded-lg">
      <p class="text-gray-600">暂无文档，请上传文档</p>
    </div>
    
    <!-- 表格视图 -->
    <div v-else class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th scope="col" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              文档名称
            </th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              格式
            </th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              大小
            </th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              状态
            </th>
            <th scope="col" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              上传时间
            </th>
            <th scope="col" class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              操作
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr
            v-for="doc in documents"
            :key="doc.id"
            class="hover:bg-gray-50 transition-colors cursor-pointer"
            :class="{ 'bg-blue-50': selectedId === doc.id }"
            @click="selectDocument(doc)"
          >
            <td class="px-4 py-3 whitespace-nowrap">
              <div class="flex items-center">
                <div class="flex-shrink-0 h-8 w-8 flex items-center justify-center bg-gray-100 rounded">
                  <span class="text-lg">{{ getFileIcon(doc.format) }}</span>
                </div>
                <div class="ml-3">
                  <div class="text-sm font-medium text-gray-900 truncate max-w-xs" :title="doc.filename">
                    {{ doc.filename }}
                  </div>
                </div>
              </div>
            </td>
            <td class="px-4 py-3 whitespace-nowrap">
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                {{ doc.format.toUpperCase() }}
              </span>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
              {{ formatFileSize(doc.size_bytes) }}
            </td>
            <td class="px-4 py-3 whitespace-nowrap">
              <span
                class="px-2.5 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full"
                :class="getStatusClass(doc.status)"
              >
                {{ getStatusText(doc.status) }}
              </span>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
              {{ formatDate(doc.upload_time) }}
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
              <button
                @click.stop="confirmDelete(doc)"
                class="text-red-600 hover:text-red-900 transition-colors"
                :disabled="deleting === doc.id"
                title="删除文档"
              >
                <span v-if="deleting === doc.id" class="spinner inline-block w-4 h-4"></span>
                <span v-else>删除</span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <!-- Pagination -->
    <div v-if="totalPages > 1" class="flex justify-between items-center mt-4 px-4">
      <div class="text-sm text-gray-600">
        显示第 {{ (currentPage - 1) * pageSize + 1 }} - {{ Math.min(currentPage * pageSize, totalDocuments) }} 条，共 {{ totalDocuments }} 条
      </div>
      <div class="flex items-center gap-2">
        <button
          class="btn-secondary text-sm px-3 py-1"
          :disabled="currentPage === 1"
          @click="goToPage(currentPage - 1)"
        >
          上一页
        </button>
        
        <span class="text-sm text-gray-600 px-2">
          {{ currentPage }} / {{ totalPages }}
        </span>
        
        <button
          class="btn-secondary text-sm px-3 py-1"
          :disabled="currentPage === totalPages"
          @click="goToPage(currentPage + 1)"
        >
          下一页
        </button>
      </div>
    </div>
    
    <!-- 删除确认对话框 -->
    <div v-if="showDeleteConfirm" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h3 class="text-lg font-semibold mb-4">确认删除</h3>
        <p class="text-gray-600 mb-6">
          确定要删除文档 <span class="font-semibold">{{ documentToDelete?.filename }}</span> 吗？
          <br>
          <span class="text-sm text-red-600">此操作不可撤销，将同时删除所有相关的处理结果。</span>
        </p>
        <div class="flex justify-end gap-3">
          <button
            class="btn-secondary"
            @click="cancelDelete"
            :disabled="deleting"
          >
            取消
          </button>
          <button
            class="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
            @click="deleteDocument"
            :disabled="deleting"
          >
            <span v-if="deleting" class="flex items-center">
              <span class="spinner inline-block w-4 h-4 mr-2"></span>
              删除中...
            </span>
            <span v-else>确认删除</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useDocumentStore } from '../../stores/document'

const documentStore = useDocumentStore()

const selectedId = ref(null)
const showDeleteConfirm = ref(false)
const documentToDelete = ref(null)
const deleting = ref(null)

const documents = computed(() => documentStore.documents)
const loading = computed(() => documentStore.loading)
const currentPage = computed(() => documentStore.currentPage)
const totalDocuments = computed(() => documentStore.totalDocuments)
const pageSize = computed(() => documentStore.pageSize)

const totalPages = computed(() => Math.ceil(totalDocuments.value / pageSize.value))

const emit = defineEmits(['select', 'delete'])

onMounted(async () => {
  await documentStore.fetchDocuments()
  // 页面初始化时，默认选中第一个文档
  if (documents.value.length > 0) {
    selectDocument(documents.value[0])
  }
})

// 监听文档列表变化，当上传新文档后自动选中
watch(documents, (newDocs, oldDocs) => {
  // 如果文档列表有内容且当前没有选中任何文档
  if (newDocs.length > 0 && !selectedId.value) {
    selectDocument(newDocs[0])
  }
  // 如果是上传新文档后（总数增加），自动选中第一个（最新的）
  else if (newDocs.length > 0 && oldDocs && newDocs.length > oldDocs.length) {
    selectDocument(newDocs[0])
  }
}, { deep: true })

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

function confirmDelete(doc) {
  documentToDelete.value = doc
  showDeleteConfirm.value = true
}

function cancelDelete() {
  showDeleteConfirm.value = false
  documentToDelete.value = null
}

async function deleteDocument() {
  if (!documentToDelete.value) return
  
  const docId = documentToDelete.value.id
  deleting.value = docId
  
  try {
    await documentStore.deleteDocument(docId)
    
    // 通知父组件
    emit('delete', docId)
    
    // 清空选中状态
    if (selectedId.value === docId) {
      selectedId.value = null
      // 如果还有其他文档，选中第一个
      if (documents.value.length > 0) {
        selectDocument(documents.value[0])
      }
    }
    
    // 关闭对话框
    showDeleteConfirm.value = false
    documentToDelete.value = null
    
    // 如果当前页没有文档了，返回上一页
    if (documents.value.length === 0 && currentPage.value > 1) {
      await documentStore.fetchDocuments(currentPage.value - 1)
      // 切换页面后，选中第一个文档
      if (documents.value.length > 0) {
        selectDocument(documents.value[0])
      }
    }
  } catch (err) {
    console.error('删除文档失败:', err)
    alert('删除文档失败: ' + err.message)
  } finally {
    deleting.value = null
  }
}

function getFileIcon(format) {
  const icons = {
    pdf: '📄',
    doc: '📝',
    docx: '📝',
    txt: '📃',
    md: '📋',
    markdown: '📋'
  }
  return icons[format.toLowerCase()] || '📄'
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

function formatDate(dateString) {
  if (!dateString) return '-'
  
  // 解析 ISO 8601 格式的UTC时间字符串
  const date = new Date(dateString)
  
  // 检查是否是有效日期
  if (isNaN(date.getTime())) return dateString
  
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  
  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}小时前`
  if (diffMins < 43200) return `${Math.floor(diffMins / 1440)}天前`
  
  // 使用本地时区格式化显示
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
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

<style scoped>
/* 确保表格滚动时表头固定 */
.overflow-x-auto {
  max-height: 600px;
  overflow-y: auto;
}

/* 优化表格行的hover效果 */
tbody tr {
  transition: background-color 0.15s ease;
}

/* 选中行的样式 */
tbody tr.bg-blue-50:hover {
  background-color: rgb(219 234 254) !important;
}
</style>
