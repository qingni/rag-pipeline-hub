<template>
  <div class="history-list">
    <t-card title="分块历史" :bordered="false">
      <template #actions>
        <t-space>
          <t-button theme="danger" size="small" variant="outline" @click="handleClearAll" :disabled="historyData.length === 0">
            <template #icon><t-icon name="delete" /></template>
            清空
          </t-button>
          <t-button theme="primary" size="small" variant="outline" @click="showFilters = !showFilters">
            <template #icon><t-icon name="filter" /></template>
            筛选
          </t-button>
          <t-button theme="default" size="small" @click="handleRefresh">
            <template #icon><t-icon name="refresh" /></template>
          </t-button>
        </t-space>
      </template>

      <!-- Filters -->
      <div v-if="showFilters" class="filters-section">
        <t-form :data="filters" layout="inline">
          <t-form-item label="文档名称">
            <t-input v-model="filters.document_name" placeholder="搜索" clearable />
          </t-form-item>
          <t-form-item label="策略">
            <t-select v-model="filters.strategy" placeholder="全部" clearable>
              <t-option value="character" label="按字数" />
              <t-option value="paragraph" label="按段落" />
              <t-option value="heading" label="按标题" />
              <t-option value="semantic" label="按语义" />
            </t-select>
          </t-form-item>
          <t-form-item>
            <t-button theme="primary" @click="handleSearch">搜索</t-button>
          </t-form-item>
        </t-form>
      </div>

      <t-loading :loading="loading">
        <t-table
          :data="historyData"
          :columns="columns"
          :pagination="paginationProps"
          row-key="result_id"
          :selected-row-keys="selectedRowKeys"
          @select-change="handleSelectChange"
          @page-change="handlePageChange"
        >
          <template #strategy_type="{ row }">
            <t-space align="center" :size="4">
              <t-tag theme="primary" variant="light">{{ getStrategyLabel(row.strategy_type) }}</t-tag>
              <t-tooltip :content="formatParams(row)" placement="top" max-width="400">
                <t-icon name="info-circle" style="cursor: pointer; color: var(--td-gray-color-6);" />
              </t-tooltip>
            </t-space>
          </template>

          <template #status="{ row }">
            <t-tag :theme="getStatusTheme(row.status)">{{ getStatusLabel(row.status) }}</t-tag>
          </template>

          <template #processing_time="{ row }">
            {{ row.processing_time?.toFixed(2) }}s
          </template>

          <template #created_at="{ row }">
            {{ formatTime(row.created_at) }}
          </template>

          <template #operation="{ row }">
            <t-space>
              <t-button theme="primary" variant="text" size="small" @click="handleView(row)">
                查看
              </t-button>
              <t-button theme="danger" variant="text" size="small" @click="handleDelete(row)">
                删除
              </t-button>
              <t-dropdown>
                <t-button theme="default" variant="text" size="small">
                  更多
                  <template #suffix><t-icon name="chevron-down" /></template>
                </t-button>
                <t-dropdown-menu>
                  <t-dropdown-item @click="handleExport(row, 'json')">导出JSON</t-dropdown-item>
                  <t-dropdown-item @click="handleExport(row, 'csv')">导出CSV</t-dropdown-item>
                </t-dropdown-menu>
              </t-dropdown>
            </t-space>
          </template>
        </t-table>
      </t-loading>

      <!-- Batch Actions -->
      <div v-if="selectedRowKeys.length > 0" class="batch-actions">
        <t-space>
          <span>已选择 {{ selectedRowKeys.length }} 项</span>
          <t-button theme="danger" size="small" @click="handleBatchDelete">
            批量删除
          </t-button>
          <t-button theme="primary" size="small" @click="handleCompare" :disabled="selectedRowKeys.length < 2">
            对比结果
          </t-button>
          <t-button theme="default" size="small" @click="selectedRowKeys = []">
            取消选择
          </t-button>
        </t-space>
      </div>
    </t-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useChunkingStore } from '@/stores/chunkingStore'
import { MessagePlugin, DialogPlugin } from 'tdesign-vue-next'

const chunkingStore = useChunkingStore()

const emit = defineEmits(['view', 'compare'])

const showFilters = ref(false)
const loading = ref(false)
const historyData = ref([])
const selectedRowKeys = ref([])
const filters = ref({
  document_name: '',
  strategy: null
})

const columns = [
  { colKey: 'row-select', type: 'multiple', width: 50 },
  { colKey: 'document_name', title: '文档名称', width: 200 },
  { colKey: 'strategy_type', title: '策略', width: 120 },
  { colKey: 'total_chunks', title: '块数', width: 100 },
  { colKey: 'processing_time', title: '耗时', width: 100 },
  { colKey: 'status', title: '状态', width: 100 },
  { colKey: 'created_at', title: '创建时间', width: 180 },
  { colKey: 'operation', title: '操作', width: 200, fixed: 'right' }
]

const paginationProps = computed(() => ({
  current: chunkingStore.historyPage,
  pageSize: chunkingStore.historyPageSize,
  total: chunkingStore.historyTotalCount,
  showJumper: true
}))

const loadHistory = async () => {
  loading.value = true
  try {
    await chunkingStore.loadHistory(chunkingStore.historyPage, filters.value)
    historyData.value = chunkingStore.historyList
  } catch (error) {
    MessagePlugin.error('加载历史失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  loadHistory()
}

const handleRefresh = () => {
  filters.value = { document_name: '', strategy: null }
  loadHistory()
}

const handlePageChange = ({ current, pageSize }) => {
  chunkingStore.historyPage = current
  chunkingStore.historyPageSize = pageSize
  loadHistory()
}

const handleSelectChange = (selectedKeys) => {
  selectedRowKeys.value = selectedKeys
}

const handleView = (row) => {
  emit('view', row.result_id)
}

const handleDelete = (row) => {
  const dialog = DialogPlugin.confirm({
    header: '确认删除',
    body: `确定要删除 "${row.document_name}" 的分块结果吗？此操作将删除数据库记录和文件，无法恢复。`,
    theme: 'warning',
    confirmBtn: {
      content: '删除',
      theme: 'danger'
    },
    cancelBtn: '取消',
    onConfirm: async () => {
      try {
        await chunkingStore.deleteResult(row.result_id)
        dialog.destroy()
        MessagePlugin.success('删除成功')
        await loadHistory()
      } catch (error) {
        MessagePlugin.error(error.message || '删除失败')
      }
    }
  })
}

const handleExport = async (row, format) => {
  try {
    const response = await chunkingStore.$api.get(`/chunking/export/${row.result_id}`, {
      params: { format },
      responseType: 'blob'
    })
    
    // Trigger download
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${row.document_name}_${row.strategy_type}.${format}`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    
    MessagePlugin.success('导出成功')
  } catch (error) {
    MessagePlugin.error('导出失败')
  }
}

const handleCompare = () => {
  if (selectedRowKeys.value.length < 2) {
    MessagePlugin.warning('请至少选择2个结果进行对比')
    return
  }
  emit('compare', selectedRowKeys.value)
}

const handleBatchDelete = () => {
  const count = selectedRowKeys.value.length
  const dialog = DialogPlugin.confirm({
    header: '确认批量删除',
    body: `确定要删除选中的 ${count} 条分块结果吗？此操作将删除数据库记录和文件，无法恢复。`,
    theme: 'warning',
    confirmBtn: {
      content: '删除',
      theme: 'danger'
    },
    cancelBtn: '取消',
    onConfirm: async () => {
      try {
        const response = await chunkingStore.batchDeleteResults(selectedRowKeys.value)
        dialog.destroy()
        if (response.data?.deleted_count > 0) {
          MessagePlugin.success(`成功删除 ${response.data.deleted_count} 条记录`)
          selectedRowKeys.value = []
          await loadHistory()
        }
        if (response.data?.failed_ids?.length > 0) {
          MessagePlugin.warning(`${response.data.failed_ids.length} 条记录删除失败`)
        }
      } catch (error) {
        MessagePlugin.error(error.message || '批量删除失败')
      }
    }
  })
}

const handleClearAll = () => {
  const total = chunkingStore.historyTotalCount
  const dialog = DialogPlugin.confirm({
    header: '确认清空',
    body: `确定要清空全部 ${total} 条分块历史记录吗？此操作将删除所有数据库记录和文件，无法恢复。`,
    theme: 'danger',
    confirmBtn: {
      content: '清空全部',
      theme: 'danger'
    },
    cancelBtn: '取消',
    onConfirm: async () => {
      try {
        // 获取所有记录的ID
        const allIds = historyData.value.map(item => item.result_id)
        const response = await chunkingStore.batchDeleteResults(allIds)
        dialog.destroy()
        if (response.data?.deleted_count > 0) {
          MessagePlugin.success(`成功清空 ${response.data.deleted_count} 条记录`)
          selectedRowKeys.value = []
          await loadHistory()
        }
      } catch (error) {
        MessagePlugin.error(error.message || '清空失败')
      }
    }
  })
}

const getStrategyLabel = (type) => {
  const labels = {
    character: '按字数',
    paragraph: '按段落',
    heading: '按标题',
    semantic: '按语义'
  }
  return labels[type] || type
}

const getStatusTheme = (status) => {
  const themes = {
    completed: 'success',
    partial: 'warning',
    failed: 'danger'
  }
  return themes[status] || 'default'
}

const getStatusLabel = (status) => {
  const labels = {
    completed: '已完成',
    partial: '部分完成',
    failed: '失败'
  }
  return labels[status] || status
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

const formatParams = (row) => {
  if (!row.statistics || !row.statistics.parameters) {
    return '无参数信息'
  }
  
  const params = row.statistics.parameters
  const strategy = row.strategy_type
  
  // 根据不同策略格式化参数
  let paramLines = []
  
  switch (strategy) {
    case 'character':
      paramLines = [
        `块大小: ${params.chunk_size || '-'} 字符`,
        `重叠: ${params.overlap || 0} 字符`
      ]
      break
      
    case 'paragraph':
      paramLines = [
        `最大块大小: ${params.max_chunk_size || '-'} 字符`,
        `合并小段落: ${params.merge_small_paragraphs ? '是' : '否'}`
      ]
      if (params.min_paragraph_length) {
        paramLines.push(`最小段落长度: ${params.min_paragraph_length} 字符`)
      }
      break
      
    case 'heading':
      paramLines = [
        `最大块大小: ${params.max_chunk_size || '-'} 字符`,
        `保留标题层级: ${params.preserve_hierarchy ? '是' : '否'}`
      ]
      if (params.max_heading_level) {
        paramLines.push(`最大标题级别: H${params.max_heading_level}`)
      }
      break
      
    case 'semantic':
      paramLines = [
        `相似度阈值: ${params.similarity_threshold || '-'}`,
        `最小块大小: ${params.min_chunk_size || '-'} 字符`
      ]
      if (params.max_chunk_size) {
        paramLines.push(`最大块大小: ${params.max_chunk_size} 字符`)
      }
      break
      
    default:
      // 通用参数显示
      Object.entries(params).forEach(([key, value]) => {
        paramLines.push(`${key}: ${value}`)
      })
  }
  
  // 添加版本信息
  if (row.version && row.version > 1) {
    paramLines.unshift(`版本: v${row.version}`)
    if (row.replacement_reason) {
      paramLines.push(`变更原因: ${row.replacement_reason}`)
    }
  }
  
  return paramLines.join('\n')
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.filters-section {
  margin-bottom: 16px;
  padding: 16px;
  background-color: var(--td-bg-color-container);
  border-radius: 3px;
}

.batch-actions {
  margin-top: 16px;
  padding: 12px;
  background-color: var(--td-brand-color-1);
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
