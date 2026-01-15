/**
 * Processing store - Pinia
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import processingService from '../services/processingService'

export const useProcessingStore = defineStore('processing', () => {
  // State
  const processingResults = ref([])
  const currentResult = ref(null)
  const status = ref('idle') // idle, processing, completed, failed
  const loading = ref(false)
  const error = ref(null)
  
  // Async task state
  const currentTaskId = ref(null)
  const taskProgress = ref(0)
  const taskStatus = ref(null) // pending, started, success, failure
  
  // Actions
  async function loadDocument(documentId, loaderType = null) {
    loading.value = true
    status.value = 'processing'
    error.value = null
    
    try {
      const response = await processingService.loadDocument(documentId, loaderType)
      
      if (response.success) {
        currentResult.value = response.data
        status.value = 'completed'
        return response.data
      }
    } catch (err) {
      error.value = err.message
      status.value = 'failed'
      throw err
    } finally {
      loading.value = false
    }
  }
  
  // ==================== 异步加载方法 ====================
  
  /**
   * 提交异步加载任务
   */
  async function loadDocumentAsync(documentId, loaderType = null) {
    loading.value = true
    status.value = 'submitting'
    error.value = null
    currentTaskId.value = null
    taskProgress.value = 0
    taskStatus.value = null
    
    try {
      const response = await processingService.loadDocumentAsync(documentId, loaderType)
      
      if (response.success) {
        currentTaskId.value = response.data.task_id
        taskStatus.value = response.data.status
        status.value = 'processing'
        return response.data
      }
    } catch (err) {
      error.value = err.message
      status.value = 'failed'
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 查询异步任务状态
   */
  async function pollTaskStatus(taskId = null) {
    const id = taskId || currentTaskId.value
    if (!id) return null
    
    try {
      const response = await processingService.getTaskStatus(id)
      
      if (response.success) {
        taskStatus.value = response.data.status
        taskProgress.value = response.data.progress || 0
        
        // 更新整体状态
        if (response.data.status === 'success') {
          status.value = 'completed'
        } else if (response.data.status === 'failure') {
          status.value = 'failed'
          error.value = response.data.error_message || '任务处理失败'
        }
        
        return response.data
      }
    } catch (err) {
      console.error('Poll task status failed:', err)
      return null
    }
  }
  
  /**
   * 获取异步任务结果
   */
  async function fetchTaskResult(taskId = null) {
    const id = taskId || currentTaskId.value
    if (!id) return null
    
    loading.value = true
    
    try {
      const response = await processingService.getTaskResult(id)
      
      if (response.success) {
        currentResult.value = response.data
        return response.data
      }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 取消异步任务
   */
  async function cancelTask(taskId = null) {
    const id = taskId || currentTaskId.value
    if (!id) return null
    
    try {
      const response = await processingService.cancelTask(id)
      
      if (response.success && response.data.cancelled) {
        taskStatus.value = 'cancelled'
        status.value = 'idle'
        currentTaskId.value = null
      }
      
      return response.data
    } catch (err) {
      console.error('Cancel task failed:', err)
      throw err
    }
  }
  
  // ==================== 其他方法 ====================
  
  async function fetchResults(documentId, processingType = null) {
    loading.value = true
    error.value = null
    
    try {
      const response = await processingService.getProcessingResults(documentId, processingType)
      
      if (response.success) {
        processingResults.value = response.data
        return response.data
      }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }
  
  async function fetchResultById(resultId) {
    loading.value = true
    error.value = null
    
    try {
      const response = await processingService.getResultById(resultId)
      
      if (response.success) {
        currentResult.value = response.data
        return response.data
      }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }
  
  function clearError() {
    error.value = null
  }
  
  function reset() {
    processingResults.value = []
    currentResult.value = null
    status.value = 'idle'
    error.value = null
    currentTaskId.value = null
    taskProgress.value = 0
    taskStatus.value = null
  }
  
  return {
    // State
    processingResults,
    currentResult,
    status,
    loading,
    error,
    
    // Async task state
    currentTaskId,
    taskProgress,
    taskStatus,
    
    // Actions
    loadDocument,
    loadDocumentAsync,
    pollTaskStatus,
    fetchTaskResult,
    cancelTask,
    fetchResults,
    fetchResultById,
    clearError,
    reset
  }
})
