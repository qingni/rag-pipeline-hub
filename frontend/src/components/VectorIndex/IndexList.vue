<template>
  <t-card title="索引列表" :bordered="false">
    <template #actions>
      <t-button variant="text" @click="handleRefresh">
        <template #icon><refresh-icon /></template>
        刷新
      </t-button>
    </template>

    <t-table
      :data="indexes"
      :columns="columns"
      :loading="loading"
      row-key="id"
      stripe
      hover
      :pagination="pagination"
      @page-change="handlePageChange"
    >
      <template #status="{ row }">
        <t-tag
          :theme="getStatusTheme(row.status)"
          variant="light"
        >
          {{ getStatusText(row.status) }}
        </t-tag>
      </template>

      <template #index_type="{ row }">
        <t-tag variant="outline">{{ row.index_type }}</t-tag>
      </template>

      <template #metric_type="{ row }">
        <t-tag variant="outline" theme="success">{{ row.metric_type }}</t-tag>
      </template>

      <template #created_at="{ row }">
        {{ formatDate(row.created_at) }}
      </template>

      <template #operation="{ row }">
        <t-space>
          <t-button
            theme="primary"
            variant="text"
            size="small"
            @click="handleSelect(row)"
          >
            选择
          </t-button>
          <t-popconfirm
            content="确定要删除这个索引吗？"
            @confirm="handleDelete(row.id)"
          >
            <t-button
              theme="danger"
              variant="text"
              size="small"
            >
              删除
            </t-button>
          </t-popconfirm>
        </t-space>
      </template>
    </t-table>
  </t-card>
</template>

<script setup>
import { computed } from 'vue';
import { RefreshIcon } from 'tdesign-icons-vue-next';
import { storeToRefs } from 'pinia';
import { useVectorIndexStore } from '../../stores/vectorIndexStore';

const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['select', 'delete', 'refresh']);

const vectorIndexStore = useVectorIndexStore();
const { indexes } = storeToRefs(vectorIndexStore);

const columns = [
  {
    colKey: 'id',
    title: 'ID',
    width: 80
  },
  {
    colKey: 'index_name',
    title: '索引名称',
    width: 200
  },
  {
    colKey: 'index_type',
    title: '类型',
    width: 120,
    cell: 'index_type'
  },
  {
    colKey: 'dimension',
    title: '维度',
    width: 100
  },
  {
    colKey: 'metric_type',
    title: '度量',
    width: 120,
    cell: 'metric_type'
  },
  {
    colKey: 'status',
    title: '状态',
    width: 100,
    cell: 'status'
  },
  {
    colKey: 'created_at',
    title: '创建时间',
    width: 180,
    cell: 'created_at'
  },
  {
    colKey: 'operation',
    title: '操作',
    width: 150,
    cell: 'operation'
  }
];

const pagination = computed(() => ({
  total: indexes.value.length,
  pageSize: 10,
  current: 1
}));

const getStatusTheme = (status) => {
  const themeMap = {
    'CREATED': 'default',
    'BUILDING': 'warning',
    'READY': 'success',
    'DELETED': 'danger'
  };
  return themeMap[status] || 'default';
};

const getStatusText = (status) => {
  const textMap = {
    'CREATED': '已创建',
    'BUILDING': '构建中',
    'READY': '就绪',
    'DELETED': '已删除'
  };
  return textMap[status] || status;
};

const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const handleSelect = (row) => {
  emit('select', row);
};

const handleDelete = (id) => {
  emit('delete', id);
};

const handleRefresh = () => {
  emit('refresh');
};

const handlePageChange = (pageInfo) => {
  // 分页逻辑（如果需要服务端分页）
  console.log('Page changed:', pageInfo);
};
</script>

<style scoped>
:deep(.t-table) {
  font-size: 14px;
}
</style>
