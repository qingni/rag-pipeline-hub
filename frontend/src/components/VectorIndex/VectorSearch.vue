<template>
  <t-card title="向量搜索" :bordered="false">
    <template #subtitle>
      <t-space>
        <span>索引: {{ index.index_name }}</span>
        <t-tag theme="success" variant="light">{{ index.status }}</t-tag>
      </t-space>
    </template>

    <t-form
      ref="formRef"
      :data="searchData"
      label-width="100px"
      @submit="handleSearch"
    >
      <t-form-item label="查询向量" name="query_vector">
        <t-textarea
          v-model="vectorInput"
          placeholder="输入向量 (逗号分隔的数字，例如: 0.1, 0.2, 0.3, ...)"
          :autosize="{ minRows: 3, maxRows: 5 }"
        />
        <div class="form-tip">
          或者
          <t-button
            variant="text"
            theme="primary"
            size="small"
            @click="generateRandomVector"
          >
            生成随机向量
          </t-button>
        </div>
      </t-form-item>

      <t-form-item label="返回数量" name="top_k">
        <t-input-number
          v-model="searchData.top_k"
          :min="1"
          :max="100"
          style="width: 200px"
        />
      </t-form-item>

      <t-form-item label="保存结果" name="save_result">
        <t-switch v-model="searchData.save_result" />
        <span class="form-tip" style="margin-left: 8px">
          保存搜索结果到文件
        </span>
      </t-form-item>

      <t-form-item>
        <t-space>
          <t-button
            theme="primary"
            type="submit"
            :loading="loading"
            :disabled="!isVectorValid"
          >
            <template #icon><search-icon /></template>
            搜索
          </t-button>
          <t-button variant="outline" @click="handleReset">
            重置
          </t-button>
        </t-space>
      </t-form-item>
    </t-form>

    <!-- 搜索结果 -->
    <t-divider v-if="searchResults" />
    
    <div v-if="searchResults" class="search-results">
      <div class="result-header">
        <h3>搜索结果</h3>
        <t-space>
          <t-tag theme="primary">
            找到 {{ searchResults.results_count }} 个结果
          </t-tag>
          <t-tag theme="success">
            耗时 {{ searchResults.search_time_ms.toFixed(2) }}ms
          </t-tag>
        </t-space>
      </div>

      <t-table
        :data="searchResults.results"
        :columns="resultColumns"
        row-key="vector_id"
        size="small"
        stripe
        :max-height="400"
      >
        <template #score="{ row }">
          <t-progress
            :percentage="(row.score * 100).toFixed(2)"
            :label="row.score.toFixed(4)"
            theme="success"
          />
        </template>

        <template #metadata="{ row }">
          <t-popup
            placement="left"
            :content="JSON.stringify(row.metadata, null, 2)"
          >
            <t-button variant="text" size="small">
              查看详情
            </t-button>
          </t-popup>
        </template>
      </t-table>
    </div>
  </t-card>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue';
import { SearchIcon } from 'tdesign-icons-vue-next';
import { storeToRefs } from 'pinia';
import { useVectorIndexStore } from '../../stores/vectorIndexStore';

const props = defineProps({
  index: {
    type: Object,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['search']);

const vectorIndexStore = useVectorIndexStore();
const { searchResults } = storeToRefs(vectorIndexStore);

const formRef = ref(null);
const vectorInput = ref('');

const searchData = reactive({
  query_vector: [],
  top_k: 10,
  save_result: false
});

const resultColumns = [
  {
    colKey: 'vector_id',
    title: '向量 ID',
    width: 300,
    ellipsis: true
  },
  {
    colKey: 'score',
    title: '相似度',
    width: 200,
    cell: 'score'
  },
  {
    colKey: 'metadata',
    title: '元数据',
    width: 150,
    cell: 'metadata'
  }
];

const isVectorValid = computed(() => {
  if (!vectorInput.value) return false;
  
  try {
    const vector = parseVector(vectorInput.value);
    return vector.length === props.index.dimension;
  } catch {
    return false;
  }
});

const parseVector = (input) => {
  const parts = input.split(',').map(s => s.trim()).filter(s => s);
  return parts.map(p => parseFloat(p));
};

const generateRandomVector = () => {
  const vector = Array.from(
    { length: props.index.dimension },
    () => (Math.random() - 0.5).toFixed(4)
  );
  vectorInput.value = vector.join(', ');
};

const handleSearch = async (e) => {
  e?.preventDefault();
  
  if (!isVectorValid.value) {
    return;
  }

  searchData.query_vector = parseVector(vectorInput.value);
  emit('search', { ...searchData });
};

const handleReset = () => {
  vectorInput.value = '';
  searchData.query_vector = [];
  searchData.top_k = 10;
  searchData.save_result = false;
  vectorIndexStore.clearSearchResults();
};

// 当索引变化时重置
watch(() => props.index, () => {
  handleReset();
});
</script>

<style scoped>
.form-tip {
  margin-top: 4px;
  font-size: 12px;
  color: var(--td-text-color-placeholder);
}

.search-results {
  margin-top: 24px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.result-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

:deep(.t-progress) {
  width: 100%;
}
</style>
