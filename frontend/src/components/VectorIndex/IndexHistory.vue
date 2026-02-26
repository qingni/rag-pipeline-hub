<template>
  <div class="index-history">
    <t-card :bordered="false">
      <template #header>
        <div class="history-header">
          <span class="history-title">索引历史记录</span>
          <t-space>
            <t-button variant="outline" size="small" @click="$emit('refresh')">
              <template #icon><t-icon name="refresh" /></template>
              刷新
            </t-button>
          </t-space>
        </div>
      </template>

      <t-table
        :data="historyList"
        :columns="columns"
        :loading="loading"
        row-key="id"
        stripe
        hover
        size="small"
        :max-height="500"
        :pagination="paginationConfig"
        @page-change="handlePageChange"
      >
        <!-- UUID 短标识 -->
        <template #uuid="{ row }">
          <t-tooltip :content="row.uuid || '-'" placement="top">
            <span class="uuid-short">{{ row.uuid ? row.uuid.substring(0, 8) : '-' }}</span>
          </t-tooltip>
        </template>

        <!-- 索引名称 -->
        <template #index_name="{ row }">
          <div class="name-cell">
            <span class="name-text">{{ row.index_name }}</span>
            <span v-if="row.source_model" class="name-meta">{{ row.source_model }}</span>
          </div>
        </template>

        <!-- 状态 -->
        <template #status="{ row }">
          <t-tag :theme="getStatusTheme(row.status)" variant="light" size="small">
            {{ getStatusText(row.status) }}
          </t-tag>
        </template>

        <!-- 创建时间 -->
        <template #created_at="{ row }">
          {{ formatDate(row.created_at) }}
        </template>

        <!-- 操作 -->
        <template #operation="{ row }">
          <t-space size="small">
            <t-button variant="text" size="small" theme="primary" @click="$emit('view', row)">
              查看详情
            </t-button>
            <t-popconfirm
              content="确定要删除这条历史记录吗？"
              @confirm="$emit('delete', row.id)"
            >
              <t-button variant="text" size="small" theme="danger">
                删除
              </t-button>
            </t-popconfirm>
          </t-space>
        </template>
      </t-table>

      <!-- 空状态 -->
      <t-empty v-if="!loading && historyList.length === 0" description="暂无历史记录" />
    </t-card>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  /** 历史记录列表 */
  historyList: {
    type: Array,
    default: () => []
  },
  /** 总条数 */
  total: {
    type: Number,
    default: 0
  },
  /** 加载状态 */
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['view', 'delete', 'refresh', 'page-change'])

const currentPage = ref(1)
const pageSize = ref(10)

const columns = [
  { colKey: 'uuid', title: 'ID', width: 100, cell: 'uuid' },
  { colKey: 'index_name', title: '索引名称', width: 200, cell: 'index_name' },
  { colKey: 'index_type', title: '数据库', width: 80 },
  { colKey: 'metric_type', title: '度量类型', width: 100 },
  { colKey: 'algorithm_type', title: '算法', width: 80 },
  { colKey: 'dimension', title: '维度', width: 70 },
  { colKey: 'vector_count', title: '向量数', width: 80 },
  { colKey: 'status', title: '状态', width: 80, cell: 'status' },
  { colKey: 'created_at', title: '创建时间', width: 140, cell: 'created_at' },
  { colKey: 'operation', title: '操作', width: 150, cell: 'operation', fixed: 'right' }
]

const paginationConfig = computed(() => ({
  total: props.total || props.historyList.length,
  current: currentPage.value,
  pageSize: pageSize.value
}))

const handlePageChange = (pageInfo) => {
  currentPage.value = pageInfo.current
  pageSize.value = pageInfo.pageSize
  emit('page-change', pageInfo)
}

const getStatusTheme = (status) => {
  const map = { BUILDING: 'warning', READY: 'success', UPDATING: 'primary', ERROR: 'danger' }
  return map[status] || 'default'
}

const getStatusText = (status) => {
  const map = { BUILDING: '构建中', READY: '就绪', UPDATING: '更新中', ERROR: '错误' }
  return map[status] || status
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  // 后端返回的是 UTC 时间，如果没有时区标识则添加 'Z' 确保正确解析
  let str = dateString
  if (typeof str === 'string' && !str.endsWith('Z') && !str.includes('+') && !str.includes('-', 10)) {
    str = str + 'Z'
  }
  return new Date(str).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.uuid-short {
  font-family: 'SF Mono', 'Menlo', 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  color: var(--td-text-color-secondary);
  cursor: default;
  padding: 2px 6px;
  background-color: var(--td-bg-color-container-hover);
  border-radius: 4px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-title {
  font-size: 16px;
  font-weight: 600;
}

.name-cell {
  display: flex;
  flex-direction: column;
}

.name-text {
  font-weight: 500;
}

.name-meta {
  font-size: 12px;
  color: var(--td-text-color-placeholder);
}
</style>
