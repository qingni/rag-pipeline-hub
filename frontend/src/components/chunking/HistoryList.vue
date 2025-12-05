<template>
  <div class="history-list">
    <t-card title="分块历史" :bordered="false">
      <template #actions>
        <t-space>
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
            <t-tag theme="primary" variant="light">{{ getStrategyLabel(row.strategy_type) }}</t-tag>
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

const handleDelete = async (row) => {
  const confirmed = await DialogPlugin.confirm({
    header: '确认删除',
    body: `确定要删除 "${row.document_name}" 的分块结果吗？`,
    confirmBtn: '删除',
    cancelBtn: '取消'
  })

  if (confirmed) {
    try {
      await chunkingStore.deleteResult(row.result_id)
      MessagePlugin.success('删除成功')
      loadHistory()
    } catch (error) {
      MessagePlugin.error('删除失败')
    }
  }
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
