<template>
  <div class="document-selector">
    <t-card title="选择文档" :bordered="false">
      <template #actions>
        <t-button theme="primary" size="small" @click="handleRefresh">
          <template #icon><t-icon name="refresh" /></template>
          刷新
        </t-button>
      </template>

      <!-- Search and Filter Bar -->
      <div class="filter-bar">
        <t-space size="small" style="width: 100%; flex-wrap: wrap">
          <t-input
            v-model="localFilters.search"
            placeholder="搜索文档名称..."
            clearable
            style="flex: 1; min-width: 200px"
            @change="handleFilterChange"
            @clear="handleFilterChange"
          >
            <template #prefix-icon>
              <t-icon name="search" />
            </template>
          </t-input>

          <t-select
            v-model="localFilters.format"
            placeholder="文件类型"
            clearable
            style="width: 140px"
            @change="handleFilterChange"
          >
            <t-option value="pdf" label="PDF" />
            <t-option value="docx" label="Word" />
            <t-option value="txt" label="文本" />
            <t-option value="md" label="Markdown" />
          </t-select>

          <t-button 
            v-if="hasActiveFilters" 
            theme="default" 
            size="small" 
            @click="clearFilters"
          >
            清除筛选
          </t-button>
        </t-space>
      </div>

      <!-- Document Count Info -->
      <div class="info-bar">
        <t-space size="small">
          <span class="info-text">
            共 <strong>{{ chunkingStore.documentsTotalCount }}</strong> 个文档
          </span>
          <t-divider layout="vertical" />
          <span v-if="selectedDocId" class="info-text success">
            已选择: {{ selectedDocName }}
          </span>
        </t-space>
      </div>

      <!-- Document List -->
      <t-loading :loading="loading" size="small">
        <div v-if="documents.length > 0" class="documents-container">
          <div class="list-view">
            <div
              v-for="doc in documents"
              :key="doc.id"
              class="doc-item-wrapper"
              :class="{ selected: selectedDocId === doc.id }"
              @click="handleSelect(doc.id)"
            >
              <t-radio
                :value="doc.id"
                :checked="selectedDocId === doc.id"
                @click.stop
              >
                <div class="doc-item">
                  <div class="doc-header">
                    <div class="doc-name" :title="doc.filename">{{ doc.filename }}</div>
                  </div>
                  <div class="doc-meta">
                    <t-tag size="small" theme="primary" variant="light">
                      {{ doc.format?.toUpperCase() || 'N/A' }}
                    </t-tag>
                    <span class="doc-size">{{ formatSize(doc.size_bytes) }}</span>
                    <span class="doc-time">{{ formatTime(doc.upload_time) }}</span>
                    <t-tag 
                      v-if="doc.processing_type"
                      size="small" 
                      :theme="doc.processing_type === 'parsed' ? 'success' : 'default'"
                      variant="light"
                    >
                      {{ doc.processing_type === 'parsed' ? '已解析' : '已加载' }}
                    </t-tag>
                  </div>
                </div>
              </t-radio>
            </div>
          </div>

          <!-- Pagination -->
          <div v-if="chunkingStore.documentsTotalCount > chunkingStore.documentsPageSize" class="pagination-wrapper">
            <t-pagination
              v-model="currentPage"
              :total="chunkingStore.documentsTotalCount"
              :page-size="chunkingStore.documentsPageSize"
              :show-jumper="true"
              :show-page-size="false"
              size="small"
              @change="handlePageChange"
            />
          </div>
        </div>

        <t-empty
          v-else-if="!loading"
          :description="hasActiveFilters ? '未找到匹配的文档' : '暂无已解析的文档'"
        >
          <template #action>
            <t-button v-if="hasActiveFilters" theme="primary" size="small" @click="clearFilters">
              清除筛选
            </t-button>
          </template>
        </t-empty>
      </t-loading>
    </t-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useChunkingStore } from '@/stores/chunkingStore'
import { MessagePlugin } from 'tdesign-vue-next'

const chunkingStore = useChunkingStore()

const loading = computed(() => chunkingStore.documentsLoading)
const documents = computed(() => chunkingStore.parsedDocuments)
const selectedDocId = ref(null)
const currentPage = ref(1)

// 筛选条件：搜索和文件类型，固定按上传时间倒序
const localFilters = ref({
  search: '',
  format: null,
  sortBy: 'upload_time',
  sortOrder: 'desc'
})

const selectedDocName = computed(() => {
  const doc = documents.value.find(d => d.id === selectedDocId.value)
  return doc ? doc.filename : ''
})

const hasActiveFilters = computed(() => {
  return !!(localFilters.value.search || localFilters.value.format)
})

let filterTimer = null
const handleFilterChange = () => {
  // 防抖处理，300ms 后执行查询
  clearTimeout(filterTimer)
  filterTimer = setTimeout(async () => {
    chunkingStore.updateDocumentFilters(localFilters.value)
    currentPage.value = 1
    await loadDocuments()
  }, 300)
}

const clearFilters = () => {
  localFilters.value = {
    search: '',
    format: null,
    sortBy: 'upload_time',
    sortOrder: 'desc'
  }
  handleFilterChange()
}

const loadDocuments = async () => {
  try {
    await chunkingStore.loadParsedDocuments(currentPage.value)
  } catch (error) {
    console.error('加载文档列表失败:', error)
    MessagePlugin.error('加载文档列表失败')
  }
}

const handleRefresh = async () => {
  currentPage.value = 1
  await loadDocuments()
  MessagePlugin.success('已刷新')
}

const handleSelect = (docId) => {
  selectedDocId.value = docId
  const doc = chunkingStore.parsedDocuments.find(d => d.id === docId)
  if (doc) {
    chunkingStore.selectDocument(doc)
    MessagePlugin.success(`已选择: ${doc.filename}`)
  }
}

const handlePageChange = async (pageInfo) => {
  currentPage.value = pageInfo.current
  await loadDocuments()
  // 翻页后滚动到顶部
  const container = document.querySelector('.documents-container')
  if (container) {
    container.scrollTop = 0
  }
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const formatTime = (time) => {
  if (!time) return '-'
  const date = new Date(time)
  const now = new Date()
  const diff = now - date
  
  // 显示相对时间
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
  if (diff < 604800000) return Math.floor(diff / 86400000) + '天前'
  
  // 显示绝对时间
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 初始化：加载文档并恢复选中状态
onMounted(async () => {
  await loadDocuments()
  
  // 恢复之前的选中状态
  if (chunkingStore.selectedDocument) {
    selectedDocId.value = chunkingStore.selectedDocument.id
  } else if (documents.value.length > 0) {
    // 如果没有选中的文档，默认选择第一个
    const firstDoc = documents.value[0]
    selectedDocId.value = firstDoc.id
    handleSelect(firstDoc.id)
  }
})
</script>

<style scoped>
.document-selector {
  margin-bottom: 20px;
}

.filter-bar {
  padding: 16px 0;
  border-bottom: 1px solid var(--td-border-level-1-color);
  margin-bottom: 12px;
}

.info-bar {
  padding: 8px 0;
  margin-bottom: 12px;
}

.info-text {
  font-size: 13px;
  color: var(--td-text-color-secondary);
}

.info-text.success {
  color: var(--td-success-color);
  font-weight: 500;
}

.documents-container {
  margin-top: 12px;
}

/* List View Styles */
.list-view {
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 6px;
  overflow: hidden;
  max-height: 500px;
  overflow-y: auto;
}

.doc-item-wrapper {
  padding: 12px 16px;
  border-bottom: 1px solid var(--td-border-level-1-color);
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--td-bg-color-container);
}

.doc-item-wrapper:last-child {
  border-bottom: none;
}

.doc-item-wrapper:hover {
  background: var(--td-bg-color-container-hover);
}

.doc-item-wrapper.selected {
  background: var(--td-brand-color-1);
  border-left: 3px solid var(--td-brand-color);
}

.doc-item {
  width: 100%;
  line-height: 1.4;
  min-width: 0;
}

.doc-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.doc-name {
  font-weight: 500;
  font-size: 14px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.5;
}

.doc-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--td-text-color-secondary);
  line-height: 1.5;
}

.doc-size, .doc-time {
  font-size: 12px;
  white-space: nowrap;
}

/* Pagination */
.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

/* Responsive */
@media (max-width: 768px) {
  .filter-bar :deep(.t-space) {
    flex-direction: column;
    align-items: stretch;
  }
  
  .filter-bar :deep(.t-input),
  .filter-bar :deep(.t-select) {
    width: 100% !important;
  }
}

/* Virtual Scroll Override */
:deep(.t-virtual-scroll) {
  border-radius: 6px;
}

:deep(.t-virtual-scroll__content) {
  padding: 0;
}
</style>
