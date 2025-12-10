/**
 * Chunking Service - API client for document chunking operations
 */
import api from './api'

class ChunkingService {
  /**
   * Get list of parsed documents ready for chunking
   */
  async getParsedDocuments(page = 1, pageSize = 20, filters = {}) {
    const response = await api.get('/chunking/documents/parsed', {
      params: { 
        page, 
        page_size: pageSize,
        search: filters.search || undefined,
        format: filters.format || undefined,
        sort_by: filters.sortBy || 'upload_time',
        sort_order: filters.sortOrder || 'desc'
      }
    })
    return response
  }

  /**
   * Get available chunking strategies
   */
  async getChunkingStrategies(activeOnly = true) {
    const response = await api.get('/chunking/strategies', {
      params: { active_only: activeOnly }
    })
    return response
  }

  /**
   * Create a new chunking task
   */
  async createChunkingTask(documentId, strategyType, parameters) {
    const response = await api.post('/chunking/chunk', {
      document_id: documentId,
      strategy_type: strategyType,
      parameters
    })
    return response
  }

  /**
   * Get chunking task status
   */
  async getChunkingTask(taskId) {
    const response = await api.get(`/chunking/task/${taskId}`)
    return response
  }

  /**
   * Get chunking result with chunks
   */
  async getChunkingResult(resultId, includeChunks = true, page = 1, pageSize = 50) {
    const response = await api.get(`/chunking/result/${resultId}`, {
      params: {
        include_chunks: includeChunks,
        page,
        page_size: pageSize
      }
    })
    return response
  }

  /**
   * Get chunking history with pagination and filters
   */
  async getChunkingHistory(filters = {}) {
    const response = await api.get('/chunking/history', {
      params: filters
    })
    return response
  }

  /**
   * Delete chunking result
   */
  async deleteChunkingResult(resultId) {
    const response = await api.delete(`/chunking/result/${resultId}`)
    return response
  }

  /**
   * Export chunking result
   */
  async exportChunkingResult(resultId, format = 'json') {
    const response = await api.get(`/chunking/export/${resultId}`, {
      params: { format },
      responseType: format === 'csv' ? 'blob' : 'json'
    })
    return response
  }

  /**
   * Compare multiple chunking results
   */
  async compareResults(resultIds) {
    const response = await api.post('/chunking/compare', {
      result_ids: resultIds
    })
    return response
  }

  /**
   * Get queue status
   */
  async getQueueStatus() {
    const response = await api.get('/chunking/queue')
    return response
  }

  /**
   * Preview chunking strategy on document
   */
  async previewChunking(documentId, strategyType, parameters) {
    const response = await api.post('/chunking/preview', {
      document_id: documentId,
      strategy_type: strategyType,
      parameters
    })
    return response
  }

  /**
   * Get latest chunking result for a document
   * Can optionally filter by strategy and parameters
   */
  async getLatestResultForDocument(documentId, strategyType = null, parameters = null) {
    const params = {
      strategy_type: strategyType
    }
    
    if (parameters) {
      params.parameters = JSON.stringify(parameters)
    }
    
    const response = await api.get(`/chunking/result/latest/${documentId}`, { params })
    return response
  }
}

export default new ChunkingService()
