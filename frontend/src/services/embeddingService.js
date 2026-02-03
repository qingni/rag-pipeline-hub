/**
 * Embedding service for frontend.
 * 
 * Provides:
 * - Document embedding operations
 * - Result export functionality
 * - Statistics queries
 */

const API_BASE = '/api/v1'

/**
 * Start document embedding
 * @param {Object} params - Embedding parameters
 * @returns {Promise<Object>} - Task information
 */
export async function startEmbedding(params) {
  const response = await fetch(`${API_BASE}/embedding/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to start embedding')
  }
  
  return response.json()
}

/**
 * Get embedding task status
 * @param {string} taskId - Task ID
 * @returns {Promise<Object>} - Task status
 */
export async function getTaskStatus(taskId) {
  const response = await fetch(`${API_BASE}/embedding/tasks/${taskId}`)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to get task status')
  }
  
  return response.json()
}

/**
 * Cancel embedding task
 * @param {string} taskId - Task ID
 * @returns {Promise<Object>} - Cancellation result
 */
export async function cancelTask(taskId) {
  const response = await fetch(`${API_BASE}/embedding/tasks/${taskId}/cancel`, {
    method: 'POST',
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to cancel task')
  }
  
  return response.json()
}

/**
 * Get embedding result
 * @param {string} resultId - Result ID
 * @returns {Promise<Object>} - Embedding result
 */
export async function getResult(resultId) {
  const response = await fetch(`${API_BASE}/embedding/results/${resultId}`)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to get result')
  }
  
  return response.json()
}

/**
 * Get embedding results for document
 * @param {string} documentId - Document ID
 * @returns {Promise<Array>} - List of results
 */
export async function getDocumentResults(documentId) {
  const response = await fetch(`${API_BASE}/embedding/documents/${documentId}/results`)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to get document results')
  }
  
  return response.json()
}

/**
 * Set active embedding result
 * @param {string} resultId - Result ID to activate
 * @returns {Promise<Object>} - Activation result
 */
export async function activateResult(resultId) {
  const response = await fetch(`${API_BASE}/embedding/results/${resultId}/activate`, {
    method: 'POST',
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to activate result')
  }
  
  return response.json()
}

/**
 * Delete embedding result (only non-active results)
 * @param {string} resultId - Result ID to delete
 * @returns {Promise<Object>} - Deletion result
 */
export async function deleteResult(resultId) {
  const response = await fetch(`${API_BASE}/embedding/results/${resultId}`, {
    method: 'DELETE',
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to delete result')
  }
  
  return response.json()
}

/**
 * Compare embedding results
 * @param {Array<string>} resultIds - Result IDs to compare
 * @returns {Promise<Object>} - Comparison data
 */
export async function compareResults(resultIds) {
  const response = await fetch(`${API_BASE}/embedding/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ result_ids: resultIds }),
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to compare results')
  }
  
  return response.json()
}

/**
 * Get embedding statistics
 * @param {string} resultId - Result ID
 * @returns {Promise<Object>} - Statistics data
 */
export async function getStatistics(resultId) {
  const response = await fetch(`${API_BASE}/embedding/results/${resultId}/statistics`)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to get statistics')
  }
  
  return response.json()
}

/**
 * Export embedding result to JSON
 * @param {string} resultId - Result ID
 * @param {Object} options - Export options
 * @returns {Promise<Blob>} - JSON file blob
 */
export async function exportToJson(resultId, options = {}) {
  const params = new URLSearchParams()
  if (options.includeVectors !== undefined) {
    params.set('include_vectors', options.includeVectors)
  }
  if (options.includeMetadata !== undefined) {
    params.set('include_metadata', options.includeMetadata)
  }
  
  const url = `${API_BASE}/embedding/results/${resultId}/export?${params.toString()}`
  const response = await fetch(url)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to export result')
  }
  
  return response.blob()
}

/**
 * Download export as file
 * @param {string} resultId - Result ID
 * @param {string} filename - Optional filename
 * @param {Object} options - Export options
 */
export async function downloadExport(resultId, filename = null, options = {}) {
  try {
    const blob = await exportToJson(resultId, options)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename || `embedding-${resultId}-${Date.now()}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Download failed:', error)
    throw error
  }
}

/**
 * Get available embedding models
 * @returns {Promise<Array>} - List of models
 */
export async function getAvailableModels() {
  const response = await fetch(`${API_BASE}/embedding/models`)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to get models')
  }
  
  return response.json()
}

/**
 * Get documents that have been chunked (ready for embedding)
 * @param {Object} params - Query parameters
 * @returns {Promise<Object>} - Documents list with pagination
 */
export async function getDocumentsWithChunking(params = {}) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', params.page)
  if (params.page_size) searchParams.set('page_size', params.page_size)
  
  const url = `${API_BASE}/embedding/documents?${searchParams.toString()}`
  const response = await fetch(url)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to get documents')
  }
  
  return response.json()
}

/**
 * Start embedding from a document
 * @param {Object} params - Embedding parameters
 * @returns {Promise<Object>} - Embedding result or task info
 */
export async function embedFromDocument(params) {
  const response = await fetch(`${API_BASE}/embedding/embed`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to start embedding')
  }
  
  return response.json()
}

/**
 * Get latest embedding result for a document
 * @param {string} documentId - Document ID
 * @param {string} modelFilter - Optional model filter
 * @returns {Promise<Object>} - Latest embedding result
 */
export async function getLatestByDocument(documentId, modelFilter = null) {
  const searchParams = new URLSearchParams()
  if (modelFilter) searchParams.set('model', modelFilter)
  
  const queryString = searchParams.toString()
  const url = `${API_BASE}/embedding/documents/${documentId}/latest${queryString ? '?' + queryString : ''}`
  const response = await fetch(url)
  
  if (!response.ok) {
    const error = await response.json()
    const err = new Error(error.detail || 'Failed to get latest result')
    err.status = response.status
    throw err
  }
  
  return response.json()
}

/**
 * List embedding results with pagination
 * @param {Object} params - Query parameters
 * @returns {Promise<Object>} - Results list with pagination
 */
export async function listResults(params = {}) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', params.page)
  if (params.page_size) searchParams.set('page_size', params.page_size)
  if (params.document_id) searchParams.set('document_id', params.document_id)
  
  const url = `${API_BASE}/embedding/results?${searchParams.toString()}`
  const response = await fetch(url)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to list results')
  }
  
  return response.json()
}

/**
 * Get embedding result by ID
 * @param {string} resultId - Result ID
 * @returns {Promise<Object>} - Embedding result details
 */
export async function getResultById(resultId) {
  const response = await fetch(`${API_BASE}/embedding/results/${resultId}`)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to get result')
  }
  
  return response.json()
}

/**
 * Format bytes to human readable string
 * @param {number} bytes - Bytes value
 * @returns {string} - Formatted string
 */
export function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/**
 * Format duration in milliseconds
 * @param {number} ms - Duration in milliseconds
 * @returns {string} - Formatted string
 */
export function formatDuration(ms) {
  if (!ms) return '-'
  if (ms < 1000) return `${ms.toFixed(0)}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}min`
}

export default {
  startEmbedding,
  getTaskStatus,
  cancelTask,
  getResult,
  getDocumentResults,
  activateResult,
  deleteResult,
  compareResults,
  getStatistics,
  exportToJson,
  downloadExport,
  getAvailableModels,
  getDocumentsWithChunking,
  embedFromDocument,
  getLatestByDocument,
  listResults,
  getResultById,
  formatBytes,
  formatDuration,
}
