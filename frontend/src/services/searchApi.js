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
  getAvailableIndexes,
  getSearchHistory,
  deleteSearchHistory,
  clearSearchHistory
}
