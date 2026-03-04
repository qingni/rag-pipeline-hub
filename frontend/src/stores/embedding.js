/**
 * Pinia store for document embedding
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import embeddingService from '@/services/embeddingService'
import { createProgressStream, clearProgress as clearProgressApi } from '@/services/embeddingProgressService'

export const useEmbeddingStore = defineStore('embedding', () => {
  // State
  const selectedDocumentId = ref(null)
  const selectedModel = ref('qwen3-embedding-8b')
  const isProcessing = ref(false)
  const embeddingResults = ref(null)
  const embeddingHistory = ref([])  // 新增：历史记录列表
  const documentsWithChunking = ref([])
  const availableModels = ref([])
  const error = ref(null)
  
  // New: Progress tracking state
  const currentTaskId = ref(null)
  const progress = ref({
    total: 0,
    completed: 0,
    failed: 0,
    cached: 0,
    speed: 0,
    eta_seconds: 0,
    status: 'idle',
    percentage: 0,
    current_item: null,
  })
  const isCancelling = ref(false)
  const progressConnection = ref(null)

  // Getters
  const currentResult = computed(() => embeddingResults.value)
  
  const selectedDocument = computed(() => {
    if (!selectedDocumentId.value) return null
    // 兼容 document_id 和 id 两种字段名
    return documentsWithChunking.value.find(
      doc => (doc.document_id || doc.id) === selectedDocumentId.value
    )
  })
  
  const canStartEmbedding = computed(() => {
    return selectedDocumentId.value && selectedModel.value && !isProcessing.value
  })
  
  // New: Progress getters
  const hasActiveTask = computed(() => {
    return currentTaskId.value !== null && isProcessing.value
  })
  
  const canCancel = computed(() => {
    return hasActiveTask.value && !isCancelling.value && progress.value.status === 'processing'
  })

  // Actions
  async function fetchDocumentsWithChunking() {
    try {
      error.value = null
      const response = await embeddingService.getDocumentsWithChunking({
        page: 1,
        page_size: 100
      })
      
      // Response structure: { success: true, data: { documents: [...], total: ... } }
      // 兼容多种响应格式
      console.log('[Embedding Store] API response:', response)
      const documents = response.data?.documents || response.documents || response.data?.items || []
      console.log('[Embedding Store] Parsed documents:', documents.length)
      documentsWithChunking.value = documents
      return documentsWithChunking.value
    } catch (err) {
      const errorMessage = err.message || '获取已分块文档列表失败'
      error.value = errorMessage
      console.error('[Embedding Store] Error:', errorMessage)
      throw err
    }
  }

  async function fetchModels() {
    try {
      error.value = null
      const response = await embeddingService.getAvailableModels()
      
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
  
  // New: Progress tracking actions
  function startProgressTracking(taskId) {
    // Close existing connection if any
    stopProgressTracking()
    
    currentTaskId.value = taskId
    progress.value = {
      total: 0,
      completed: 0,
      failed: 0,
      cached: 0,
      speed: 0,
      eta_seconds: 0,
      status: 'processing',
      percentage: 0,
      current_item: null,
    }
    
    progressConnection.value = createProgressStream(taskId, {
      onProgress: (data) => {
        progress.value = {
          ...progress.value,
          ...data,
        }
      },
      onComplete: (data) => {
        progress.value.status = data.status || 'completed'
        isProcessing.value = false
        stopProgressTracking()
      },
      onError: (err) => {
        console.error('Progress stream error:', err)
        error.value = '进度跟踪连接失败'
      },
    })
  }
  
  function stopProgressTracking() {
    if (progressConnection.value) {
      progressConnection.value.close()
      progressConnection.value = null
    }
  }
  
  async function cancelCurrentTask() {
    if (!currentTaskId.value || isCancelling.value) {
      return false
    }
    
    try {
      isCancelling.value = true
      
      const response = await fetch(`/api/v1/embedding/progress/${currentTaskId.value}/cancel`, {
        method: 'POST',
      })
      
      if (!response.ok) {
        throw new Error('取消请求失败')
      }
      
      progress.value.status = 'cancelling'
      return true
    } catch (err) {
      error.value = err.message || '取消任务失败'
      return false
    } finally {
      isCancelling.value = false
    }
  }
  
  function resetProgress() {
    stopProgressTracking()
    currentTaskId.value = null
    progress.value = {
      total: 0,
      completed: 0,
      failed: 0,
      cached: 0,
      speed: 0,
      eta_seconds: 0,
      status: 'idle',
      percentage: 0,
      current_item: null,
    }
    isCancelling.value = false
  }

  async function fetchEmbeddingHistory(documentId = null) {
    try {
      error.value = null
      const params = {
        page: 1,
        page_size: 100
      }
      if (documentId) {
        params.document_id = documentId
      }
      
      const response = await embeddingService.listResults(params)
      
      // Handle response format: { results: [...], pagination: {...} }
      const results = response.data?.results || response.results || []
      embeddingHistory.value = results
      
      return embeddingHistory.value
    } catch (err) {
      const errorMessage = err.message || '获取历史记录失败'
      error.value = errorMessage
      throw err
    }
  }

  async function fetchEmbeddingResultById(resultId) {
    try {
      error.value = null
      const response = await embeddingService.getResultById(resultId)
      
      const resultData = response.data || response
      
      // 构建 documentInfo，使用 API 返回的 document_name
      let documentInfo = null
      if (resultData.document_name) {
        documentInfo = {
          filename: resultData.document_name,
          document_id: resultData.document_id
        }
      } else if (resultData.document_id) {
        // 如果 API 没有返回 document_name，尝试从已加载的文档列表中查找
        // 兼容 document_id 和 id 两种字段名
        const doc = documentsWithChunking.value.find(
          d => (d.document_id || d.id) === resultData.document_id
        )
        if (doc) {
          documentInfo = {
            filename: doc.filename,
            document_id: doc.document_id
          }
        }
      }
      
      embeddingResults.value = {
        ...resultData,
        documentInfo: documentInfo
      }
      
      return embeddingResults.value
    } catch (err) {
      const errorMessage = err.message || '获取向量化结果失败'
      error.value = errorMessage
      throw err
    }
  }

  async function deleteEmbeddingResult(resultId) {
    try {
      error.value = null
      await embeddingService.deleteResult(resultId)
      
      // 从历史记录中移除
      embeddingHistory.value = embeddingHistory.value.filter(
        item => item.result_id !== resultId
      )
      
      // 如果删除的是当前结果，清空
      if (embeddingResults.value?.result_id === resultId) {
        clearResults()
      }
      
      return true
    } catch (err) {
      const errorMessage = err.message || '删除失败'
      error.value = errorMessage
      throw err
    }
  }

  async function clearAllEmbeddingResults() {
    try {
      error.value = null
      const response = await embeddingService.clearAllResults()
      
      // 清空本地状态
      embeddingHistory.value = []
      clearResults()
      
      return response
    } catch (err) {
      const errorMessage = err.message || '清空失败'
      error.value = errorMessage
      throw err
    }
  }

  return {
    // State
    selectedDocumentId,
    selectedModel,
    isProcessing,
    embeddingResults,
    embeddingHistory,  // 新增
    documentsWithChunking,
    availableModels,
    error,
    // New: Progress state
    currentTaskId,
    progress,
    isCancelling,
    
    // Getters
    currentResult,
    selectedDocument,
    canStartEmbedding,
    // New: Progress getters
    hasActiveTask,
    canCancel,
    
    // Actions
    fetchDocumentsWithChunking,
    fetchModels,
    fetchLatestEmbeddingResult,
    fetchEmbeddingHistory,  // 新增
    fetchEmbeddingResultById,  // 新增
    deleteEmbeddingResult,  // 新增
    clearAllEmbeddingResults,  // 新增：清空所有向量化记录
    startEmbedding,
    clearResults,
    resetSelection,
    // New: Progress actions
    startProgressTracking,
    stopProgressTracking,
    cancelCurrentTask,
    resetProgress
  }
})
