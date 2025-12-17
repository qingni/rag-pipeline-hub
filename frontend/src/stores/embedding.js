/**
 * Pinia store for document embedding
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import embeddingService from '@/services/embeddingService'

export const useEmbeddingStore = defineStore('embedding', () => {
  // State
  const selectedDocumentId = ref(null)
  const selectedModel = ref('qwen3-embedding-8b')
  const isProcessing = ref(false)
  const embeddingResults = ref(null)
  const documentsWithChunking = ref([])
  const availableModels = ref([])
  const error = ref(null)

  // Getters
  const currentResult = computed(() => embeddingResults.value)
  
  const selectedDocument = computed(() => {
    if (!selectedDocumentId.value) return null
    return documentsWithChunking.value.find(
      doc => doc.id === selectedDocumentId.value
    )
  })
  
  const canStartEmbedding = computed(() => {
    return selectedDocumentId.value && selectedModel.value && !isProcessing.value
  })

  // Actions
  async function fetchDocumentsWithChunking() {
    try {
      error.value = null
      const response = await embeddingService.getDocumentsWithChunking({
        page: 1,
        page_size: 100
      })
      
      // Response structure: { success: true, data: { items: [...], total: ... } }
      documentsWithChunking.value = response.data?.items || []
      return documentsWithChunking.value
    } catch (err) {
      const errorMessage = err.message || '获取已分块文档列表失败'
      error.value = errorMessage
      throw err
    }
  }

  async function fetchModels() {
    try {
      error.value = null
      const response = await embeddingService.listModels()
      
      // Handle two possible response formats:
      // 1. Wrapped: { success: true, data: { models: [...] } }
      // 2. Direct: { models: [...], count: ... }
      const models = response.data?.models || response.models || []
      availableModels.value = models
      
      // Set default model if none selected
      if (!selectedModel.value && availableModels.value.length > 0) {
        selectedModel.value = availableModels.value[0].name
      }
      
      return availableModels.value
    } catch (err) {
      const errorMessage = err.message || '获取模型列表失败'
      error.value = errorMessage
      throw err
    }
  }

  async function fetchLatestEmbeddingResult(documentId, modelFilter = null) {
    try {
      error.value = null
      const response = await embeddingService.getLatestByDocument(documentId, modelFilter)
      
      // Handle two possible response formats:
      // 1. Wrapped: { success: true, data: { ... } }
      // 2. Direct: { result_id, model, vectors, ... }
      const resultData = response.data || response
      
      embeddingResults.value = {
        ...resultData,
        documentInfo: selectedDocument.value
      }
      
      // 自动切换模型选择器到历史结果使用的模型
      if (resultData?.model && resultData.model !== selectedModel.value) {
        selectedModel.value = resultData.model
      }
      
      return embeddingResults.value
    } catch (err) {
      // 404 是正常情况（文档未向量化），不显示错误
      if (err.status === 404) {
        embeddingResults.value = null
        return null
      }
      
      const errorMessage = err.message || '获取向量化结果失败'
      error.value = errorMessage
      throw err
    }
  }

  async function startEmbedding(options = {}) {
    if (!selectedDocumentId.value || !selectedModel.value) {
      error.value = '请选择文档和模型'
      return
    }

    try {
      isProcessing.value = true
      error.value = null

      const response = await embeddingService.embedFromDocument({
        document_id: selectedDocumentId.value,
        model: selectedModel.value,
        strategy_type: options.strategy_type || null,
        max_retries: options.max_retries || 3,
        timeout: options.timeout || 60
      })

      // Handle two possible response formats:
      // 1. Wrapped: { success: true, data: { ... } }
      // 2. Direct: { request_id, status, vectors, ... }
      const resultData = response.data || response
      
      embeddingResults.value = {
        ...resultData,
        documentInfo: selectedDocument.value
      }

      return embeddingResults.value
    } catch (err) {
      const errorMessage = err.message || '向量化失败'
      error.value = errorMessage
      throw err
    } finally {
      isProcessing.value = false
    }
  }

  function clearResults() {
    embeddingResults.value = null
    error.value = null
  }

  function resetSelection() {
    selectedDocumentId.value = null
    selectedModel.value = availableModels.value[0]?.name || 'qwen3-embedding-8b'
    clearResults()
  }

  return {
    // State
    selectedDocumentId,
    selectedModel,
    isProcessing,
    embeddingResults,
    documentsWithChunking,
    availableModels,
    error,
    
    // Getters
    currentResult,
    selectedDocument,
    canStartEmbedding,
    
    // Actions
    fetchDocumentsWithChunking,
    fetchModels,
    fetchLatestEmbeddingResult,
    startEmbedding,
    clearResults,
    resetSelection
  }
})
