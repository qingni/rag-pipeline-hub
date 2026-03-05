<template>
  <div class="generation-config">
    <h4 class="config-title">
      <Settings :size="18" />
      模型配置
    </h4>
    
    <!-- 知识库选择 -->
    <div class="config-item">
      <label class="config-label">
        <span>知识库</span>
        <t-tag v-if="selectedCollectionIds.length > 0" size="small" theme="primary">
          {{ selectedCollectionIds.length }} 个
        </t-tag>
      </label>
      <t-select
        v-model="selectedCollectionIds"
        :disabled="disabled || isLoadingCollections"
        :loading="isLoadingCollections"
        placeholder="选择知识库（可多选）"
        multiple
        clearable
        :popup-props="{ overlayClassName: 'generation-collection-select-popup' }"
      >
        <t-option
          v-for="collection in availableCollections"
          :key="collection.id"
          :value="collection.id"
          :label="collection.name"
        >
          <div class="collection-option">
            <div class="collection-name">{{ collection.name }}</div>
            <div class="collection-desc">
              {{ collection.document_count || 0 }} 文档 · {{ collection.vector_count || 0 }} 向量
            </div>
          </div>
        </t-option>
      </t-select>
      <div class="config-hint">
        选择要检索的知识库，不选则仅使用模型自身知识
      </div>
    </div>
    
    <!-- 检索数量 -->
    <div class="config-item" v-if="selectedCollectionIds.length > 0">
      <label class="config-label">
        检索数量 (Top-K)
        <span class="label-value">{{ topKValue }}</span>
      </label>
      <t-slider
        v-model="topKValue"
        :min="1"
        :max="20"
        :step="1"
        :disabled="disabled"
      />
      <div class="config-hint">
        从知识库中检索的相关文档数量
      </div>
    </div>
    
    <!-- 模型选择 -->
    <div class="config-item">
      <label class="config-label">生成模型</label>
      <t-select
        v-model="selectedModel"
        :disabled="disabled"
        placeholder="选择模型"
        :popup-props="{ overlayClassName: 'generation-model-select-popup' }"
      >
        <t-option
          v-for="model in models"
          :key="model.name"
          :value="model.name"
          :label="model.name"
        >
          <div class="model-option">
            <div class="model-name">{{ model.name }}</div>
            <div class="model-desc">{{ model.description }}</div>
          </div>
        </t-option>
      </t-select>
      <div class="config-hint" v-if="currentModel">
        {{ currentModel.description }}
      </div>
    </div>
    
    <!-- 温度参数 -->
    <div class="config-item">
      <label class="config-label">
        温度 (Temperature)
        <span class="label-value">{{ temperatureValue.toFixed(1) }}</span>
      </label>
      <t-slider
        v-model="temperatureValue"
        :min="0"
        :max="2"
        :step="0.1"
        :disabled="disabled"
      />
      <div class="config-hint">
        较低的值使输出更确定，较高的值使输出更随机
      </div>
    </div>
    
    <!-- 最大输出长度 -->
    <div class="config-item">
      <label class="config-label">最大输出长度</label>
      <t-input-number
        v-model="maxTokensValue"
        :min="1"
        :max="8192"
        :step="256"
        :disabled="disabled"
        theme="normal"
      />
      <div class="config-hint">
        生成回答的最大 token 数量
      </div>
    </div>
    
    <!-- 模型信息 -->
    <div class="model-info" v-if="currentModel">
      <div class="info-item">
        <span class="info-label">上下文长度</span>
        <span class="info-value">{{ formatNumber(currentModel.context_length) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Settings } from 'lucide-vue-next'

const props = defineProps({
  model: {
    type: String,
    default: 'deepseek-v3.2'
  },
  temperature: {
    type: Number,
    default: 0.7
  },
  maxTokens: {
    type: Number,
    default: 4096
  },
  models: {
    type: Array,
    default: () => []
  },
  disabled: {
    type: Boolean,
    default: false
  },
  collectionIds: {
    type: Array,
    default: () => []
  },
  availableCollections: {
    type: Array,
    default: () => []
  },
  isLoadingCollections: {
    type: Boolean,
    default: false
  },
  topK: {
    type: Number,
    default: 5
  }
})

const emit = defineEmits([
  'update:model', 
  'update:temperature', 
  'update:maxTokens',
  'update:collectionIds',
  'update:topK'
])

const selectedModel = computed({
  get: () => props.model,
  set: (value) => emit('update:model', value)
})

const temperatureValue = computed({
  get: () => props.temperature,
  set: (value) => emit('update:temperature', value)
})

const maxTokensValue = computed({
  get: () => props.maxTokens,
  set: (value) => emit('update:maxTokens', value)
})

const selectedCollectionIds = computed({
  get: () => props.collectionIds,
  set: (value) => emit('update:collectionIds', value)
})

const topKValue = computed({
  get: () => props.topK,
  set: (value) => emit('update:topK', value)
})

const currentModel = computed(() => {
  return props.models.find(m => m.name === props.model)
})

function formatNumber(num) {
  if (num >= 1000) {
    return (num / 1000).toFixed(0) + 'K'
  }
  return num.toString()
}
</script>

<style scoped>
.generation-config {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.config-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 500;
  color: #1f2937;
  margin: 0 0 16px 0;
}

.config-item {
  margin-bottom: 16px;
}

.config-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 8px;
}

.label-value {
  font-weight: 600;
  color: #6366f1;
}

.config-hint {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
}

.model-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.model-name {
  font-weight: 500;
  font-size: 14px;
}

.model-desc {
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.4;
}

.model-info {
  background: #f9fafb;
  border-radius: 8px;
  padding: 12px;
  margin-top: 16px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-label {
  font-size: 12px;
  color: #6b7280;
}

.info-value {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}
</style>

<!-- 全局样式，用于弹出层 -->
<style>
.generation-model-select-popup .t-select-option {
  padding: 10px 12px !important;
  height: auto !important;
  min-height: auto !important;
}

.generation-model-select-popup .t-select-option__content {
  white-space: normal;
  line-height: 1.5;
}

.generation-model-select-popup .model-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.generation-model-select-popup .model-name {
  font-weight: 500;
  font-size: 14px;
  color: var(--td-text-color-primary);
}

.generation-model-select-popup .model-desc {
  font-size: 12px;
  color: var(--td-text-color-placeholder);
  line-height: 1.4;
}

/* 知识库选择弹出层样式 */
.generation-collection-select-popup .t-select-option {
  padding: 10px 12px !important;
  height: auto !important;
  min-height: auto !important;
}

.generation-collection-select-popup .t-select-option__content {
  white-space: normal;
  line-height: 1.5;
}

.generation-collection-select-popup .collection-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.generation-collection-select-popup .collection-name {
  font-weight: 500;
  font-size: 14px;
  color: var(--td-text-color-primary);
}

.generation-collection-select-popup .collection-desc {
  font-size: 12px;
  color: var(--td-text-color-placeholder);
  line-height: 1.4;
}
</style>
