/**
 * Processing service - API calls
 */
import apiClient from './api'

const processingService = {
  /**
   * Load document with specified loader
   */
  async loadDocument(documentId, loaderType = 'pymupdf') {
    return apiClient.post('/processing/load', {
      document_id: documentId,
      loader_type: loaderType
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
