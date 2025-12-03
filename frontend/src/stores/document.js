/**
 * Document store - Pinia
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import documentService from '../services/documentService'

export const useDocumentStore = defineStore('document', () => {
  // State
  const documents = ref([])
  const currentDocument = ref(null)
  const uploadProgress = ref(0)
  const loading = ref(false)
  const error = ref(null)
  
  // Pagination
  const currentPage = ref(1)
  const pageSize = ref(4)  // 每页显示4个文档
  const totalDocuments = ref(0)
  
  // Actions
  async function uploadDocument(file) {
    loading.value = true
    error.value = null
    uploadProgress.value = 0
    
    try {
      const response = await documentService.uploadDocument(file, (progress) => {
        uploadProgress.value = progress
      })
      
      if (response.success) {
        const uploadedDoc = response.data
        currentDocument.value = uploadedDoc
        
        // 刷新文档列表到第一页，确保新文档显示
        await fetchDocuments(1)
        
        return uploadedDoc
      }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
      uploadProgress.value = 0
    }
  }
  
  async function fetchDocuments(page = 1, status = null) {
    loading.value = true
    error.value = null
    
    try {
      const response = await documentService.getDocuments(page, pageSize.value, status)
      
      if (response.success) {
        documents.value = response.data.items
        currentPage.value = response.data.page
        totalDocuments.value = response.data.total
      }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }
  
  async function fetchDocumentById(documentId) {
    loading.value = true
    error.value = null
    
    try {
      const response = await documentService.getDocumentById(documentId)
      
      if (response.success) {
        currentDocument.value = response.data
        return response.data
      }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }
  
  async function getDocumentPreview(documentId, pages = 3) {
    loading.value = true
    error.value = null
    
    try {
      const response = await documentService.getDocumentPreview(documentId, pages)
      
      if (response.success) {
        return response.data
      }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }
  
  async function deleteDocument(documentId) {
    loading.value = true
    error.value = null
    
    try {
      const response = await documentService.deleteDocument(documentId)
      
      if (response.success) {
        // Remove from documents list
        documents.value = documents.value.filter(d => d.id !== documentId)
        
        if (currentDocument.value?.id === documentId) {
          currentDocument.value = null
        }
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
  
  return {
    // State
    documents,
    currentDocument,
    uploadProgress,
    loading,
    error,
    currentPage,
    pageSize,
    totalDocuments,
    
    // Actions
    uploadDocument,
    fetchDocuments,
    fetchDocumentById,
    getDocumentPreview,
    deleteDocument,
    clearError
  }
})
