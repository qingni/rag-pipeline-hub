/**
 * 搜索查询 API 服务
 * 
 * 提供与后端搜索 API 交互的方法
 */
import api from './api'

const BASE_URL = '/search'

/**
 * 执行语义搜索
 * @param {Object} params - 搜索参数
 * @param {string} params.query_text - 查询文本
 * @param {string[]} [params.index_ids] - 目标索引ID列表
 * @param {number} [params.top_k=10] - 返回结果数量
 * @param {number} [params.threshold=0.5] - 相似度阈值
 * @param {string} [params.metric_type='cosine'] - 相似度计算方法
 * @returns {Promise<Object>} 搜索响应
 */
export async function executeSearch(params) {
  return await api.post(BASE_URL, params)
}

/**
 * 执行混合检索（稠密+稀疏双路召回 + RRF + Reranker）
 * @param {Object} params - 搜索参数
 * @param {string} params.query_text - 查询文本
 * @param {string[]} [params.collection_ids] - 目标 Collection ID 列表（最多5个）
 * @param {number} [params.top_k=10] - 最终返回结果数量
 * @param {number} [params.threshold=0.5] - 相似度阈值
 * @param {string} [params.search_mode='auto'] - 检索模式 (auto/hybrid/dense_only)
 * @param {number} [params.reranker_top_n=20] - Reranker 候选集大小
 * @param {number} [params.reranker_top_k] - Reranker 最终返回数
 * @param {number} [params.page=1] - 页码
 * @param {number} [params.page_size=10] - 每页数量
 * @returns {Promise<Object>} 混合检索响应
 */
export async function executeHybridSearch(params) {
  return await api.post(`${BASE_URL}/hybrid`, params)
}

/**
 * 获取 Reranker 健康状态
 * @returns {Promise<Object>} Reranker 健康检查响应
 */
export async function getRerankerHealth() {
  return await api.get(`${BASE_URL}/reranker/health`)
}

/**
 * 获取可用 Collection 列表（含 has_sparse 标识）
 * @returns {Promise<Object>} Collection 列表响应
 */
export async function getAvailableCollections() {
  return await api.get(`${BASE_URL}/collections`)
}

/**
 * 获取可用索引列表
 * @returns {Promise<Object>} 索引列表响应
 */
export async function getAvailableIndexes() {
  return await api.get(`${BASE_URL}/indexes`)
}

/**
 * 获取搜索历史
 * @param {Object} params - 分页参数
 * @param {number} [params.limit=20] - 返回数量
 * @param {number} [params.offset=0] - 偏移量
 * @returns {Promise<Object>} 历史列表响应
 */
export async function getSearchHistory(params = {}) {
  return await api.get(`${BASE_URL}/history`, { params })
}

/**
 * 删除单条历史记录
 * @param {string} historyId - 历史记录ID
 * @returns {Promise<Object>} 成功响应
 */
export async function deleteSearchHistory(historyId) {
  return await api.delete(`${BASE_URL}/history/${historyId}`)
}

/**
 * 清空所有历史记录
 * @returns {Promise<Object>} 成功响应
 */
export async function clearSearchHistory() {
  return await api.delete(`${BASE_URL}/history`)
}

export default {
  executeSearch,
  executeHybridSearch,
  getAvailableIndexes,
  getAvailableCollections,
  getRerankerHealth,
  getSearchHistory,
  deleteSearchHistory,
  clearSearchHistory
}
