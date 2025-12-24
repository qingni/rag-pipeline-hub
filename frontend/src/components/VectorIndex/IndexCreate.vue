<template>
  <t-dialog
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    header="创建向量索引"
    width="700px"
    :confirm-btn="{
      content: '创建',
      theme: 'primary',
      loading: loading
    }"
    @confirm="handleConfirm"
    @close="handleClose"
  >
    <!-- 创建方式选择 -->
    <t-tabs v-model="createMode" class="create-tabs">
      <t-tab-panel value="manual" label="手动创建">
        <t-form
          ref="manualFormRef"
          :data="formData"
          :rules="rules"
          label-width="100px"
          class="create-form"
        >
          <t-form-item label="索引名称" name="index_name">
            <t-input
              v-model="formData.index_name"
              placeholder="请输入索引名称（字母、数字、下划线）"
              clearable
            />
          </t-form-item>

          <t-form-item label="向量维度" name="dimension">
            <t-select
              v-model="formData.dimension"
              placeholder="请选择向量维度"
              filterable
            >
              <t-option
                v-for="dim in validDimensions"
                :key="dim"
                :value="dim"
                :label="`${dim} 维`"
              >
                <div class="dimension-option">
                  <span>{{ dim }} 维</span>
                  <span class="dim-hint">{{ getDimensionHint(dim) }}</span>
                </div>
              </t-option>
            </t-select>
          </t-form-item>

          <t-form-item label="索引类型" name="index_type">
            <t-radio-group v-model="formData.index_type">
              <t-radio value="FAISS">
                FAISS
                <span class="radio-desc">（本地内存索引，快速）</span>
              </t-radio>
              <t-radio value="MILVUS">
                Milvus
                <span class="radio-desc">（分布式向量数据库，推荐）</span>
              </t-radio>
            </t-radio-group>
          </t-form-item>

          <t-form-item label="算法类型" name="algorithm_type">
            <t-select
              v-model="formData.algorithm_type"
              placeholder="请选择索引算法"
            >
              <t-option value="FLAT" label="FLAT（暴力搜索）">
                <div>
                  <div>FLAT（暴力搜索）</div>
                  <div class="option-desc">精确但较慢，适合小数据集</div>
                </div>
              </t-option>
              <t-option value="IVF_FLAT" label="IVF_FLAT（倒排索引）">
                <div>
                  <div>IVF_FLAT（倒排索引）</div>
                  <div class="option-desc">平衡精度和速度</div>
                </div>
              </t-option>
              <t-option value="HNSW" label="HNSW（图索引）">
                <div>
                  <div>HNSW（图索引）</div>
                  <div class="option-desc">高性能，适合大数据集</div>
                </div>
              </t-option>
            </t-select>
          </t-form-item>

          <t-form-item label="度量类型" name="metric_type">
            <t-select
              v-model="formData.metric_type"
              placeholder="请选择相似度度量类型"
            >
              <t-option value="cosine" label="余弦相似度 (Cosine)">
                <div>
                  <div>余弦相似度 (Cosine)</div>
                  <div class="option-desc">适用于文本、图像嵌入</div>
                </div>
              </t-option>
              <t-option value="euclidean" label="欧氏距离 (Euclidean)">
                <div>
                  <div>欧氏距离 (Euclidean)</div>
                  <div class="option-desc">适用于空间坐标、特征向量</div>
                </div>
              </t-option>
              <t-option value="dot_product" label="点积 (Dot Product)">
                <div>
                  <div>点积 (Dot Product)</div>
                  <div class="option-desc">适用于归一化向量</div>
                </div>
              </t-option>
            </t-select>
          </t-form-item>

          <t-form-item label="描述" name="description">
            <t-textarea
              v-model="formData.description"
              placeholder="请输入索引描述（可选）"
              :autosize="{ minRows: 2, maxRows: 4 }"
            />
          </t-form-item>
        </t-form>
      </t-tab-panel>

      <t-tab-panel value="embedding" label="从向量化任务创建">
        <t-form
          ref="embeddingFormRef"
          :data="embeddingFormData"
          :rules="embeddingRules"
          label-width="100px"
          class="create-form"
        >
          <t-form-item label="向量化任务" name="embedding_result_id">
            <t-select
              v-model="embeddingFormData.embedding_result_id"
              placeholder="请选择已完成的文档向量化结果"
              :loading="loadingEmbeddings"
              filterable
              @change="handleEmbeddingSelect"
            >
              <t-option
                v-for="task in embeddingTasks"
                :key="task.result_id"
                :value="task.result_id"
                :label="task.document_name || task.result_id"
              >
                <div class="option-item">
                  <div class="option-name">{{ task.document_name || '未命名文档' }}</div>
                  <div class="option-desc">{{ task.model }} · {{ task.vector_dimension }}维 · {{ task.successful_count || 0 }}向量</div>
                </div>
              </t-option>
            </t-select>
            <t-button
              variant="text"
              theme="primary"
              size="small"
              style="margin-left: 8px"
              @click="loadEmbeddingTasks"
            >
              刷新列表
            </t-button>
          </t-form-item>

          <!-- 选中任务的详情 -->
          <div v-if="selectedEmbedding" class="embedding-details">
            <t-descriptions :column="2" bordered>
              <t-descriptions-item label="文档名称">
                {{ selectedEmbedding.document_name || '未命名' }}
              </t-descriptions-item>
              <t-descriptions-item label="向量化模型">
                {{ selectedEmbedding.model }}
              </t-descriptions-item>
              <t-descriptions-item label="向量维度">
                {{ selectedEmbedding.vector_dimension }}
              </t-descriptions-item>
              <t-descriptions-item label="向量数量">
                {{ selectedEmbedding.successful_count || 0 }}
              </t-descriptions-item>
              <t-descriptions-item label="创建时间">
                {{ formatDate(selectedEmbedding.created_at) }}
              </t-descriptions-item>
              <t-descriptions-item label="状态">
                <t-tag :theme="selectedEmbedding.status === 'SUCCESS' ? 'success' : 'warning'">
                  {{ selectedEmbedding.status === 'SUCCESS' ? '已完成' : selectedEmbedding.status }}
                </t-tag>
              </t-descriptions-item>
            </t-descriptions>
          </div>

          <t-form-item label="索引名称" name="name">
            <t-input
              v-model="embeddingFormData.name"
              placeholder="可选，留空则自动生成"
              clearable
            />
            <div class="form-tip">留空将自动使用文档名称生成索引名</div>
          </t-form-item>

          <t-form-item label="索引类型" name="provider">
            <t-radio-group v-model="embeddingFormData.provider">
              <t-radio value="FAISS">
                FAISS
                <span class="radio-desc">（本地内存索引）</span>
              </t-radio>
              <t-radio value="MILVUS">
                Milvus
                <span class="radio-desc">（分布式数据库）</span>
              </t-radio>
            </t-radio-group>
          </t-form-item>

          <t-form-item label="算法类型" name="index_type">
            <t-select
              v-model="embeddingFormData.index_type"
              placeholder="请选择索引算法"
            >
              <t-option value="FLAT" label="FLAT" />
              <t-option value="IVF_FLAT" label="IVF_FLAT" />
              <t-option value="HNSW" label="HNSW" />
            </t-select>
          </t-form-item>

          <t-form-item label="度量类型" name="metric_type">
            <t-select v-model="embeddingFormData.metric_type">
              <t-option value="cosine" label="余弦相似度" />
              <t-option value="euclidean" label="欧氏距离" />
              <t-option value="dot_product" label="点积" />
            </t-select>
          </t-form-item>
        </t-form>
      </t-tab-panel>
    </t-tabs>
  </t-dialog>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue';
import { useVectorIndexStore } from '../../stores/vectorIndexStore';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:visible', 'create', 'create-from-embedding']);

const vectorIndexStore = useVectorIndexStore();

const createMode = ref('manual');
const manualFormRef = ref(null);
const embeddingFormRef = ref(null);
const loadingEmbeddings = ref(false);
const embeddingTasks = ref([]);
const selectedEmbedding = ref(null);

// 有效的向量维度
const validDimensions = [128, 256, 512, 768, 1024, 1536, 2048, 3072, 4096];

// 手动创建表单数据
const formData = reactive({
  index_name: '',
  dimension: 1536,
  index_type: 'FAISS',
  algorithm_type: 'FLAT',
  metric_type: 'cosine',
  description: ''
});

// 从向量化任务创建表单数据
const embeddingFormData = reactive({
  embedding_result_id: '',
  name: '',
  provider: 'FAISS',
  index_type: 'FLAT',
  metric_type: 'cosine',
  index_params: {}
});

const rules = {
  index_name: [
    { required: true, message: '请输入索引名称', type: 'error' },
    { 
      pattern: /^[a-zA-Z0-9_-]+$/, 
      message: '索引名称只能包含字母、数字、下划线和连字符', 
      type: 'error' 
    }
  ],
  dimension: [
    { required: true, message: '请选择向量维度', type: 'error' }
  ],
  index_type: [
    { required: true, message: '请选择索引类型', type: 'error' }
  ],
  metric_type: [
    { required: true, message: '请选择度量类型', type: 'error' }
  ]
};

const embeddingRules = {
  embedding_result_id: [
    { required: true, message: '请选择向量化任务', type: 'error' }
  ]
};

// 获取维度提示
const getDimensionHint = (dim) => {
  const hints = {
    128: '轻量级',
    256: '小型模型',
    512: 'BERT-small',
    768: 'BERT-base',
    1024: 'BERT-large',
    1536: 'OpenAI text-embedding-ada-002',
    2048: '大型模型',
    3072: 'OpenAI text-embedding-3-large',
    4096: '超大模型'
  };
  return hints[dim] || '';
};

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN');
};

// 加载向量化任务列表
const loadEmbeddingTasks = async () => {
  loadingEmbeddings.value = true;
  try {
    const result = await vectorIndexStore.fetchEmbeddingTasks();
    // API 返回 { tasks: [], total: N, ... }，只显示已完成的任务
    const tasks = result?.tasks || result || [];
    embeddingTasks.value = tasks.filter(t => t.status === 'SUCCESS' || t.status === 'PARTIAL_SUCCESS');
  } catch (error) {
    console.error('加载向量化任务失败:', error);
    embeddingTasks.value = [];
  } finally {
    loadingEmbeddings.value = false;
  }
};

// 选择向量化任务
const handleEmbeddingSelect = (taskId) => {
  const task = embeddingTasks.value.find(t => t.result_id === taskId);
  selectedEmbedding.value = task || null;
};

// 确认创建
const handleConfirm = async () => {
  if (createMode.value === 'manual') {
    const valid = await manualFormRef.value?.validate();
    if (valid === true) {
      emit('create', { ...formData });
    }
  } else {
    const valid = await embeddingFormRef.value?.validate();
    if (valid === true) {
      emit('create-from-embedding', { ...embeddingFormData });
    }
  }
};

// 关闭对话框
const handleClose = () => {
  manualFormRef.value?.reset();
  embeddingFormRef.value?.reset();
  selectedEmbedding.value = null;
  createMode.value = 'manual';
};

// 监听对话框显示状态
watch(() => props.visible, (newVal) => {
  if (newVal) {
    loadEmbeddingTasks();
  } else {
    handleClose();
  }
});

onMounted(() => {
  if (props.visible) {
    loadEmbeddingTasks();
  }
});
</script>

<style scoped>
.create-tabs {
  margin-top: -16px;
}

.create-form {
  padding-top: 16px;
}

.form-tip {
  margin-top: 4px;
  font-size: 12px;
  color: var(--td-text-color-placeholder);
}

.radio-desc {
  margin-left: 8px;
  font-size: 12px;
  color: var(--td-text-color-secondary);
}

.option-desc {
  font-size: 12px;
  color: var(--td-text-color-placeholder);
  margin-top: 2px;
}

.option-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 0;
}

.option-name {
  font-weight: 500;
  font-size: 14px;
  color: var(--td-text-color-primary);
}

.dimension-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.dim-hint {
  font-size: 12px;
  color: var(--td-text-color-placeholder);
}

.embedding-option {
  padding: 4px 0;
}

.embedding-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.embedding-name {
  font-weight: 500;
}

.embedding-meta {
  display: flex;
  gap: 12px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--td-text-color-secondary);
}

.embedding-details {
  margin: 16px 0;
  padding: 16px;
  background: var(--td-bg-color-container);
  border-radius: 6px;
}

:deep(.t-radio) {
  display: block;
  margin-bottom: 12px;
}

:deep(.t-tabs__nav) {
  margin-bottom: 16px;
}
</style>
