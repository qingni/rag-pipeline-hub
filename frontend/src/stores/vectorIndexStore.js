/**
 * 向量索引 Pinia Store
 * 
 * 管理向量索引的全局状态
 * 
 * 2024-12-24 更新: 添加向量化任务和配置状态
 */

import { defineStore } from 'pinia';
import {
  listIndexes,
  getIndex,
  createIndex,
  deleteIndex,
  addVectors,
  searchVectors,
  getIndexStatistics,
  getQueryHistory,
  getEmbeddingTasks,
  createIndexFromEmbedding,
  getIndexHistory,
  clearAllIndexHistory,
  persistIndex,
  recoverIndex,
  deleteVectors,
  updateVector,
  hybridSearch,
  rerankerHealthCheck,
  getRecommendation,
  logRecommendation,
  getRecommendStats,
  getCollections
} from '../services/vectorIndexApi';
export const useVectorIndexStore = defineStore('vectorIndex', {
  state: () => ({
    // 索引列表
    indexes: [],
    // 当前选中的索引
    currentIndex: null,
    // 索引统计信息
    statistics: null,
    // 查询历史
    queryHistory: [],
    // 搜索结果
    searchResults: null,
    
    // ==================== Collection 管理状态 ====================
    // 可用的 Collection 列表
    collections: [],
    // 当前选中的 Collection（创建索引时的目标 Collection）
    selectedCollection: null,  // null 表示使用默认 Collection
    
    // ==================== Collection 管理状态 ====================
    // 可用的 Collection 列表
    collections: [],
    // 当前选中的 Collection（创建索引时的目标 Collection）
    selectedCollection: null,  // null 表示使用默认 Collection
    
    // ==================== 混合检索状态 ====================
    // 混合检索结果
    hybridSearchResults: null,
    // 混合检索模式
    searchMode: 'dense', // 'dense' | 'hybrid'
    // Reranker 健康状态
    rerankerHealth: null,
    // 混合检索参数
    hybridSearchParams: {
      top_n: 20,
      top_k: 5,
      enable_reranker: true,
      rrf_k: 60
    },
    
    // ==================== 智能推荐状态 ====================
    // 推荐结果
    recommendation: null,
    // 推荐统计
    recommendStats: null,
    // 推荐加载状态
    recommendLoading: false,
    
    // ==================== 向量化任务集成状态 ====================
    // 向量化任务列表
    embeddingTasks: [],
    embeddingTasksTotal: 0,
    // 当前选中的向量化任务
    selectedTaskId: null,
    selectedTask: null,
    
    // 配置选项
    selectedDatabase: 'MILVUS',  // 仅支持 Milvus
    selectedAlgorithm: 'FLAT',  // FLAT | HNSW | IVF_FLAT | IVF_SQ8 | IVF_PQ
    algorithmParams: {},
    metricType: 'cosine',
    namespace: 'default',
    
    // 索引历史
    indexHistory: [],
    indexHistoryPagination: {
      page: 1,
      pageSize: 20,
      total: 0,
      totalPages: 0
    },
    
    // 加载状态
    loading: {
      list: false,
      create: false,
      delete: false,
      addVectors: false,
      search: false,
      statistics: false,
      history: false,
      embeddingTasks: false,
      createFromEmbedding: false,
      indexHistory: false,
      hybridSearch: false,
      recommend: false
    },
    // 错误信息
    error: null
  }),

  getters: {
    /**
     * 获取索引总数
     */
    indexCount: (state) => state.indexes.length,

    /**
     * 获取 READY 状态的索引数量
     */
    readyIndexCount: (state) => 
      state.indexes.filter(idx => idx.status === 'READY').length,

    /**
     * 获取当前索引的向量总数
     */
    currentVectorCount: (state) => 
      state.statistics?.vector_count || 0,

    /**
     * 获取当前索引的查询总数
     */
    currentQueryCount: (state) => 
      state.statistics?.total_queries || 0,

    /**
     * 是否有任何加载中的操作
     */
    isLoading: (state) => 
      Object.values(state.loading).some(val => val),

    /**
     * 根据选择的数据库获取可用算法
     */
    availableAlgorithms: (state) => {
      if (state.selectedDatabase === 'MILVUS') {
        return ['FLAT', 'IVF_FLAT', 'IVF_SQ8', 'IVF_PQ', 'HNSW'];
      }
      return ['FLAT', 'IVF_FLAT', 'IVF_SQ8', 'IVF_PQ', 'HNSW'];
    },

    /**
     * 是否可以开始索引
     */
    canStartIndexing: (state) => {
      return state.selectedTaskId && 
             state.selectedDatabase && 
             state.selectedAlgorithm &&
             !state.loading.createFromEmbedding;
    },

    /**
     * 获取选中任务的维度
     */
    selectedTaskDimension: (state) => {
      return state.selectedTask?.vector_dimension || 0;
    }
  },

  actions: {
    // ==================== Collection 管理 Actions ====================

    /**
     * 加载 Collection 列表
     */
    async fetchCollections() {
      try {
        const result = await getCollections();
        this.collections = result.collections || [];
        return result;
      } catch (error) {
        console.error('加载 Collection 列表失败:', error);
        this.collections = [];
        return { collections: [], total: 0 };
      }
    },

    /**
     * 选择目标 Collection
     * @param {string|null} collectionName - Collection 名称，null 表示使用默认
     */
    setSelectedCollection(collectionName) {
      this.selectedCollection = collectionName;
    },

    // ==================== 向量化任务集成 Actions ====================

    /**
     * 加载向量化任务列表
     */
    async fetchEmbeddingTasks(params = {}) {
      this.loading.embeddingTasks = true;
      this.error = null;
      
      try {
        const result = await getEmbeddingTasks({
          status: params.status || 'SUCCESS',
          limit: params.limit || 50,
          offset: params.offset || 0
        });
        
        this.embeddingTasks = result.tasks || [];
        this.embeddingTasksTotal = result.total || 0;
        
        return result;
      } catch (error) {
        this.error = error.response?.data?.detail || '加载向量化任务失败';
        throw error;
      } finally {
        this.loading.embeddingTasks = false;
      }
    },

    /**
     * 选择向量化任务
     */
    selectEmbeddingTask(taskId) {
      this.selectedTaskId = taskId;
      this.selectedTask = this.embeddingTasks.find(t => t.result_id === taskId) || null;
      
      // 清除上次推荐结果
      this.recommendation = null;
      
      // 自动获取推荐
      if (this.selectedTask) {
        this.fetchRecommendation();
      }
    },

    /**
     * 从向量化任务创建索引
     */
    async createIndexFromEmbedding(options = {}) {
      // 支持传入 embedding_result_id 或使用 store 中的 selectedTaskId
      const embeddingResultId = options.embedding_result_id || this.selectedTaskId;
      
      if (!embeddingResultId) {
        throw new Error('请先选择向量化任务');
      }
      
      this.loading.createFromEmbedding = true;
      this.error = null;
      
      try {
        const data = {
          embedding_result_id: embeddingResultId,
          name: options.name || null,
          collection_name: options.collection_name || this.selectedCollection || null,
          provider: options.provider || this.selectedDatabase,
          index_type: options.index_type || this.selectedAlgorithm,
          metric_type: options.metric_type || this.metricType,
          index_params: options.index_params || this.algorithmParams,
          namespace: options.namespace || this.namespace
        };
        
        const newIndex = await createIndexFromEmbedding(data);
        
        // 添加到索引列表
        this.indexes.unshift(newIndex);
        this.currentIndex = newIndex;
        
        // 刷新历史记录
        await this.fetchIndexHistory();
        
        return newIndex;
      } catch (error) {
        this.error = error.response?.data?.detail || '创建索引失败';
        throw error;
      } finally {
        this.loading.createFromEmbedding = false;
      }
    },

    /**
     * 加载索引历史记录
     */
    async fetchIndexHistory(params = {}) {
      this.loading.indexHistory = true;
      this.error = null;
      
      try {
        const result = await getIndexHistory({
          page: params.page || this.indexHistoryPagination.page,
          page_size: params.page_size || this.indexHistoryPagination.pageSize,
          sort_by: params.sort_by || 'created_at',
          sort_order: params.sort_order || 'desc'
        });
        
        this.indexHistory = result.items || [];
        this.indexHistoryPagination = {
          page: result.page,
          pageSize: result.page_size,
          total: result.total,
          totalPages: result.total_pages
        };
        
        return result;
      } catch (error) {
        this.error = error.response?.data?.detail || '加载历史记录失败';
        throw error;
      } finally {
        this.loading.indexHistory = false;
      }
    },

    /**
     * 设置数据库类型
     */
    setDatabase(database) {
      this.selectedDatabase = database;
      
      // 如果当前算法不可用，切换到默认算法
      if (!this.availableAlgorithms.includes(this.selectedAlgorithm)) {
        this.selectedAlgorithm = 'FLAT';
      }
    },

    /**
     * 设置算法类型
     */
    setAlgorithm(algorithm) {
      this.selectedAlgorithm = algorithm;
      
      // 设置默认参数
      switch (algorithm) {
        case 'HNSW':
          this.algorithmParams = { M: 16, efConstruction: 200 };
          break;
        case 'IVF_FLAT':
        case 'IVF_PQ':
          this.algorithmParams = { nlist: 1024 };
          break;
        default:
          this.algorithmParams = {};
      }
    },

    /**
     * 设置算法参数
     */
    setAlgorithmParams(params) {
      this.algorithmParams = { ...this.algorithmParams, ...params };
    },

    /**
     * 重置配置
     */
    resetConfig() {
      this.selectedTaskId = null;
      this.selectedTask = null;
      this.selectedDatabase = 'MILVUS';  // 默认使用 Milvus
      this.selectedAlgorithm = 'FLAT';   // 默认使用 FLAT
      this.algorithmParams = {};
      this.metricType = 'cosine';
      this.namespace = 'default';
    },

    // ==================== 原有 Actions ====================

    /**
     * 加载索引列表
     */
    async fetchIndexes(skip = 0, limit = 100) {
      this.loading.list = true;
      this.error = null;
      
      try {
        this.indexes = await listIndexes(skip, limit);
      } catch (error) {
        this.error = error.response?.data?.detail || '加载索引列表失败';
        throw error;
      } finally {
        this.loading.list = false;
      }
    },

    /**
     * 获取索引详情
     */
    async fetchIndex(indexId) {
      this.loading.list = true;
      this.error = null;
      
      try {
        this.currentIndex = await getIndex(indexId);
        return this.currentIndex;
      } catch (error) {
        this.error = error.response?.data?.detail || '加载索引详情失败';
        throw error;
      } finally {
        this.loading.list = false;
      }
    },

    /**
     * 创建新索引
     */
    async createNewIndex(indexData) {
      this.loading.create = true;
      this.error = null;
      
      try {
        const newIndex = await createIndex(indexData);
        this.indexes.push(newIndex);
        return newIndex;
      } catch (error) {
        this.error = error.response?.data?.detail || '创建索引失败';
        throw error;
      } finally {
        this.loading.create = false;
      }
    },

    /**
     * 删除索引
     */
    async clearAllHistory() {
      this.loading.delete = true;
      this.error = null;
      
      try {
        const result = await clearAllIndexHistory();
        this.indexes = [];
        this.indexHistory = [];
        this.currentIndex = null;
        this.statistics = null;
        return result;
      } catch (error) {
        this.error = error.response?.data?.detail || '清空历史记录失败';
        throw error;
      } finally {
        this.loading.delete = false;
      }
    },

    async removeIndex(indexId) {
      this.loading.delete = true;
      this.error = null;
      
      try {
        await deleteIndex(indexId);
        this.indexes = this.indexes.filter(idx => idx.id !== indexId);
        this.indexHistory = this.indexHistory.filter(idx => idx.id !== indexId);
        
        if (this.currentIndex?.id === indexId) {
          this.currentIndex = null;
          this.statistics = null;
        }
      } catch (error) {
        this.error = error.response?.data?.detail || '删除索引失败';
        throw error;
      } finally {
        this.loading.delete = false;
      }
    },

    /**
     * 添加向量到索引
     */
    async insertVectors(indexId, vectorsData) {
      this.loading.addVectors = true;
      this.error = null;
      
      try {
        const result = await addVectors(indexId, vectorsData);
        
        // 更新索引状态
        await this.fetchIndex(indexId);
        
        return result;
      } catch (error) {
        this.error = error.response?.data?.detail || '添加向量失败';
        throw error;
      } finally {
        this.loading.addVectors = false;
      }
    },

    /**
     * 向量相似度搜索
     */
    async performSearch(indexId, searchData) {
      this.loading.search = true;
      this.error = null;
      
      try {
        this.searchResults = await searchVectors(indexId, searchData);
        return this.searchResults;
      } catch (error) {
        this.error = error.response?.data?.detail || '搜索失败';
        throw error;
      } finally {
        this.loading.search = false;
      }
    },

    /**
     * 获取索引统计信息
     */
    async fetchStatistics(indexId) {
      this.loading.statistics = true;
      this.error = null;
      
      try {
        this.statistics = await getIndexStatistics(indexId);
        return this.statistics;
      } catch (error) {
        this.error = error.response?.data?.detail || '加载统计信息失败';
        throw error;
      } finally {
        this.loading.statistics = false;
      }
    },

    /**
     * 获取查询历史
     */
    async fetchQueryHistory(indexId, limit = 100) {
      this.loading.history = true;
      this.error = null;
      
      try {
        this.queryHistory = await getQueryHistory(indexId, limit);
        return this.queryHistory;
      } catch (error) {
        this.error = error.response?.data?.detail || '加载查询历史失败';
        throw error;
      } finally {
        this.loading.history = false;
      }
    },

    /**
     * 清除错误
     */
    clearError() {
      this.error = null;
    },

    /**
     * 清除搜索结果
     */
    clearSearchResults() {
      this.searchResults = null;
    },

    /**
     * 选择当前索引
     */
    setCurrentIndex(index) {
      this.currentIndex = index;
    },

    // ==================== 持久化 Actions ====================

    /**
     * 持久化索引到磁盘
     */
    async persistIndex(indexId) {
      this.loading.create = true;
      this.error = null;
      
      try {
        const result = await persistIndex(indexId);
        return result;
      } catch (error) {
        this.error = error.response?.data?.detail || '持久化索引失败';
        throw error;
      } finally {
        this.loading.create = false;
      }
    },

    /**
     * 从磁盘恢复索引
     */
    async recoverIndex(indexId) {
      this.loading.create = true;
      this.error = null;
      
      try {
        const result = await recoverIndex(indexId);
        // 刷新索引列表
        await this.fetchIndexes();
        return result;
      } catch (error) {
        this.error = error.response?.data?.detail || '恢复索引失败';
        throw error;
      } finally {
        this.loading.create = false;
      }
    },

    // ==================== 向量 CRUD Actions ====================

    /**
     * 删除向量
     */
    async removeVectors(indexId, vectorIds) {
      this.loading.delete = true;
      this.error = null;
      
      try {
        const result = await deleteVectors(indexId, vectorIds);
        // 刷新索引详情
        await this.fetchIndex(indexId);
        return result;
      } catch (error) {
        this.error = error.response?.data?.detail || '删除向量失败';
        throw error;
      } finally {
        this.loading.delete = false;
      }
    },

    /**
     * 更新向量
     */
    async modifyVector(indexId, vectorId, vector, metadata) {
      this.loading.addVectors = true;
      this.error = null;
      
      try {
        const result = await updateVector(indexId, {
          vector_id: vectorId,
          vector,
          metadata
        });
        return result;
      } catch (error) {
        this.error = error.response?.data?.detail || '更新向量失败';
        throw error;
      } finally {
        this.loading.addVectors = false;
      }
    },

    // ==================== 混合检索 Actions ====================

    /**
     * 执行混合检索
     * @param {Object} searchData - 混合检索参数
     */
    async performHybridSearch(searchData) {
      this.loading.hybridSearch = true;
      this.error = null;
      
      try {
        this.hybridSearchResults = await hybridSearch(searchData);
        return this.hybridSearchResults;
      } catch (error) {
        this.error = error.response?.data?.detail || '混合检索失败';
        throw error;
      } finally {
        this.loading.hybridSearch = false;
      }
    },

    /**
     * 检查 Reranker 健康状态
     */
    async checkRerankerHealth() {
      try {
        this.rerankerHealth = await rerankerHealthCheck();
        return this.rerankerHealth;
      } catch (error) {
        this.rerankerHealth = { available: false, error: error.message };
        return this.rerankerHealth;
      }
    },

    /**
     * 切换检索模式
     * @param {'dense'|'hybrid'} mode
     */
    setSearchMode(mode) {
      this.searchMode = mode;
    },

    /**
     * 设置混合检索参数
     * @param {Object} params
     */
    setHybridSearchParams(params) {
      this.hybridSearchParams = { ...this.hybridSearchParams, ...params };
    },

    /**
     * 清除混合检索结果
     */
    clearHybridSearchResults() {
      this.hybridSearchResults = null;
    },

    // ==================== 智能推荐 Actions ====================

    /**
     * 获取智能推荐
     */
    async fetchRecommendation() {
      if (!this.selectedTaskId) return;
      
      this.loading.recommend = true;
      this.recommendLoading = true;
      
      try {
        const result = await getRecommendation({
          embedding_task_id: this.selectedTaskId,
          vector_count: this.selectedTask?.successful_count,
          dimension: this.selectedTask?.vector_dimension,
          embedding_model: this.selectedTask?.model
        });
        
        this.recommendation = result.data;
        
        // 自动填充推荐值
        if (this.recommendation) {
          this.selectedAlgorithm = this.recommendation.recommended_index_type || 'FLAT';
          this.metricType = this.recommendation.recommended_metric_type || 'cosine';
          
          // 设置默认参数
          this.setAlgorithm(this.selectedAlgorithm);
        }
        
        return result;
      } catch (error) {
        console.error('获取推荐失败:', error);
        // 推荐失败不阻塞用户操作
        this.recommendation = null;
      } finally {
        this.loading.recommend = false;
        this.recommendLoading = false;
      }
    },

    /**
     * 记录推荐采纳行为
     */
    async logRecommendation() {
      if (!this.recommendation || !this.selectedTaskId) return;
      
      try {
        await logRecommendation({
          embedding_task_id: this.selectedTaskId,
          recommended_index_type: this.recommendation.recommended_index_type,
          recommended_metric_type: this.recommendation.recommended_metric_type,
          final_index_type: this.selectedAlgorithm,
          final_metric_type: this.metricType,
          is_fallback: this.recommendation.is_fallback || false,
          reason: this.recommendation.reason || ''
        });
      } catch (error) {
        console.error('记录推荐行为失败:', error);
      }
    },

    /**
     * 获取推荐统计
     */
    async fetchRecommendStats(days = 30) {
      try {
        const result = await getRecommendStats(days);
        this.recommendStats = result.data;
        return this.recommendStats;
      } catch (error) {
        console.error('获取推荐统计失败:', error);
        return null;
      }
    }
  }
});
