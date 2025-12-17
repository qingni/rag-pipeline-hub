<template>
  <div class="document-embedding-page">
    <!-- 左侧控制面板 -->
    <div class="control-panel">
      <div class="panel-header">
        <Hash :size="24" class="panel-icon" />
        <h2 class="panel-title">文档向量化</h2>
      </div>
      
      <div class="panel-content">
        <!-- 文档选择器 -->
        <DocumentSelector
          v-model="store.selectedDocumentId"
          :documents="store.documentsWithChunking"
          :loading="loadingDocs"
        />
        
        <!-- 模型选择器 -->
        <ModelSelector
          v-model="store.selectedModel"
          :models="store.availableModels"
          :loading="loadingModels"
        />
        
        <!-- 高级选项 (可选) -->
        <t-collapse
          v-model="advancedExpanded"
          class="advanced-options"
          :default-value="[]"
        >
          <t-collapse-panel value="advanced" header="高级选项">
            <div class="options-grid">
              <div class="option-item">
                <label class="option-label">最大重试次数</label>
                <t-input-number
                  v-model="maxRetries"
                  :min="0"
                  :max="10"
                  :default-value="3"
                />
              </div>
              
              <div class="option-item">
                <label class="option-label">超时时间（秒）</label>
                <t-input-number
                  v-model="timeout"
                  :min="10"
                  :max="300"
                  :default-value="60"
                />
              </div>
            </div>
          </t-collapse-panel>
        </t-collapse>
        
        <!-- 开始按钮 -->
        <t-button
          theme="primary"
          size="large"
          block
          :loading="store.isProcessing"
          :disabled="!store.canStartEmbedding"
          @click="handleStartEmbedding"
        >
          <template #icon>
            <Zap :size="18" />
          </template>
          {{ buttonText }}
        </t-button>
        
        <!-- 验证提示 -->
        <div v-if="!store.canStartEmbedding && !store.isProcessing" class="validation-hint">
          <AlertCircle :size="14" />
          <span>{{ validationMessage }}</span>
        </div>
        
        <!-- 错误提示 -->
        <t-alert
          v-if="store.error"
          theme="error"
          :message="store.error"
          close
          @close="store.error = null"
        />
      </div>
    </div>
    
    <!-- 右侧结果面板 -->
    <div class="results-panel">
      <!-- 加载中状态 -->
      <div v-if="loadingResult" class="loading-overlay">
        <t-loading size="large" text="正在加载向量化结果..." />
      </div>
      
      <EmbeddingResults v-else :result="store.currentResult" />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, computed, watch } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { Hash, Zap, AlertCircle } from 'lucide-vue-next'
import { useEmbeddingStore } from '@/stores/embedding'
import DocumentSelector from '@/components/embedding/DocumentSelector.vue'
import ModelSelector from '@/components/embedding/ModelSelector.vue'
import EmbeddingResults from '@/components/embedding/EmbeddingResults.vue'

const store = useEmbeddingStore()

const loadingDocs = ref(false)
const loadingModels = ref(false)
const loadingResult = ref(false)
const advancedExpanded = ref([])
const maxRetries = ref(3)
const timeout = ref(60)

const validationMessage = computed(() => {
  if (!store.selectedDocumentId) {
    return '请选择文档'
  }
  if (!store.selectedModel) {
    return '请选择向量模型'
  }
  return ''
})

const buttonText = computed(() => {
  if (store.isProcessing) {
    return '向量化中...'
  }
  return store.currentResult ? '重新向量化' : '开始向量化'
})

// 监听文档选择变化，自动加载历史向量化结果
watch(
  () => store.selectedDocumentId,
  async (newDocumentId, oldDocumentId) => {
    if (!newDocumentId) {
      store.clearResults()
      return
    }
    
    // 文档切换时才加载（避免初始化重复加载）
    if (oldDocumentId !== undefined && newDocumentId !== oldDocumentId) {
      await loadLatestResult(newDocumentId)
    } else if (oldDocumentId === undefined) {
      // 首次选择文档
      await loadLatestResult(newDocumentId)
    }
  }
)

onMounted(async () => {
  // 并行加载文档和模型
  await Promise.all([
    loadDocuments(),
    loadModels()
  ])
})

async function loadDocuments() {
  try {
    loadingDocs.value = true
    await store.fetchDocumentsWithChunking()
    
    if (store.documentsWithChunking.length === 0) {
      MessagePlugin.info('暂无已分块文档，请先对文档进行分块处理')
    }
  } catch (error) {
    MessagePlugin.error(error.message || '获取文档列表失败')
  } finally {
    loadingDocs.value = false
  }
}

async function loadModels() {
  try {
    loadingModels.value = true
    await store.fetchModels()
  } catch (error) {
    MessagePlugin.error(error.message || '获取模型列表失败')
  } finally {
    loadingModels.value = false
  }
}

async function loadLatestResult(documentId) {
  try {
    loadingResult.value = true
    await store.fetchLatestEmbeddingResult(documentId)
    
    if (store.currentResult) {
      MessagePlugin.success('已加载历史向量化结果')
    }
  } catch (error) {
    // 404 错误已在 store 中处理，不显示错误消息
    if (error.response?.status !== 404) {
      console.error('Failed to load latest result:', error)
    }
  } finally {
    loadingResult.value = false
  }
}

async function handleStartEmbedding() {
  if (!store.canStartEmbedding) {
    MessagePlugin.warning(validationMessage.value)
    return
  }

  try {
    await store.startEmbedding({
      max_retries: maxRetries.value,
      timeout: timeout.value
    })
    
    MessagePlugin.success('向量化完成')
  } catch (error) {
    // Error already handled in store
    console.error('Embedding failed:', error)
  }
}
</script>

<style scoped>
.document-embedding-page {
  display: flex;
  height: 100%;
  gap: 1.5rem;
  padding: 1.5rem;
  background-color: #f5f6fa;
}

.control-panel {
  width: 380px;
  flex-shrink: 0;
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
  background-color: #f9fafb;
}

.panel-icon {
  color: #3b82f6;
  margin-right: 0.75rem;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.panel-content {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
}

.advanced-options {
  margin-bottom: 1.5rem;
}

.options-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
  padding: 0.5rem 0;
}

.option-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.option-label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.validation-hint {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.75rem;
  padding: 0.75rem;
  background-color: #fef3c7;
  border: 1px solid #fde047;
  border-radius: 6px;
  font-size: 12px;
  color: #92400e;
}

.validation-hint svg {
  flex-shrink: 0;
  color: #f59e0b;
}

.results-panel {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.loading-overlay {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}
</style>
