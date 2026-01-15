/**
 * Processing service - API calls
 */
import apiClient from './api'

// 文档加载超时时间（5分钟，复杂 PDF 使用 Docling 解析可能需要较长时间）
const DOCUMENT_LOAD_TIMEOUT = 5 * 60 * 1000

const processingService = {
  /**
   * Load document with specified loader (sync mode)
   * @param {string} documentId - Document ID
   * @param {string} loaderType - Loader type (auto, docling, pymupdf, etc.)
   * @param {boolean} enableFallback - Enable fallback to other loaders
   */
  async loadDocument(documentId, loaderType = null, enableFallback = true) {
    return apiClient.post('/processing/load', {
      document_id: documentId,
      loader_type: loaderType,
      enable_fallback: enableFallback
    }, {
      timeout: DOCUMENT_LOAD_TIMEOUT
    })
  },
  
  // ==================== 异步加载 API ====================
  
  /**
   * Submit async loading task
   * @param {string} documentId - Document ID
   * @param {string} loaderType - Loader type (typically 'docling_serve')
   * @returns {Promise<{task_id: string, status: string}>}
   */
  async loadDocumentAsync(documentId, loaderType = null) {
    return apiClient.post('/processing/load/async', {
      document_id: documentId,
      loader_type: loaderType
    })
  },
  
  /**
   * Get async task status
   * @param {string} taskId - Task ID
   * @returns {Promise<{status: string, progress: number}>}
   */
  async getTaskStatus(taskId) {
    return apiClient.get(`/processing/load/task/${taskId}/status`)
  },
  
  /**
   * Get async task result
   * @param {string} taskId - Task ID
   * @returns {Promise<Object>} - Full loading result
   */
  async getTaskResult(taskId) {
    return apiClient.get(`/processing/load/task/${taskId}/result`)
  },
  
  /**
   * Cancel async task
   * @param {string} taskId - Task ID
   */
  async cancelTask(taskId) {
    return apiClient.post(`/processing/load/task/${taskId}/cancel`)
  },
  
  /**
   * List async tasks
   * @param {Object} params - Query params
   */
  async listTasks(params = {}) {
    return apiClient.get('/processing/load/tasks', { params })
  },
  
  // ==================== 其他 API ====================
  
  /**
   * Get processing results for a document
   */
  async getProcessingResults(documentId, processingType = null) {
    const params = {}
    if (processingType) {
      params.processing_type = processingType
    }
    
    return apiClient.get(`/processing/results/${documentId}`, { params })
  },
  
  /**
   * Get processing result by ID
   */
  async getResultById(resultId) {
    return apiClient.get(`/processing/results/detail/${resultId}`)
  }
}

export default processingService
