<template>
  <t-card :bordered="false" class="history-list-card">
    <div class="card-header">
      <div class="header-left">
        <History :size="20" class="header-icon" />
        <h3 class="card-title">向量化历史</h3>
      </div>
      <t-button
        theme="default"
        variant="outline"
        size="small"
        @click="handleRefresh"
        :loading="loading"
      >
        <RefreshCw :size="14" />
        刷新
      </t-button>
    </div>
    
    <div class="filter-section">
      <t-input
        v-model="searchText"
        placeholder="搜索文档名称..."
        clearable
        @change="handleSearch"
      >
        <template #prefix-icon>
          <Search :size="16" />
        </template>
      </t-input>
      
      <t-select
        v-model="statusFilter"
        placeholder="筛选状态"
        clearable
        style="width: 150px"
        @change="handleFilter"
      >
        <t-option value="SUCCESS" label="成功" />
        <t-option value="PARTIAL_SUCCESS" label="部分成功" />
        <t-option value="FAILED" label="失败" />
      </t-select>
    </div>
    
    <!-- 历史记录列表 -->
    <div v-if="loading && !historyList.length" class="loading-container">
      <t-loading size="large" text="加载中..." />
    </div>
    
    <t-empty
      v-else-if="!historyList.length"
      description="暂无向量化历史记录"
    />
    
    <div v-else class="history-list">
      <div
        v-for="item in paginatedList"
        :key="item.result_id"
        class="history-item"
        :class="{ 'active': selectedId === item.result_id }"
        @click="handleSelect(item)"
      >
        <div class="item-header">
          <div class="item-title">
            <FileText :size="16" class="item-icon" />
            <span class="document-name">{{ item.document_name || '未知文档' }}</span>
          </div>
          <t-tag :theme="getStatusTheme(item.status)" size="small" variant="light">
            {{ getStatusText(item.status) }}
          </t-tag>
        </div>
        
        <div class="item-meta">
          <span class="meta-item">
            <Cpu :size="12" />
            {{ item.model }}
          </span>
          <span class="meta-item">
            <Layers :size="12" />
            {{ item.vector_dimension }}维
          </span>
          <span class="meta-item">
            <CheckCircle2 :size="12" />
            {{ item.successful_count }}个
          </span>
          <span class="meta-item">
            <Clock :size="12" />
            {{ formatTime(item.created_at) }}
          </span>
        </div>
        
        <!-- JSON文件路径 -->
        <div v-if="item.json_file_path" class="json-file-path">
          <FileJson :size="12" class="path-icon" />
          <span class="path-text" :title="item.json_file_path">{{ item.json_file_path }}</span>
          <t-button
            theme="default"
            variant="text"
            size="small"
            class="copy-btn"
            @click.stop="copyPath(item.json_file_path)"
          >
            <Copy :size="10" />
          </t-button>
        </div>
        
        <div class="item-actions">
          <t-button
            theme="primary"
            variant="text"
            size="small"
            @click.stop="$emit('view', item.result_id)"
          >
            <Eye :size="12" />
            查看
          </t-button>
          <t-button
            theme="default"
            variant="text"
            size="small"
            @click.stop="handleDownload(item)"
          >
            <Download :size="12" />
            导出
          </t-button>
          <t-popconfirm
            content="确定要删除这条向量化记录吗？"
            @confirm="handleDelete(item.result_id)"
          >
            <t-button
              theme="danger"
              variant="text"
              size="small"
              @click.stop
            >
              <Trash2 :size="12" />
              删除
            </t-button>
          </t-popconfirm>
        </div>
      </div>
    </div>
    
    <!-- 分页 -->
    <div v-if="totalPages > 1" class="pagination">
      <t-pagination
        v-model="currentPage"
        :total="filteredList.length"
        :page-size="pageSize"
        :show-page-size="false"
        @change="handlePageChange"
      />
    </div>
  </t-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import {
  History,
  RefreshCw,
  Search,
  FileText,
  Cpu,
  Layers,
  CheckCircle2,
  Clock,
  Eye,
  Download,
  Trash2,
  FileJson,
  Copy
} from 'lucide-vue-next'
import { useEmbeddingStore } from '@/stores/embedding'

const props = defineProps({
  documentId: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['view', 'delete', 'download'])

const store = useEmbeddingStore()
const loading = ref(false)
const searchText = ref('')
const statusFilter = ref(null)
const selectedId = ref(null)
const currentPage = ref(1)
const pageSize = ref(10)

const historyList = computed(() => store.embeddingHistory || [])

const filteredList = computed(() => {
  let list = [...historyList.value]
  
  // 按文档ID过滤
  if (props.documentId) {
    list = list.filter(item => item.document_id === props.documentId)
  }
  
  // 按搜索文本过滤
  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    list = list.filter(item =>
      item.document_name?.toLowerCase().includes(search)
    )
  }
  
  // 按状态过滤
  if (statusFilter.value) {
    list = list.filter(item => item.status === statusFilter.value)
  }
  
  return list
})

const totalPages = computed(() =>
  Math.ceil(filteredList.value.length / pageSize.value)
)

const paginatedList = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredList.value.slice(start, end)
})

onMounted(() => {
  loadHistory()
})

async function loadHistory() {
  try {
    loading.value = true
    await store.fetchEmbeddingHistory(props.documentId)
  } catch (error) {
    MessagePlugin.error(error.message || '加载历史记录失败')
  } finally {
    loading.value = false
  }
}

function handleRefresh() {
  loadHistory()
}

function handleSearch() {
  currentPage.value = 1
}

function handleFilter() {
  currentPage.value = 1
}

function handleSelect(item) {
  selectedId.value = item.result_id
  emit('view', item.result_id)
}

function handlePageChange(pageInfo) {
  currentPage.value = pageInfo.current
}

async function handleDelete(resultId) {
  try {
    await store.deleteEmbeddingResult(resultId)
    MessagePlugin.success('删除成功')
    emit('delete', resultId)
    loadHistory()
  } catch (error) {
    MessagePlugin.error(error.message || '删除失败')
  }
}

function handleDownload(item) {
  emit('download', item)
}

function getStatusTheme(status) {
  const themes = {
    'SUCCESS': 'success',
    'PARTIAL_SUCCESS': 'warning',
    'FAILED': 'danger'
  }
  return themes[status] || 'default'
}

function getStatusText(status) {
  const texts = {
    'SUCCESS': '成功',
    'PARTIAL_SUCCESS': '部分成功',
    'FAILED': '失败'
  }
  return texts[status] || status
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function copyPath(path) {
  try {
    await navigator.clipboard.writeText(path)
    MessagePlugin.success('路径已复制到剪贴板')
  } catch (err) {
    MessagePlugin.error('复制失败')
  }
}
</script>

<style scoped>
.history-list-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.history-list-card :deep(.t-card__body) {
  padding: 0;
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
  background-color: #f9fafb;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon {
  color: #3b82f6;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.filter-section {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.filter-section :deep(.t-input) {
  flex: 1;
}

.loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 24px;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.history-item {
  padding: 16px;
  margin-bottom: 8px;
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.history-item:hover {
  border-color: #3b82f6;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
}

.history-item.active {
  border-color: #3b82f6;
  background-color: #eff6ff;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.item-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.item-icon {
  color: #6b7280;
  flex-shrink: 0;
}

.document-name {
  font-size: 14px;
  font-weight: 500;
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #6b7280;
}

.meta-item svg {
  flex-shrink: 0;
}

.json-file-path {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  padding: 8px 10px;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
}

.path-icon {
  color: #64748b;
  flex-shrink: 0;
}

.path-text {
  font-size: 11px;
  color: #475569;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.copy-btn {
  flex-shrink: 0;
  padding: 2px 4px !important;
  min-width: auto !important;
  height: auto !important;
}

.copy-btn:hover {
  color: #3b82f6;
}

.item-actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}

.pagination {
  padding: 16px 24px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: center;
}
</style>
