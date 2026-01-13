/**
 * Processing service - API calls
 */
import apiClient from './api'

// 文档加载超时时间（5分钟，复杂 PDF 使用 Docling 解析可能需要较长时间）
const DOCUMENT_LOAD_TIMEOUT = 5 * 60 * 1000

const processingService = {
  /**
   * Load document with specified loader
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
