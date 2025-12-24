/**
 * 向量索引 API 服务
 * 
 * 提供向量索引管理的所有 API 调用方法
 * 
 * 2024-12-24 更新: 添加向量化任务集成 API
 */

import axios from 'axios';

// 向量索引 API 使用独立的基础路径
const BASE_URL = 'http://localhost:8000';
const VECTOR_INDEX_API = `${BASE_URL}/api/vector-index`;

// ==================== 向量化任务集成 API ====================

/**
 * 获取可用的向量化任务列表
 * @param {Object} params - 查询参数
 * @param {string} params.status - 过滤任务状态 (SUCCESS, PARTIAL_SUCCESS)
 * @param {number} params.limit - 返回数量限制
 * @param {number} params.offset - 分页偏移量
 * @returns {Promise<Object>} 向量化任务列表
 */
export async function getEmbeddingTasks(params = {}) {
  try {
    const response = await axios.get(`${VECTOR_INDEX_API}/embedding-tasks`, {
      params: {
        status: params.status || 'SUCCESS',
        limit: params.limit || 50,
        offset: params.offset || 0
      }
    });
    return response.data;
  } catch (error) {
    console.error('Failed to get embedding tasks:', error);
    throw error;
  }
}

/**
 * 从向量化任务创建索引
 * @param {Object} data - 创建参数
 * @param {string} data.embedding_result_id - 向量化任务结果ID
 * @param {string} data.name - 索引名称（可选）
 * @param {string} data.provider - 向量数据库 (FAISS/MILVUS)
 * @param {string} data.index_type - 索引算法类型
 * @param {string} data.metric_type - 相似度度量方法
 * @param {Object} data.index_params - 索引参数
 * @param {string} data.namespace - 命名空间
 * @returns {Promise<Object>} 创建的索引对象
 */
export async function createIndexFromEmbedding(data) {
  try {
    const response = await axios.post(`${VECTOR_INDEX_API}/indexes/from-embedding`, data);
    return response.data;
  } catch (error) {
    console.error('Failed to create index from embedding:', error);
    throw error;
  }
}

/**
 * 获取索引历史记录
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页数量
 * @param {string} params.sort_by - 排序字段
 * @param {string} params.sort_order - 排序方向
 * @returns {Promise<Object>} 历史记录列表
 */
export async function getIndexHistory(params = {}) {
  try {
    const response = await axios.get(`${VECTOR_INDEX_API}/indexes/history`, {
      params: {
        page: params.page || 1,
        page_size: params.page_size || 20,
        sort_by: params.sort_by || 'created_at',
        sort_order: params.sort_order || 'desc'
      }
    });
    return response.data;
  } catch (error) {
    console.error('Failed to get index history:', error);
    throw error;
  }
}

/**
 * 查找匹配条件的已存在索引
 * @param {Object} params - 查询参数
 * @param {string} params.embedding_result_id - 向量化任务结果ID
 * @param {string} params.provider - 向量数据库类型
 * @param {string} params.algorithm_type - 索引算法类型
 * @param {string} params.metric_type - 度量类型
 * @returns {Promise<Object>} { found: boolean, index: Object|null }
 */
export async function findMatchingIndex(params) {
  try {
    const response = await axios.get(`${VECTOR_INDEX_API}/indexes/find-matching`, {
      params: {
        embedding_result_id: params.embedding_result_id,
        provider: params.provider,
        algorithm_type: params.algorithm_type,
        metric_type: params.metric_type
      }
    });
    return response.data;
  } catch (error) {
    console.error('Failed to find matching index:', error);
    throw error;
  }
}

// ==================== 原有 API ====================

/**
 * 创建向量索引
 * @param {Object} indexData - 索引数据
 * @param {string} indexData.index_name - 索引名称
 * @param {number} indexData.dimension - 向量维度
 * @param {string} indexData.index_type - 索引类型 (MILVUS/FAISS)
 * @param {string} indexData.algorithm_type - 算法类型
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
 * @param {string} namespace - 命名空间筛选
 * @param {string} status - 状态筛选
 * @returns {Promise<Array>} 索引列表
 */
export async function listIndexes(skip = 0, limit = 100, namespace = null, status = null) {
  try {
    const params = { skip, limit };
    if (namespace) params.namespace = namespace;
    if (status) params.status = status;
    
    const response = await axios.get(`${VECTOR_INDEX_API}/indexes`, { params });
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
 * @param {number} searchData.threshold - 相似度阈值
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
 * 批量向量搜索
 * @param {number} indexId - 索引 ID
 * @param {Object} searchData - 搜索数据
 * @param {Array<Array<number>>} searchData.query_vectors - 查询向量列表
 * @param {number} searchData.top_k - 返回结果数量
 * @param {number} searchData.threshold - 相似度阈值
 * @returns {Promise<Object>} 批量搜索结果
 */
export async function batchSearchVectors(indexId, searchData) {
  try {
    const response = await axios.post(
      `${VECTOR_INDEX_API}/indexes/${indexId}/batch-search`,
      searchData
    );
    return response.data;
  } catch (error) {
    console.error('Failed to batch search vectors:', error);
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
      `${VECTOR_INDEX_API}/indexes/${indexId}/query-history`,
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

// ==================== 持久化 API ====================

/**
 * 持久化索引到磁盘
 * @param {number} indexId - 索引 ID
 * @returns {Promise<Object>} 持久化结果
 */
export async function persistIndex(indexId) {
  try {
    const response = await axios.post(
      `${VECTOR_INDEX_API}/indexes/${indexId}/persist`
    );
    return response.data;
  } catch (error) {
    console.error('Failed to persist index:', error);
    throw error;
  }
}

/**
 * 从磁盘恢复索引
 * @param {number} indexId - 索引 ID
 * @returns {Promise<Object>} 恢复结果
 */
export async function recoverIndex(indexId) {
  try {
    const response = await axios.post(
      `${VECTOR_INDEX_API}/indexes/${indexId}/recover`
    );
    return response.data;
  } catch (error) {
    console.error('Failed to recover index:', error);
    throw error;
  }
}

// ==================== 向量 CRUD API ====================

/**
 * 删除向量
 * @param {number} indexId - 索引 ID
 * @param {Array<string>} vectorIds - 要删除的向量 ID 列表
 * @returns {Promise<Object>} 删除结果
 */
export async function deleteVectors(indexId, vectorIds) {
  try {
    const response = await axios.delete(
      `${VECTOR_INDEX_API}/indexes/${indexId}/vectors`,
      { data: { vector_ids: vectorIds } }
    );
    return response.data;
  } catch (error) {
    console.error('Failed to delete vectors:', error);
    throw error;
  }
}

/**
 * 更新向量
 * @param {number} indexId - 索引 ID
 * @param {Object} data - 更新数据
 * @param {string} data.vector_id - 向量 ID
 * @param {Array<number>} data.vector - 新的向量数据
 * @param {Object} data.metadata - 新的元数据
 * @returns {Promise<Object>} 更新结果
 */
export async function updateVector(indexId, data) {
  try {
    const response = await axios.put(
      `${VECTOR_INDEX_API}/indexes/${indexId}/vectors`,
      data
    );
    return response.data;
  } catch (error) {
    console.error('Failed to update vector:', error);
    throw error;
  }
}

// 导出所有 API 方法
export default {
  // 向量化任务集成
  getEmbeddingTasks,
  createIndexFromEmbedding,
  getIndexHistory,
  findMatchingIndex,
  // 原有 API
  createIndex,
  listIndexes,
  getIndex,
  deleteIndex,
  addVectors,
  searchVectors,
  batchSearchVectors,
  getIndexStatistics,
  getQueryHistory,
  healthCheck,
  // 持久化 API
  persistIndex,
  recoverIndex,
  // 向量 CRUD
  deleteVectors,
  updateVector
};
