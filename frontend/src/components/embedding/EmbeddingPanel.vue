<template>
  <div class="panel">
    <t-card title="模型与参数" :bordered="false" class="mb-4">
      <div class="space-y-3">
        <div>
          <label class="panel-label">选择模型</label>
          <t-select
            v-model="localModel"
            placeholder="请选择模型"
            class="w-full"
            :options="modelOptions"
          />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <t-input-number v-model="maxRetries" :min="0" :max="10" label="最大重试次数" />
          <t-input-number v-model="timeout" :min="5" :max="300" label="超时时间 (秒)" />
        </div>
      </div>
    </t-card>

    <t-card :bordered="false">
      <t-tabs v-model:value="activeTab">
        <t-tab-panel value="single" label="单文本向量化">
          <div class="space-y-3">
            <t-textarea
              v-model="singleText"
              placeholder="请输入需要向量化的文本"
              :maxlength="10000"
              :autosize="{ minRows: 6, maxRows: 8 }"
            />
            <t-button
              theme="primary"
              block
              :disabled="!singleText.trim() || !localModel"
              :loading="loadingSingle"
              @click="handleSingleSubmit"
            >
              生成向量
            </t-button>
          </div>
        </t-tab-panel>
        <t-tab-panel value="batch" label="批量向量化">
          <div class="space-y-4">
            <t-alert
              theme="info"
              message="支持最多 1000 条文本。可上传 JSON/CSV 文件或手动粘贴，每行一条。"
              :close="false"
            />
            <div class="flex items-center gap-3">
              <input
                ref="fileInput"
                type="file"
                accept=".json,.csv,.txt"
                class="hidden"
                @change="handleFileChange"
              />
              <t-button theme="default" variant="outline" @click="triggerFileSelect">
                上传文件
              </t-button>
              <div v-if="batchSummary.count" class="text-sm text-gray-600 truncate">
                {{ batchSummary.fileName }} · 已解析 {{ batchSummary.count }} 条
              </div>
              <t-link
                v-if="batchSummary.count"
                theme="danger"
                hover="underline"
                size="small"
                @click="emit('clear-batch')"
              >
                清空
              </t-link>
            </div>
            <div>
              <label class="panel-label">手动粘贴 (每行一条)</label>
              <t-textarea
                v-model="batchTextarea"
                placeholder="输入多条文本，每行一条"
                :autosize="{ minRows: 4, maxRows: 8 }"
              />
            </div>
            <t-button
              theme="primary"
              block
              :disabled="!localModel"
              :loading="loadingBatch"
              @click="handleBatchSubmit"
            >
              批量向量化
            </t-button>
          </div>
        </t-tab-panel>
      </t-tabs>
    </t-card>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'

const props = defineProps({
  models: {
    type: Array,
    default: () => [],
  },
  selectedModel: {
    type: String,
    default: '',
  },
  loadingSingle: Boolean,
  loadingBatch: Boolean,
  batchSummary: {
    type: Object,
    default: () => ({ count: 0, fileName: '' }),
  },
})

const emit = defineEmits(['update:model', 'submit-single', 'submit-batch', 'parse-batch-file', 'clear-batch'])

const activeTab = ref('single')
const singleText = ref('')
const batchTextarea = ref('')
const maxRetries = ref(3)
const timeout = ref(60)
const fileInput = ref(null)
const localModel = ref(props.selectedModel)
const batchSummary = computed(() => props.batchSummary)

watch(
  () => props.selectedModel,
  (value) => {
    localModel.value = value
  },
)

watch(localModel, (value) => {
  emit('update:model', value)
})

const modelOptions = computed(() =>
  props.models.map((model) => ({
    label: `${model.name} · ${model.dimension}维`,
    value: model.name,
  })),
)

const triggerFileSelect = () => {
  fileInput.value?.click()
}

const handleFileChange = (event) => {
  const [file] = event.target.files || []
  if (file) {
    emit('parse-batch-file', file)
  }
  event.target.value = ''
}

const handleSingleSubmit = () => {
  if (!singleText.value.trim()) {
    MessagePlugin.warning('请输入文本')
    return
  }
  emit('submit-single', {
    text: singleText.value,
    model: localModel.value,
    maxRetries: maxRetries.value,
    timeout: timeout.value,
  })
}

const handleBatchSubmit = () => {
  const manualTexts = batchTextarea.value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
  emit('submit-batch', {
    manualTexts,
    model: localModel.value,
    maxRetries: maxRetries.value,
    timeout: timeout.value,
  })
}
</script>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.panel-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #4b5563;
  margin-bottom: 0.25rem;
}
</style>
