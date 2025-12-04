<template>
  <div class="document-list">
    <!-- 标题和操作栏 -->
    <div class="flex justify-between items-center mb-4">
      <div>
        <h3 class="text-lg font-semibold">
          文档列表
          <t-tag theme="default" variant="light" class="ml-2">
            共 {{ totalDocuments }} 个文档
          </t-tag>
        </h3>
      </div>
      <t-button 
        variant="outline"
        size="small"
        @click="refresh"
        :loading="loading"
      >
        <template #icon>
          <RefreshCwIcon :size="16" />
        </template>
        刷新
      </t-button>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="loading && documents.length === 0" class="text-center py-12">
      <t-loading size="large" text="加载中..." />
    </div>
    
    <!-- 空状态 -->
    <t-empty 
      v-else-if="documents.length === 0" 
      description="暂无文档，请上传文档"
    >
      <template #image>
        <FileIcon :size="64" class="text-gray-300" />
      </template>
    </t-empty>
    
    <!-- 文档表格 -->
    <div v-else>
      <t-table
        :data="documents"
        :columns="columns"
        :hover="true"
        row-key="id"
        :selected-row-keys="selectedId ? [selectedId] : []"
        :row-class-name="getRowClassName"
        @select-change="handleSelectChange"
        @row-click="handleRowClick"
        size="medium"
        table-layout="auto"
        class="document-table"
      >
        <!-- 文档名称列 -->
        <template #filename="{ row }">
          <div class="flex items-center">
            <div class="flex-shrink-0 mr-3">
              <component :is="getFileIconComponent(row.format)" :size="20" class="text-blue-500" />
            </div>
            <div class="truncate max-w-xs" :title="row.filename">
              <span class="font-medium">{{ row.filename }}</span>
            </div>
          </div>
        </template>
        
        <!-- 格式列 -->
        <template #format="{ row }">
          <t-tag theme="primary" variant="light" size="small">
            {{ row.format.toUpperCase() }}
          </t-tag>
        </template>
        
        <!-- 大小列 -->
        <template #size="{ row }">
          <span class="text-sm text-gray-600">
            {{ formatFileSize(row.size_bytes) }}
          </span>
        </template>
        
        <!-- 状态列 -->
        <template #status="{ row }">
          <t-tag 
            :theme="getStatusTheme(row.status)"
            variant="light"
            size="small"
          >
            {{ getStatusText(row.status) }}
          </t-tag>
        </template>
        
        <!-- 时间列 -->
        <template #upload_time="{ row }">
          <span class="text-sm text-gray-600">
            {{ formatDate(row.upload_time) }}
          </span>
        </template>
        
        <!-- 操作列 -->
        <template #operation="{ row }">
          <t-space>
            <t-popconfirm
              content="确定要删除此文档吗？此操作不可撤销，将同时删除所有相关的处理结果。"
              theme="warning"
              @confirm="handleDelete(row)"
            >
              <t-button
                theme="danger"
                variant="text"
                size="small"
                :loading="deleting === row.id"
              >
                <template #icon>
                  <Trash2Icon :size="14" />
                </template>
                删除
              </t-button>
            </t-popconfirm>
          </t-space>
        </template>
      </t-table>
      
      <!-- 分页 -->
      <div v-if="totalPages > 1" class="mt-4 flex justify-end">
        <t-pagination
          v-model="currentPageModel"
          :total="totalDocuments"
          :page-size="pageSize"
          :show-page-size="false"
          show-jumper
          @change="handlePageChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useDocumentStore } from '../../stores/document'
import { 
  RefreshCw as RefreshCwIcon, 
  File as FileIcon,
  FileText,
  FileCode,
  FileType,
  Trash2 as Trash2Icon
} from 'lucide-vue-next'

const documentStore = useDocumentStore()

const selectedId = ref(null)
const deleting = ref(null)

const documents = computed(() => documentStore.documents)
const loading = computed(() => documentStore.loading)
const currentPage = computed(() => documentStore.currentPage)
const totalDocuments = computed(() => documentStore.totalDocuments)
const pageSize = computed(() => documentStore.pageSize)
const currentDocument = computed(() => documentStore.currentDocument)
const totalPages = computed(() => Math.ceil(totalDocuments.value / pageSize.value))

const currentPageModel = ref(currentPage.value)

const emit = defineEmits(['select', 'delete'])

// 表格列配置
const columns = [
  {
    colKey: 'filename',
    title: '文档名称',
    width: 300,
    ellipsis: true
  },
  {
    colKey: 'format',
    title: '格式',
    width: 100,
    align: 'center'
  },
  {
    colKey: 'size',
    title: '大小',
    width: 120,
    align: 'right'
  },
  {
    colKey: 'status',
    title: '状态',
    width: 100,
    align: 'center'
  },
  {
    colKey: 'upload_time',
    title: '上传时间',
    width: 180
  },
  {
    colKey: 'operation',
    title: '操作',
    width: 100,
    align: 'center',
    fixed: 'right'
  }
]

onMounted(async () => {
  await documentStore.fetchDocuments()
  if (documents.value.length > 0) {
    selectDocument(documents.value[0])
  }
})

watch(currentDocument, (newDoc) => {
  if (newDoc) {
    selectedId.value = newDoc.id
  }
}, { immediate: true })

watch(documents, (newDocs, oldDocs) => {
  if (newDocs.length === 0) {
    selectedId.value = null
    return
  }
  
  const currentSelectedInList = selectedId.value && newDocs.some(doc => doc.id === selectedId.value)
  
  if (!currentSelectedInList) {
    selectDocument(newDocs[0])
  } else if (oldDocs && newDocs.length > oldDocs.length && currentPage.value === 1) {
    selectDocument(newDocs[0])
  }
}, { deep: true })

watch(currentPage, (newPage) => {
  currentPageModel.value = newPage
})

function selectDocument(doc) {
  selectedId.value = doc.id
  console.log('选中文档:', doc.filename, '文档ID:', doc.id, 'selectedId:', selectedId.value)
  emit('select', doc)
}

function getRowClassName({ row }) {
  return row.id === selectedId.value ? 'selected-row' : ''
}

function handleRowClick({ row }) {
  selectDocument(row)
}

function handleSelectChange(selectedRowKeys) {
  // 当用户通过表格选择功能选择行时触发
  if (selectedRowKeys.length > 0) {
    const selectedDoc = documents.value.find(doc => doc.id === selectedRowKeys[0])
    if (selectedDoc) {
      selectDocument(selectedDoc)
    }
  }
}

function refresh() {
  documentStore.fetchDocuments(currentPage.value)
}

function handlePageChange(pageInfo) {
  documentStore.fetchDocuments(pageInfo.current)
}

async function handleDelete(doc) {
  const docId = doc.id
  deleting.value = docId
  
  try {
    await documentStore.deleteDocument(docId)
    emit('delete', docId)
    
    if (selectedId.value === docId) {
      selectedId.value = null
      if (documents.value.length > 0) {
        selectDocument(documents.value[0])
      }
    }
    
    if (documents.value.length === 0 && currentPage.value > 1) {
      await documentStore.fetchDocuments(currentPage.value - 1)
      if (documents.value.length > 0) {
        selectDocument(documents.value[0])
      }
    }
  } catch (err) {
    console.error('删除文档失败:', err)
  } finally {
    deleting.value = null
  }
}

function getFileIconComponent(format) {
  const iconMap = {
    pdf: FileText,
    doc: FileCode,
    docx: FileCode,
    txt: FileType,
    md: FileType,
    markdown: FileType
  }
  return iconMap[format?.toLowerCase()] || FileIcon
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
  
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return dateString
  
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  
  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}小时前`
  if (diffMins < 43200) return `${Math.floor(diffMins / 1440)}天前`
  
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

function getStatusTheme(status) {
  const themeMap = {
    uploaded: 'primary',
    processing: 'warning',
    ready: 'success',
    error: 'danger'
  }
  return themeMap[status] || 'default'
}

function getStatusText(status) {
  const textMap = {
    uploaded: '已上传',
    processing: '处理中',
    ready: '就绪',
    error: '错误'
  }
  return textMap[status] || status
}
</script>

<style scoped>
.document-list {
  padding: 0;
}

/* 移除默认的斑马纹背景 */
:deep(.t-table__body tr) {
  background-color: #ffffff !important;
  transition: background-color 0.2s ease;
}

/* 自定义选中行的背景色 */
:deep(.t-table__body tr.selected-row) {
  background-color: #f3f4f6 !important;
}

/* TDesign 内置选中样式（备用） */
:deep(.t-table__body tr.t-table-row--selected),
:deep(.t-table__body tr.t-is-selected),
:deep(.t-table__body tr[aria-selected="true"]) {
  background-color: #f3f4f6 !important;
}

/* hover 效果 - 非选中行 */
:deep(.t-table__body tr:hover:not(.selected-row)) {
  background-color: #f9fafb !important;
}

/* 选中行的 hover 效果 */
:deep(.t-table__body tr.selected-row:hover),
:deep(.t-table__body tr.t-table-row--selected:hover),
:deep(.t-table__body tr.t-is-selected:hover),
:deep(.t-table__body tr[aria-selected="true"]:hover) {
  background-color: #e5e7eb !important;
}

/* 确保单元格背景透明，使用行背景 */
:deep(.t-table__body tr td) {
  background-color: transparent !important;
}

/* 点击时的视觉反馈 */
:deep(.t-table__body tr:active) {
  background-color: #e5e7eb !important;
}
</style>
