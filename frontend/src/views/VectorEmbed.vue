<template>
  <div class="embed-page">
    <div class="panel-column">
      <EmbeddingPanel
        :models="models"
        :selected-model="selectedModel"
        :loading-single="loading.single"
        :loading-batch="loading.batch"
        :batch-summary="{ count: parsedFileTexts.length, fileName: batchFileName }"
        @update:model="handleModelChange"
        @submit-single="handleSingleSubmit"
        @submit-batch="handleBatchSubmit"
        @parse-batch-file="handleParseBatchFile"
        @clear-batch="clearBatchState"
      />
    </div>
    <div class="results-column">
      <EmbeddingResults :result="latestResult" />
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import EmbeddingPanel from '@/components/embedding/EmbeddingPanel.vue'
import EmbeddingResults from '@/components/embedding/EmbeddingResults.vue'
import embeddingService from '@/services/embeddingService'

const models = ref([])
const selectedModel = ref('')
const latestResult = ref(null)
const loading = reactive({ single: false, batch: false })
const parsedFileTexts = ref([])
const batchFileName = ref('')

const fetchModels = async () => {
  try {
    const response = await embeddingService.listModels()
    models.value = response.models || []
    if (!selectedModel.value && models.value.length) {
      selectedModel.value = models.value[0].name
    }
  } catch (error) {
    MessagePlugin.error(error.message || '模型列表获取失败')
  }
}

onMounted(() => {
  fetchModels()
})

const handleModelChange = (model) => {
  selectedModel.value = model
}

const handleSingleSubmit = async ({ text, maxRetries, timeout }) => {
  if (!selectedModel.value) {
    MessagePlugin.warning('请先选择模型')
    return
  }
  loading.single = true
  try {
    const response = await embeddingService.embedSingle({
      text,
      model: selectedModel.value,
      max_retries: maxRetries,
      timeout,
    })
    latestResult.value = { mode: 'single', data: response }
    MessagePlugin.success('向量生成完成')
  } catch (error) {
    MessagePlugin.error(error.message || '向量生成失败')
  } finally {
    loading.single = false
  }
}

const handleBatchSubmit = async ({ manualTexts, maxRetries, timeout }) => {
  if (!selectedModel.value) {
    MessagePlugin.warning('请先选择模型')
    return
  }
  const preparedTexts = prepareBatchTexts(manualTexts)
  if (!preparedTexts.length) {
    MessagePlugin.warning('请上传文件或输入文本')
    return
  }
  loading.batch = true
  try {
    const response = await embeddingService.embedBatch({
      texts: preparedTexts,
      model: selectedModel.value,
      max_retries: maxRetries,
      timeout,
    })
    latestResult.value = { mode: 'batch', data: response }
    MessagePlugin.success('批量向量化完成')
  } catch (error) {
    MessagePlugin.error(error.message || '批量向量化失败')
  } finally {
    loading.batch = false
  }
}

const prepareBatchTexts = (manualTexts = []) => {
  const sanitized = [
    ...parsedFileTexts.value,
    ...manualTexts,
  ]
    .map((text) => text?.trim())
    .filter(Boolean)

  if (sanitized.length > 1000) {
    MessagePlugin.warning('最多仅支持 1000 条文本，将自动截取前 1000 条')
    return sanitized.slice(0, 1000)
  }

  return sanitized
}

const handleParseBatchFile = async (file) => {
  try {
    const texts = await parseBatchFile(file)
    parsedFileTexts.value = texts
    batchFileName.value = file.name
    MessagePlugin.success(`文件解析成功，共 ${texts.length} 条`) 
  } catch (error) {
    MessagePlugin.error(error.message || '文件解析失败')
  }
}

const clearBatchState = () => {
  parsedFileTexts.value = []
  batchFileName.value = ''
}

const parseBatchFile = async (file) => {
  const content = await file.text()
  const extension = file.name.split('.').pop()?.toLowerCase() || ''

  if (extension === 'json') {
    return parseJsonTexts(content)
  }
  if (extension === 'csv') {
    return parseCsvTexts(content)
  }
  return parseLineTexts(content)
}

const parseJsonTexts = (raw) => {
  try {
    const data = JSON.parse(raw)
    if (Array.isArray(data)) {
      return data.map(extractText).filter(Boolean)
    }
    if (Array.isArray(data.texts)) {
      return data.texts.map(extractText).filter(Boolean)
    }
    throw new Error('JSON 格式需为字符串数组或含 texts 字段')
  } catch (error) {
    throw new Error('JSON 解析失败: ' + error.message)
  }
}

const parseCsvTexts = (raw) => {
  const lines = raw.split(/\r?\n/).filter(Boolean)
  if (!lines.length) {
    return []
  }
  const headers = lines[0].split(',').map((h) => h.trim().toLowerCase())
  const textIndex = headers.findIndex((h) => h === 'text' || h === 'content')
  if (textIndex === -1) {
    return lines.map((line) => line.split(',')[0]?.trim()).filter(Boolean)
  }
  return lines.slice(1).map((line) => line.split(',')[textIndex]?.trim()).filter(Boolean)
}

const parseLineTexts = (raw) => raw.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)

const extractText = (item) => {
  if (typeof item === 'string') {
    return item
  }
  if (typeof item === 'object' && item) {
    return item.text || item.content || ''
  }
  return ''
}
</script>

<style scoped>
.embed-page {
  display: flex;
  flex: 1;
  height: 100%;
  padding: 1.5rem;
  gap: 1.5rem;
  background-color: #f5f6fa;
}

.panel-column {
  width: 360px;
  flex-shrink: 0;
}

.results-column {
  flex: 1;
  overflow-y: auto;
}
</style>
