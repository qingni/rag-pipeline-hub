<template>
  <div class="model-selector">
    <label class="selector-label">选择向量模型</label>
    <t-select
      v-model="localSelectedModel"
      :options="formattedModels"
      placeholder="请选择向量模型"
      :disabled="loading || models.length === 0"
      @change="handleChange"
    />
    
    <!-- 模型详细信息面板 -->
    <div v-if="selectedModelInfo" class="model-details">
      <div class="detail-header">
        <Hash :size="16" class="header-icon" />
        <span class="header-text">模型详情</span>
      </div>
      
      <div class="detail-grid">
        <div class="detail-item">
          <span class="detail-label">模型名称</span>
          <span class="detail-value">{{ selectedModelInfo.name }}</span>
        </div>
        
        <div class="detail-item">
          <span class="detail-label">向量维度</span>
          <span class="detail-value highlight">{{ selectedModelInfo.dimension }} 维</span>
        </div>
        
        <div class="detail-item">
          <span class="detail-label">服务提供商</span>
          <span class="detail-value">{{ selectedModelInfo.provider }}</span>
        </div>
        
        <div class="detail-item">
          <span class="detail-label">多语言支持</span>
          <span class="detail-value">
            <Check v-if="selectedModelInfo.supports_multilingual" :size="16" class="check-icon" />
            <X v-else :size="16" class="x-icon" />
          </span>
        </div>
        
        <div class="detail-item">
          <span class="detail-label">批处理上限</span>
          <span class="detail-value">{{ selectedModelInfo.max_batch_size }} 条</span>
        </div>
        
        <div class="detail-item full-width">
          <span class="detail-label">模型描述</span>
          <span class="detail-value">{{ selectedModelInfo.description }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch, ref } from 'vue'
import { Hash, Check, X } from 'lucide-vue-next'

const props = defineProps({
  models: {
    type: Array,
    default: () => []
  },
  modelValue: {
    type: String,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const localSelectedModel = ref(props.modelValue)

// 格式化模型选项: "ModelName · Dimension维 · Description"
const formattedModels = computed(() => {
  return props.models.map(model => ({
    label: `${model.name} · ${model.dimension}维 · ${model.description}`,
    value: model.name
  }))
})

const selectedModelInfo = computed(() => {
  if (!localSelectedModel.value) return null
  return props.models.find(model => model.name === localSelectedModel.value)
})

function handleChange(value) {
  emit('update:modelValue', value)
}

// 同步外部变化
watch(() => props.modelValue, (newValue) => {
  localSelectedModel.value = newValue
})
</script>

<style scoped>
.model-selector {
  margin-bottom: 1.5rem;
}

.selector-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 0.5rem;
}

.model-details {
  margin-top: 1rem;
  padding: 1rem;
  background-color: #f0f9ff;
  border-radius: 6px;
  border: 1px solid #bfdbfe;
}

.detail-header {
  display: flex;
  align-items: center;
  margin-bottom: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #bfdbfe;
}

.header-icon {
  color: #3b82f6;
  margin-right: 0.5rem;
}

.header-text {
  font-size: 13px;
  font-weight: 600;
  color: #1e40af;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-item.full-width {
  grid-column: 1 / -1;
}

.detail-label {
  font-size: 11px;
  color: #6b7280;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.detail-value {
  font-size: 13px;
  color: #111827;
  font-weight: 500;
  display: flex;
  align-items: center;
}

.detail-value.highlight {
  color: #3b82f6;
  font-weight: 600;
}

.check-icon {
  color: #10b981;
}

.x-icon {
  color: #ef4444;
}
</style>
