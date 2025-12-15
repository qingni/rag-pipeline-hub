/**
 * Embedding API client
 */
import apiClient from './api'

const API_KEY = import.meta.env.VITE_EMBEDDING_API_KEY

const buildHeaders = () => {
  if (!API_KEY) {
    return {}
  }
  return {
    'X-API-Key': API_KEY,
  }
}

export const embeddingService = {
  async embedSingle({ text, model, max_retries = 3, timeout = 60 }) {
    return apiClient.post(
      '/embedding/single',
      {
        text,
        model,
        max_retries,
        timeout,
      },
      { headers: buildHeaders() },
    )
  },

  async embedBatch({ texts, model, max_retries = 3, timeout = 60 }) {
    return apiClient.post(
      '/embedding/batch',
      {
        texts,
        model,
        max_retries,
        timeout,
      },
      { headers: buildHeaders() },
    )
  },

  async listModels() {
    return apiClient.get('/embedding/models')
  },

  async getModelInfo(modelName) {
    return apiClient.get(`/embedding/models/${modelName}`)
  },
}
