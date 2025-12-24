<template>
  <t-dialog
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    header="创建向量索引"
    width="600px"
    :confirm-btn="{
      content: '创建',
      theme: 'primary',
      loading: loading
    }"
    @confirm="handleConfirm"
    @close="handleClose"
  >
    <t-form
      ref="formRef"
      :data="formData"
      :rules="rules"
      label-width="100px"
      @submit="handleSubmit"
    >
      <t-form-item label="索引名称" name="index_name">
        <t-input
          v-model="formData.index_name"
          placeholder="请输入索引名称"
          clearable
        />
      </t-form-item>

      <t-form-item label="向量维度" name="dimension">
        <t-input-number
          v-model="formData.dimension"
          :min="1"
          :max="4096"
          placeholder="请输入向量维度"
          style="width: 100%"
        />
        <div class="form-tip">常用维度: OpenAI (1536), BERT (768), Word2Vec (300)</div>
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
          :autosize="{ minRows: 3, maxRows: 5 }"
        />
      </t-form-item>
    </t-form>
  </t-dialog>
</template>

<script setup>
import { ref, reactive, watch } from 'vue';

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

const emit = defineEmits(['update:visible', 'create']);

const formRef = ref(null);

const formData = reactive({
  index_name: '',
  dimension: 1536,
  index_type: 'FAISS',
  metric_type: 'cosine',
  description: ''
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
    { required: true, message: '请输入向量维度', type: 'error' },
    { 
      validator: (val) => val > 0 && val <= 4096, 
      message: '向量维度必须在 1-4096 之间', 
      type: 'error' 
    }
  ],
  index_type: [
    { required: true, message: '请选择索引类型', type: 'error' }
  ],
  metric_type: [
    { required: true, message: '请选择度量类型', type: 'error' }
  ]
};

const handleConfirm = async () => {
  const valid = await formRef.value.validate();
  if (valid === true) {
    emit('create', { ...formData });
  }
};

const handleSubmit = (e) => {
  e.preventDefault();
};

const handleClose = () => {
  formRef.value?.reset();
};

watch(() => props.visible, (newVal) => {
  if (!newVal) {
    formRef.value?.reset();
  }
});
</script>

<style scoped>
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

:deep(.t-radio) {
  display: block;
  margin-bottom: 12px;
}
</style>
