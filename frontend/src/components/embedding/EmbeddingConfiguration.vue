<template>
  <div class="embedding-configuration">
    <t-card title="向量化配置" :bordered="false">
      <t-form
        ref="formRef"
        :data="formData"
        :rules="formRules"
        label-align="left"
        label-width="100px"
        @submit="handleSubmit"
      >
        <!-- 模型选择 -->
        <t-form-item label="向量模型" name="model">
          <t-select
            v-model="formData.model"
            placeholder="请选择向量模型"
            @change="handleModelChange"
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
                <div class="model-info">
                  <t-tag size="small" theme="primary" variant="outline">
                    维度: {{ model.dimension }}
                  </t-tag>
                  <t-tag size="small" theme="success" variant="outline">
                    {{ model.provider }}
                  </t-tag>
                </div>
              </div>
            </t-option>
          </t-select>
          
          <!-- 模型详情 -->
          <div v-if="selectedModelInfo" class="model-details">
            <t-descriptions bordered size="small" :column="1">
              <t-descriptions-item label="维度">
                {{ selectedModelInfo.dimension }}
              </t-descriptions-item>
              <t-descriptions-item label="提供商">
                {{ selectedModelInfo.provider }}
              </t-descriptions-item>
              <t-descriptions-item label="多语言支持">
                <t-tag
                  :theme="selectedModelInfo.supports_multilingual ? 'success' : 'default'"
                  size="small"
                >
                  {{ selectedModelInfo.supports_multilingual ? '支持' : '不支持' }}
                </t-tag>
              </t-descriptions-item>
              <t-descriptions-item label="最大批次">
                {{ selectedModelInfo.max_batch_size }}
              </t-descriptions-item>
            </t-descriptions>
          </div>
        </t-form-item>
        
        <!-- 分块策略过滤（仅在文档模式） -->
        <t-form-item
          v-if="mode === 'document'"
          label="分块策略"
          name="strategyType"
        >
          <t-select
            v-model="formData.strategyType"
            placeholder="不限制（使用最新分块结果）"
            clearable
          >
            <t-option value="fixed_size" label="固定大小分块" />
            <t-option value="semantic" label="语义分块" />
            <t-option value="recursive" label="递归分块" />
            <t-option value="markdown" label="Markdown分块" />
          </t-select>
          <template #tips>
            留空则自动选择文档的最新活跃分块结果
          </template>
        </t-form-item>
        
        <!-- 高级配置 -->
        <t-form-item>
          <template #label>
            <span>高级配置</span>
            <t-switch
              v-model="showAdvanced"
              size="small"
              style="margin-left: 8px;"
            />
          </template>
        </t-form-item>
        
        <template v-if="showAdvanced">
          <!-- 最大重试次数 -->
          <t-form-item label="最大重试" name="maxRetries">
            <t-input-number
              v-model="formData.maxRetries"
              :min="0"
              :max="10"
              placeholder="最大重试次数"
            />
            <template #tips>
              单个分块失败后的最大重试次数 (0-10)
            </template>
          </t-form-item>
          
          <!-- 超时时间 -->
          <t-form-item label="超时时间" name="timeout">
            <t-input-number
              v-model="formData.timeout"
              :min="5"
              :max="300"
              placeholder="超时时间（秒）"
            />
            <template #tips>
              单个请求的超时时间，单位秒 (5-300)
            </template>
          </t-form-item>
        </template>
        
        <!-- 操作按钮 -->
        <t-form-item>
          <t-space>
            <t-button
              theme="primary"
              type="submit"
              :loading="loading"
              :disabled="!canSubmit"
            >
              <template #icon><t-icon name="play-circle" /></template>
              开始向量化
            </t-button>
            <t-button
              theme="default"
              variant="outline"
              @click="handleReset"
            >
              重置
            </t-button>
          </t-space>
        </t-form-item>
      </t-form>
    </t-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'

const props = defineProps({
  models: {
    type: Array,
    default: () => []
  },
  mode: {
    type: String,
    default: 'chunking_result',
    validator: (value) => ['document', 'chunking_result'].includes(value)
  },
  loading: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['submit', 'model-change'])

const formRef = ref(null)
const showAdvanced = ref(false)
const selectedModelInfo = ref(null)

const formData = reactive({
  model: '',
  strategyType: null,
  maxRetries: 3,
  timeout: 60
})

const formRules = {
  model: [
    { required: true, message: '请选择向量模型', type: 'error' }
  ],
  maxRetries: [
    { required: true, message: '请输入最大重试次数', type: 'error' },
    { min: 0, max: 10, message: '重试次数范围: 0-10', type: 'error' }
  ],
  timeout: [
    { required: true, message: '请输入超时时间', type: 'error' },
    { min: 5, max: 300, message: '超时时间范围: 5-300秒', type: 'error' }
  ]
}

const canSubmit = computed(() => {
  return formData.model && !props.disabled && !props.loading
})

onMounted(() => {
  // 默认选择第一个模型
  if (props.models.length > 0 && !formData.model) {
    formData.model = props.models[0].name
    handleModelChange(formData.model)
  }
})

watch(() => props.models, (newModels) => {
  if (newModels.length > 0 && !formData.model) {
    formData.model = newModels[0].name
    handleModelChange(formData.model)
  }
}, { immediate: true })

const handleModelChange = (modelName) => {
  selectedModelInfo.value = props.models.find(m => m.name === modelName)
  emit('model-change', modelName)
}

const handleSubmit = ({ validateResult, firstError }) => {
  if (validateResult === true) {
    const config = {
      model: formData.model,
      maxRetries: formData.maxRetries,
      timeout: formData.timeout
    }
    
    if (props.mode === 'document' && formData.strategyType) {
      config.strategyType = formData.strategyType
    }
    
    emit('submit', config)
  } else {
    MessagePlugin.warning(firstError || '请检查表单')
  }
}

const handleReset = () => {
  formData.model = props.models.length > 0 ? props.models[0].name : ''
  formData.strategyType = null
  formData.maxRetries = 3
  formData.timeout = 60
  showAdvanced.value = false
}

defineExpose({
  validate: () => formRef.value?.validate(),
  reset: handleReset
})
</script>

<style scoped>
.embedding-configuration {
  height: 100%;
}

.model-option {
  padding: 4px 0;
}

.model-name {
  font-weight: 500;
  font-size: 14px;
  margin-bottom: 4px;
}

.model-desc {
  font-size: 12px;
  color: var(--td-text-color-secondary);
  margin-bottom: 6px;
}

.model-info {
  display: flex;
  gap: 6px;
}

.model-details {
  margin-top: 12px;
  padding: 12px;
  background: var(--td-bg-color-container);
  border-radius: 6px;
}
</style>
