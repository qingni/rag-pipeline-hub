<template>
  <div class="index-history">
    <t-card :bordered="false" class="history-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">索引历史记录</span>
          <t-space>
            <t-button variant="text" size="small" @click="refresh">
              <template #icon><RefreshIcon :size="14" /></template>
              刷新
            </t-button>
          </t-space>
        </div>
      </template>

      <t-table
        :data="historyData"
        :columns="columns"
        :loading="loading"
        row-key="id"
        stripe
        hover
        :pagination="paginationConfig"
        @page-change="handlePageChange"
      >
        <!-- 索引名称列 -->
        <template #index_name="{ row }">
          <div class="index-name-cell">
            <span class="name">{{ row.index_name }}</span>
            <t-tag v-if="row.source_document_name" size="small" variant="light" theme="primary">
              {{ truncate(row.source_document_name, 20) }}
            </t-tag>
          </div>
        </template>

        <!-- 状态列 -->
        <template #status="{ row }">
          <t-tag :theme="getStatusTheme(row.status)" variant="light">
            <template v-if="row.status === 'BUILDING'" #icon>
              <LoadingIcon class="spin-icon" :size="12" />
            </template>
            {{ getStatusText(row.status) }}
          </t-tag>
        </template>

        <!-- 向量数量列 -->
        <template #vector_count="{ row }">
          <span class="vector-count">{{ formatNumber(row.vector_count || 0) }}</span>
        </template>

        <!-- 创建时间列 -->
        <template #created_at="{ row }">
          {{ formatDate(row.created_at) }}
        </template>

        <!-- 操作列 -->
        <template #operation="{ row }">
          <t-space>
            <t-button
              theme="primary"
              variant="text"
              size="small"
              @click="handleViewDetail(row)"
            >
              查看详情
            </t-button>
            <t-button
              theme="danger"
              variant="text"
              size="small"
              @click="handleDelete(row)"
            >
              删除
            </t-button>
          </t-space>
        </template>
      </t-table>
    </t-card>

    <!-- 详情抽屉 -->
    <t-drawer
      v-model:visible="detailVisible"
      header="索引详情"
      size="500px"
      :footer="false"
    >
      <div v-if="selectedIndex" class="detail-content">
        <t-descriptions :column="1" bordered>
          <t-descriptions-item label="索引ID">{{ selectedIndex.id }}</t-descriptions-item>
          <t-descriptions-item label="索引名称">{{ selectedIndex.index_name }}</t-descriptions-item>
          <t-descriptions-item label="向量数据库">
            <t-tag variant="outline">{{ selectedIndex.index_type }}</t-tag>
          </t-descriptions-item>
          <t-descriptions-item label="索引算法">
            <t-tag variant="outline" theme="warning">{{ selectedIndex.algorithm_type || 'FLAT' }}</t-tag>
          </t-descriptions-item>
          <t-descriptions-item label="向量维度">{{ selectedIndex.dimension }}</t-descriptions-item>
          <t-descriptions-item label="度量类型">{{ selectedIndex.metric_type }}</t-descriptions-item>
          <t-descriptions-item label="向量数量">
            <span class="highlight-value">{{ formatNumber(selectedIndex.vector_count || 0) }}</span>
          </t-descriptions-item>
          <t-descriptions-item label="状态">
            <t-tag :theme="getStatusTheme(selectedIndex.status)" variant="light">
              {{ getStatusText(selectedIndex.status) }}
            </t-tag>
          </t-descriptions-item>
          <t-descriptions-item label="创建时间">{{ formatDate(selectedIndex.created_at) }}</t-descriptions-item>
          <t-descriptions-item label="更新时间">{{ formatDate(selectedIndex.updated_at) }}</t-descriptions-item>
          <t-descriptions-item v-if="selectedIndex.source_document_name" label="源文档">
            {{ selectedIndex.source_document_name }}
          </t-descriptions-item>
          <t-descriptions-item v-if="selectedIndex.source_model" label="向量模型">
            {{ selectedIndex.source_model }}
          </t-descriptions-item>
          <t-descriptions-item v-if="selectedIndex.embedding_result_id" label="向量化任务ID">
            <span class="mono-text">{{ selectedIndex.embedding_result_id }}</span>
          </t-descriptions-item>
        </t-descriptions>

        <div class="drawer-actions">
          <t-button 
            theme="danger" 
            variant="outline" 
            block
            @click="handleDeleteFromDrawer"
          >
            删除此索引
          </t-button>
        </div>
      </div>
    </t-drawer>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { MessagePlugin, DialogPlugin } from 'tdesign-vue-next';
import { RefreshCw as RefreshIcon, Loader as LoadingIcon } from 'lucide-vue-next';

const props = defineProps({
  historyData: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  pagination: {
    type: Object,
    default: () => ({
      page: 1,
      pageSize: 10,
      total: 0
    })
  }
});

const emit = defineEmits(['refresh', 'view-detail', 'delete', 'page-change']);

// 状态
const detailVisible = ref(false);
const selectedIndex = ref(null);

// 表格列定义
const columns = [
  { colKey: 'id', title: 'ID', width: 60 },
  { colKey: 'index_name', title: '索引名称', width: 200, cell: 'index_name' },
  { colKey: 'index_type', title: '数据库', width: 80 },
  { colKey: 'algorithm_type', title: '算法', width: 90 },
  { colKey: 'dimension', title: '维度', width: 70 },
  { colKey: 'vector_count', title: '向量数', width: 80, cell: 'vector_count' },
  { colKey: 'status', title: '状态', width: 90, cell: 'status' },
  { colKey: 'created_at', title: '创建时间', width: 150, cell: 'created_at' },
  { colKey: 'operation', title: '操作', width: 140, cell: 'operation', fixed: 'right' }
];

// 分页配置
const paginationConfig = computed(() => ({
  total: props.pagination.total,
  pageSize: props.pagination.pageSize,
  current: props.pagination.page,
  showJumper: true,
  showPageSize: true,
  pageSizeOptions: [10, 20, 50]
}));

// 方法
const refresh = () => {
  emit('refresh');
};

const handlePageChange = ({ current, pageSize }) => {
  emit('page-change', { page: current, pageSize });
};

const handleViewDetail = (row) => {
  selectedIndex.value = row;
  detailVisible.value = true;
  emit('view-detail', row);
};

const handleDelete = (row) => {
  const dialog = DialogPlugin.confirm({
    header: '确认删除',
    body: `确定要删除索引「${row.index_name}」吗？此操作不可恢复。`,
    confirmBtn: { theme: 'danger', content: '删除' },
    onConfirm: () => {
      emit('delete', row.id);
      dialog.destroy();
    }
  });
};

const handleDeleteFromDrawer = () => {
  if (!selectedIndex.value) return;
  
  const dialog = DialogPlugin.confirm({
    header: '确认删除',
    body: `确定要删除索引「${selectedIndex.value.index_name}」吗？此操作不可恢复。`,
    confirmBtn: { theme: 'danger', content: '删除' },
    onConfirm: () => {
      emit('delete', selectedIndex.value.id);
      detailVisible.value = false;
      selectedIndex.value = null;
      dialog.destroy();
    }
  });
};

// 工具函数
const getStatusTheme = (status) => {
  const map = {
    BUILDING: 'warning',
    READY: 'success',
    UPDATING: 'primary',
    ERROR: 'danger'
  };
  return map[status] || 'default';
};

const getStatusText = (status) => {
  const map = {
    BUILDING: '构建中',
    READY: '就绪',
    UPDATING: '更新中',
    ERROR: '错误'
  };
  return map[status] || status;
};

const formatDate = (dateString) => {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const formatNumber = (num) => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toString();
};

const truncate = (str, maxLen) => {
  if (!str) return '';
  return str.length > maxLen ? str.substring(0, maxLen) + '...' : str;
};
</script>

<style scoped>
.index-history {
  width: 100%;
}

.history-card {
  background: var(--td-bg-color-container);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
}

.index-name-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.index-name-cell .name {
  font-weight: 500;
}

.vector-count {
  font-weight: 500;
  color: var(--td-brand-color);
}

.spin-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.detail-content {
  padding: 16px 0;
}

.highlight-value {
  font-weight: 600;
  color: var(--td-brand-color);
}

.mono-text {
  font-family: monospace;
  font-size: 12px;
}

.drawer-actions {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--td-component-border);
}
</style>
