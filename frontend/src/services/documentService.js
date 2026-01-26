/**
 * Document service - API calls
 */
import apiClient from './api'

const documentService = {
  /**
   * Upload a document
   */
  async uploadDocument(file, onProgress) {
    const formData = new FormData()
    formData.append('file', file)
    
    return apiClient.post('/documents', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 120000,  // 上传超时 2 分钟（小文件 < 10MB）
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(progress)
        }
      }
    })
  },
  
  /**
   * Get documents list with pagination
   */
  async getDocuments(page = 1, pageSize = 20, status = null) {
    const params = { page, page_size: pageSize }
    if (status) {
      params.status = status
    }
    
    return apiClient.get('/documents', { params })
  },
  
  /**
   * Get document by ID
   */
  async getDocumentById(documentId) {
    return apiClient.get(`/documents/${documentId}`)
  },
  
  /**
   * Get document preview
   */
  async getDocumentPreview(documentId, pages = 3) {
    return apiClient.get(`/documents/${documentId}/preview`, {
      params: { pages }
    })
  },
  
  /**
   * Delete document
   */
  async deleteDocument(documentId) {
    return apiClient.delete(`/documents/${documentId}`)
  }
}

export default documentService
