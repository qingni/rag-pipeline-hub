/**
 * Model recommendation API service.
 * 
 * Provides methods for:
 * - Single document recommendation
 * - Batch document recommendation
 * - Model capability management
 */
import api from './api';

const BASE_URL = '/embedding/recommend';

/**
 * Get model recommendation for a single document.
 * @param {Object} data - Request data
 * @param {string} data.document_id - Document identifier
 * @param {string} data.document_name - Document filename
 * @param {Array} data.chunks - Document chunks
 * @param {number} [data.top_n=3] - Number of recommendations
 * @returns {Promise<Object>} Recommendation result
 */
export const recommendForDocument = async (data) => {
  // api 拦截器已经返回 response.data，直接返回结果即可
  return await api.post(`${BASE_URL}/single`, data);
};

/**
 * Get model recommendation for multiple documents.
 * @param {Object} data - Request data
 * @param {Array} data.documents - List of documents with chunks
 * @param {number} [data.top_n=3] - Number of recommendations
 * @param {number} [data.outlier_threshold] - Outlier detection threshold
 * @returns {Promise<Object>} Batch recommendation result
 */
export const recommendForBatch = async (data) => {
  // api 拦截器已经返回 response.data，直接返回结果即可
  return await api.post(`${BASE_URL}/batch`, data);
};

/**
 * Analyze document features without recommendation.
 * @param {Object} data - Request data
 * @param {string} data.document_id - Document identifier
 * @param {string} data.document_name - Document filename
 * @param {Array} data.chunks - Document chunks
 * @returns {Promise<Object>} Document analysis result
 */
export const analyzeDocumentFeatures = async (data) => {
  // api 拦截器已经返回 response.data，直接返回结果即可
  return await api.post(`${BASE_URL}/analyze`, data);
};

/**
 * List available embedding models.
 * @param {Object} [options] - Query options
 * @param {boolean} [options.enabled_only=true] - Only show enabled models
 * @param {string} [options.model_type] - Filter by type: text, multimodal
 * @returns {Promise<Object>} List of models with capabilities
 */
export const listModels = async (options = {}) => {
  const params = new URLSearchParams();
  if (options.enabled_only !== undefined) {
    params.append('enabled_only', options.enabled_only);
  }
  if (options.model_type) {
    params.append('model_type', options.model_type);
  }
  // api 拦截器已经返回 response.data，直接返回结果即可
  return await api.get(`${BASE_URL}/models?${params}`);
};

/**
 * Get capability details for a specific model.
 * @param {string} modelName - Model identifier
 * @returns {Promise<Object>} Model capability details
 */
export const getModelCapability = async (modelName) => {
  // api 拦截器已经返回 response.data，直接返回结果即可
  return await api.get(`${BASE_URL}/models/${modelName}`);
};

/**
 * Update model capability configuration.
 * @param {string} modelName - Model identifier
 * @param {Object} updates - Fields to update
 * @returns {Promise<Object>} Updated model capability
 */
export const updateModelCapability = async (modelName, updates) => {
  // api 拦截器已经返回 response.data，直接返回结果即可
  return await api.put(`${BASE_URL}/models/${modelName}`, updates);
};

/**
 * Get recommendation algorithm weights.
 * @returns {Promise<Object>} Current weights configuration
 */
export const getRecommendationWeights = async () => {
  // api 拦截器已经返回 response.data，直接返回结果即可
  return await api.get(`${BASE_URL}/weights`);
};

/**
 * Reload model capability configuration.
 * @returns {Promise<Object>} Reload status
 */
export const reloadConfiguration = async () => {
  // api 拦截器已经返回 response.data，直接返回结果即可
  return await api.post(`${BASE_URL}/reload`);
};

export default {
  recommendForDocument,
  recommendForBatch,
  analyzeDocumentFeatures,
  listModels,
  getModelCapability,
  updateModelCapability,
  getRecommendationWeights,
  reloadConfiguration,
};
