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
  
  // Actions
  async function loadDocument(documentId, loaderType = 'pymupdf') {
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
  
  async function parseDocument(documentId, parseOption = 'full_text', includeTables = true) {
    loading.value = true
    status.value = 'processing'
    error.value = null
    
    try {
      const response = await processingService.parseDocument(documentId, parseOption, includeTables)
      
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
  }
  
  return {
    // State
    processingResults,
    currentResult,
    status,
    loading,
    error,
    
    // Actions
    loadDocument,
    parseDocument,
    fetchResults,
    fetchResultById,
    clearError,
    reset
  }
})
