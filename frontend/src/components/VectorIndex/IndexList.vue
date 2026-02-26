<template>
  <div class="index-list">
    <t-card :bordered="false">
      <template #header>
        <div class="list-header">
          <span class="list-title">索引列表</span>
          <t-space>
            <t-input
              v-model="searchKeyword"
              placeholder="搜索索引名称"
              clearable
              size="small"
              style="width: 200px"
            >
              <template #prefix-icon><t-icon name="search" /></template>
            </t-input>
            <t-button variant="outline" size="small" @click="$emit('refresh')">
              <template #icon><t-icon name="refresh" /></template>
              刷新
            </t-button>
          </t-space>
        </div>
      </template>

      <t-table
        :data="filteredIndexes"
        :columns="columns"
        :loading="loading"
        row-key="id"
        stripe
        hover
        size="small"
        :max-height="500"
      >
        <!-- 索引名称 -->
        <template #index_name="{ row }">
          <div class="name-cell">
            <span class="name-text">{{ row.index_name }}</span>
            <t-space size="4px" style="margin-top: 2px">
              <t-tag v-if="row.has_sparse" theme="warning" variant="light" size="small">
                稀疏向量
              </t-tag>
              <t-tag v-if="row.source_document_name" variant="light" size="small">
                {{ row.source_document_name }}
              </t-tag>
            </t-space>
          </div>
        </template>

        <!-- 状态 -->
        <template #status="{ row }">
          <t-tag :theme="getStatusTheme(row.status)" variant="light" size="small">
            {{ getStatusText(row.status) }}
          </t-tag>
        </template>

        <!-- 向量数量 -->
        <template #vector_count="{ row }">
          <span class="mono-value">{{ formatNumber(row.vector_count || 0) }}</span>
        </template>

        <!-- 操作 -->
        <template #operation="{ row }">
          <t-space size="small">
            <t-button variant="text" size="small" theme="primary" @click="$emit('view', row)">
              详情
            </t-button>
            <t-button variant="text" size="small" theme="primary" @click="$emit('search', row)">
              检索
            </t-button>
            <t-button variant="text" size="small" theme="danger" @click="$emit('delete', row)">
              删除
            </t-button>
          </t-space>
        </template>
      </t-table>
    </t-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  /** 索引列表数据 */
  indexes: {
    type: Array,
    default: () => []
  },
  /** 加载状态 */
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['view', 'search', 'delete', 'refresh'])

const searchKeyword = ref('')

const columns = [
  { colKey: 'index_name', title: '索引名称', width: 220, cell: 'index_name' },
  { colKey: 'algorithm_type', title: '算法', width: 90 },
  { colKey: 'dimension', title: '维度', width: 70 },
  { colKey: 'vector_count', title: '向量数', width: 90, cell: 'vector_count' },
  { colKey: 'metric_type', title: '度量', width: 80 },
  { colKey: 'status', title: '状态', width: 80, cell: 'status' },
  { colKey: 'operation', title: '操作', width: 170, cell: 'operation', fixed: 'right' }
]

const filteredIndexes = computed(() => {
  if (!searchKeyword.value) return props.indexes
  const keyword = searchKeyword.value.toLowerCase()
  return props.indexes.filter(idx =>
    idx.index_name?.toLowerCase().includes(keyword) ||
    idx.source_document_name?.toLowerCase().includes(keyword)
  )
})

const getStatusTheme = (status) => {
  const map = { BUILDING: 'warning', READY: 'success', UPDATING: 'primary', ERROR: 'danger' }
  return map[status] || 'default'
}

const getStatusText = (status) => {
  const map = { BUILDING: '构建中', READY: '就绪', UPDATING: '更新中', ERROR: '错误' }
  return map[status] || status
}

const formatNumber = (num) => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}
</script>

<style scoped>
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.list-title {
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

.mono-value {
  font-family: monospace;
  font-weight: 500;
}
</style>
