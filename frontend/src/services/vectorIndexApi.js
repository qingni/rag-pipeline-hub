/**
 * 向量索引 API 服务
 * 
 * 提供向量索引管理的所有 API 调用方法
 */

import axios from 'axios';

// 向量索引 API 使用独立的基础路径，不依赖 VITE_API_BASE_URL（因为它包含 /api/v1）
const BASE_URL = 'http://localhost:8000';
const VECTOR_INDEX_API = `${BASE_URL}/api/vector-index`;

/**
 * 创建向量索引
 * @param {Object} indexData - 索引数据
 * @param {string} indexData.index_name - 索引名称
 * @param {number} indexData.dimension - 向量维度
 * @param {string} indexData.index_type - 索引类型 (MILVUS/FAISS)
 * @param {string} indexData.metric_type - 度量类型 (cosine/euclidean/dot_product)
 * @param {string} indexData.description - 索引描述
 * @returns {Promise<Object>} 创建的索引对象
 */
export async function createIndex(indexData) {
  try {
    const response = await axios.post(`${VECTOR_INDEX_API}/indexes`, indexData);
    return response.data;
  } catch (error) {
    console.error('Failed to create index:', error);
    throw error;
  }
}

/**
 * 获取索引列表
 * @param {number} skip - 跳过的记录数
 * @param {number} limit - 返回的记录数
 * @returns {Promise<Array>} 索引列表
 */
export async function listIndexes(skip = 0, limit = 100) {
  try {
    const response = await axios.get(`${VECTOR_INDEX_API}/indexes`, {
      params: { skip, limit }
    });
    return response.data;
  } catch (error) {
    console.error('Failed to list indexes:', error);
    throw error;
  }
}

/**
 * 获取索引详情
 * @param {number} indexId - 索引 ID
 * @returns {Promise<Object>} 索引对象
 */
export async function getIndex(indexId) {
  try {
    const response = await axios.get(`${VECTOR_INDEX_API}/indexes/${indexId}`);
    return response.data;
  } catch (error) {
    console.error('Failed to get index:', error);
    throw error;
  }
}

/**
 * 删除索引
 * @param {number} indexId - 索引 ID
 * @returns {Promise<void>}
 */
export async function deleteIndex(indexId) {
  try {
    await axios.delete(`${VECTOR_INDEX_API}/indexes/${indexId}`);
  } catch (error) {
    console.error('Failed to delete index:', error);
    throw error;
  }
}

/**
 * 向索引添加向量
 * @param {number} indexId - 索引 ID
 * @param {Object} data - 向量数据
 * @param {Array<Array<number>>} data.vectors - 向量列表
 * @param {Array<Object>} data.metadata - 元数据列表
 * @returns {Promise<Object>} 添加结果
 */
export async function addVectors(indexId, data) {
  try {
    const response = await axios.post(
      `${VECTOR_INDEX_API}/indexes/${indexId}/vectors`,
      data
    );
    return response.data;
  } catch (error) {
    console.error('Failed to add vectors:', error);
    throw error;
  }
}

/**
 * 向量相似度搜索
 * @param {number} indexId - 索引 ID
 * @param {Object} searchData - 搜索数据
 * @param {Array<number>} searchData.query_vector - 查询向量
 * @param {number} searchData.top_k - 返回结果数量
 * @param {Object} searchData.filters - 过滤条件
 * @param {boolean} searchData.save_result - 是否保存结果
 * @returns {Promise<Object>} 搜索结果
 */
export async function searchVectors(indexId, searchData) {
  try {
    const response = await axios.post(
      `${VECTOR_INDEX_API}/indexes/${indexId}/search`,
      searchData
    );
    return response.data;
  } catch (error) {
    console.error('Failed to search vectors:', error);
    throw error;
  }
}

/**
 * 获取索引统计信息
 * @param {number} indexId - 索引 ID
 * @returns {Promise<Object>} 统计信息
 */
export async function getIndexStatistics(indexId) {
  try {
    const response = await axios.get(
      `${VECTOR_INDEX_API}/indexes/${indexId}/statistics`
    );
    return response.data;
  } catch (error) {
    console.error('Failed to get index statistics:', error);
    throw error;
  }
}

/**
 * 获取查询历史
 * @param {number} indexId - 索引 ID
 * @param {number} limit - 返回记录数
 * @returns {Promise<Array>} 查询历史列表
 */
export async function getQueryHistory(indexId, limit = 100) {
  try {
    const response = await axios.get(
      `${VECTOR_INDEX_API}/indexes/${indexId}/history`,
      { params: { limit } }
    );
    return response.data;
  } catch (error) {
    console.error('Failed to get query history:', error);
    throw error;
  }
}

/**
 * 健康检查
 * @returns {Promise<Object>} 健康状态
 */
export async function healthCheck() {
  try {
    const response = await axios.get(`${VECTOR_INDEX_API}/health`);
    return response.data;
  } catch (error) {
    console.error('Health check failed:', error);
    throw error;
  }
}
