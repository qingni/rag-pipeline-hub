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

const embeddingService = {
  /**
   * 获取有分块结果的文档列表
   * @param {Object} params - 请求参数
   */
  async getDocumentsWithChunking(params = {}) {
    return apiClient.get('/documents', {
      params: {
        has_chunking_result: true,
        page: params.page || 1,
        page_size: params.page_size || 100
      }
    })
  },

  /**
   * 从分块结果进行向量化
   * @param {Object} params - 请求参数
   * @param {string} params.result_id - 分块结果ID
   * @param {string} params.model - 向量模型名称
   * @param {number} params.max_retries - 最大重试次数
   * @param {number} params.timeout - 超时时间（秒）
   */
  async embedFromChunkingResult({ result_id, model, max_retries = 3, timeout = 60 }) {
    return apiClient.post(
      '/embedding/from-chunking-result',
      {
        result_id,
        model,
        max_retries,
        timeout,
      },
      { headers: buildHeaders() },
    )
  },

  /**
   * 从文档进行向量化（使用最新的活跃分块结果）
   * @param {Object} params - 请求参数
   * @param {number} params.document_id - 文档ID
   * @param {string} params.model - 向量模型名称
   * @param {string} params.strategy_type - 可选的分块策略过滤
   * @param {number} params.max_retries - 最大重试次数
   * @param {number} params.timeout - 超时时间（秒）
   */
  async embedFromDocument({ document_id, model, strategy_type = null, max_retries = 3, timeout = 60 }) {
    const payload = {
      document_id,
      model,
      max_retries,
      timeout,
    }
    
    if (strategy_type) {
      payload.strategy_type = strategy_type
    }
    
    return apiClient.post(
      '/embedding/from-document',
      payload,
      { headers: buildHeaders() },
    )
  },

  /**
   * 单文本向量化（backend-only API）
   */
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

  /**
   * 批量文本向量化（backend-only API）
   */
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

  /**
   * 获取所有可用的向量模型
   */
  async listModels() {
    return apiClient.get('/embedding/models')
  },

  /**
   * 获取特定模型信息
   * @param {string} modelName - 模型名称
   */
  async getModelInfo(modelName) {
    return apiClient.get(`/embedding/models/${modelName}`)
  },

  /**
   * 获取文档的最新向量化结果
   * @param {number} documentId - 文档ID
   * @param {string} model - 可选的模型过滤
   */
  async getLatestByDocument(documentId, model = null) {
    const params = model ? { model } : {}
    return apiClient.get(`/embedding/results/by-document/${documentId}`, { params })
  },

  /**
   * 根据结果ID获取向量化结果
   * @param {string} resultId - 结果ID
   */
  async getResultById(resultId) {
    return apiClient.get(`/embedding/results/${resultId}`)
  },

  /**
   * 列出向量化结果（带分页和过滤）
   * @param {Object} params - 查询参数
   */
  async listResults(params = {}) {
    return apiClient.get('/embedding/results', { params })
  },

  /**
   * 删除向量化结果
   * @param {string} resultId - 结果ID
   */
  async deleteResult(resultId) {
    return apiClient.delete(`/embedding/results/${resultId}`)
  },
}

export default embeddingService
