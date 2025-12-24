<template>
  <t-card title="索引列表" :bordered="false">
    <template #actions>
      <t-space>
        <t-input
          v-model="searchKeyword"
          placeholder="搜索索引名称"
          clearable
          style="width: 200px"
        >
          <template #prefix-icon><search-icon /></template>
        </t-input>
        <t-button variant="text" @click="handleRefresh">
          <template #icon><refresh-icon /></template>
          刷新
        </t-button>
      </t-space>
    </template>

    <t-table
      :data="filteredIndexes"
      :columns="columns"
      :loading="loading"
      row-key="id"
      stripe
      hover
      :pagination="pagination"
      @page-change="handlePageChange"
    >
      <template #index_name="{ row }">
        <div class="index-name-cell">
          <span class="name">{{ row.index_name }}</span>
          <t-tag v-if="row.source_document_name" size="small" variant="light" theme="primary">
            {{ row.source_document_name }}
          </t-tag>
        </div>
      </template>

      <template #status="{ row }">
        <t-tag
          :theme="getStatusTheme(row.status)"
          variant="light"
        >
          <template #icon>
            <loading-icon v-if="row.status === 'BUILDING'" class="spin-icon" />
            <check-circle-icon v-else-if="row.status === 'READY'" />
            <close-circle-icon v-else-if="row.status === 'ERROR'" />
          </template>
          {{ getStatusText(row.status) }}
        </t-tag>
      </template>

      <template #index_type="{ row }">
        <t-tag variant="outline">{{ row.index_type }}</t-tag>
      </template>

      <template #algorithm_type="{ row }">
        <t-tag variant="outline" theme="warning">{{ row.algorithm_type || 'FLAT' }}</t-tag>
      </template>

      <template #metric_type="{ row }">
        <t-tag variant="outline" theme="success">{{ row.metric_type }}</t-tag>
      </template>

      <template #vector_count="{ row }">
        <span class="vector-count">{{ formatNumber(row.vector_count || 0) }}</span>
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
            :disabled="row.status !== 'READY'"
            @click="handleSelect(row)"
          >
            选择
          </t-button>
          <t-dropdown
            :options="getMoreOptions(row)"
            @click="(item) => handleMoreAction(item, row)"
          >
            <t-button variant="text" size="small">
              更多
              <template #suffix><chevron-down-icon /></template>
            </t-button>
          </t-dropdown>
        </t-space>
      </template>
    </t-table>
  </t-card>
</template>

<script setup>
import { ref, computed } from 'vue';
import { 
  RefreshIcon, 
  SearchIcon,
  LoadingIcon,
  CheckCircleIcon,
  CloseCircleIcon,
  ChevronDownIcon
} from 'tdesign-icons-vue-next';
import { storeToRefs } from 'pinia';
import { useVectorIndexStore } from '../../stores/vectorIndexStore';
import { MessagePlugin, DialogPlugin } from 'tdesign-vue-next';

const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['select', 'delete', 'refresh']);

const vectorIndexStore = useVectorIndexStore();
const { indexes } = storeToRefs(vectorIndexStore);

const searchKeyword = ref('');

const columns = [
  {
    colKey: 'id',
    title: 'ID',
    width: 60
  },
  {
    colKey: 'index_name',
    title: '索引名称',
    width: 200,
    cell: 'index_name'
  },
  {
    colKey: 'index_type',
    title: '提供者',
    width: 90,
    cell: 'index_type'
  },
  {
    colKey: 'algorithm_type',
    title: '算法',
    width: 100,
    cell: 'algorithm_type'
  },
  {
    colKey: 'dimension',
    title: '维度',
    width: 70
  },
  {
    colKey: 'metric_type',
    title: '度量',
    width: 90,
    cell: 'metric_type'
  },
  {
    colKey: 'vector_count',
    title: '向量数',
    width: 90,
    cell: 'vector_count'
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
    width: 150,
    cell: 'created_at'
  },
  {
    colKey: 'operation',
    title: '操作',
    width: 130,
    cell: 'operation',
    fixed: 'right'
  }
];

// 过滤后的索引列表
const filteredIndexes = computed(() => {
  if (!searchKeyword.value) {
    return indexes.value;
  }
  const keyword = searchKeyword.value.toLowerCase();
  return indexes.value.filter(index => 
    index.index_name?.toLowerCase().includes(keyword) ||
    index.source_document_name?.toLowerCase().includes(keyword)
  );
});

const pagination = computed(() => ({
  total: filteredIndexes.value.length,
  pageSize: 10,
  current: 1
}));

const getStatusTheme = (status) => {
  const themeMap = {
    'BUILDING': 'warning',
    'READY': 'success',
    'UPDATING': 'primary',
    'ERROR': 'danger'
  };
  return themeMap[status] || 'default';
};

const getStatusText = (status) => {
  const textMap = {
    'BUILDING': '构建中',
    'READY': '就绪',
    'UPDATING': '更新中',
    'ERROR': '错误'
  };
  return textMap[status] || status;
};

const formatDate = (dateString) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const formatNumber = (num) => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
};

const getMoreOptions = (row) => {
  const options = [
    { content: '查看详情', value: 'detail' },
    { content: '查看历史', value: 'history' }
  ];
  
  if (row.status === 'READY' && row.index_type === 'FAISS') {
    options.push({ content: '持久化', value: 'persist' });
  }
  
  options.push({ content: '删除', value: 'delete', theme: 'error' });
  
  return options;
};

const handleMoreAction = async (item, row) => {
  switch (item.value) {
    case 'detail':
      // 显示详情弹窗
      DialogPlugin.alert({
        header: '索引详情',
        body: `
          <div style="line-height: 2;">
            <p><strong>ID:</strong> ${row.id}</p>
            <p><strong>名称:</strong> ${row.index_name}</p>
            <p><strong>提供者:</strong> ${row.index_type}</p>
            <p><strong>算法:</strong> ${row.algorithm_type || 'FLAT'}</p>
            <p><strong>维度:</strong> ${row.dimension}</p>
            <p><strong>度量类型:</strong> ${row.metric_type}</p>
            <p><strong>向量数量:</strong> ${row.vector_count || 0}</p>
            <p><strong>状态:</strong> ${row.status}</p>
            <p><strong>命名空间:</strong> ${row.namespace || 'default'}</p>
            ${row.source_document_name ? `<p><strong>源文档:</strong> ${row.source_document_name}</p>` : ''}
            ${row.source_model ? `<p><strong>源模型:</strong> ${row.source_model}</p>` : ''}
            ${row.error_message ? `<p style="color: red;"><strong>错误:</strong> ${row.error_message}</p>` : ''}
          </div>
        `,
        confirmBtn: '关闭'
      });
      break;
    case 'history':
      // TODO: 显示操作历史
      MessagePlugin.info('操作历史功能开发中');
      break;
    case 'persist':
      try {
        await vectorIndexStore.persistIndex(row.id);
        MessagePlugin.success('索引持久化成功');
      } catch (error) {
        MessagePlugin.error('持久化失败: ' + (error.message || '未知错误'));
      }
      break;
    case 'delete':
      handleDelete(row.id);
      break;
  }
};

const handleSelect = (row) => {
  emit('select', row);
};

const handleDelete = (id) => {
  const dialog = DialogPlugin.confirm({
    header: '确认删除',
    body: '确定要删除这个索引吗？此操作不可恢复。',
    confirmBtn: { theme: 'danger', content: '删除' },
    onConfirm: async () => {
      try {
        await vectorIndexStore.removeIndex(id);
        MessagePlugin.success('索引删除成功');
        dialog.destroy();
      } catch (error) {
        MessagePlugin.error('删除失败: ' + (error.message || '未知错误'));
      }
    }
  });
};

const handleRefresh = () => {
  emit('refresh');
};

const handlePageChange = (pageInfo) => {
  console.log('Page changed:', pageInfo);
};
</script>

<style scoped>
.index-name-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.index-name-cell .name {
  font-weight: 500;
}

.vector-count {
  font-family: monospace;
  font-weight: 500;
}

.spin-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

:deep(.t-table) {
  font-size: 13px;
}
</style>
