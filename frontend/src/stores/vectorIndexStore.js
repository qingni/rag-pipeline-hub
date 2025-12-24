/**
 * 向量索引 Pinia Store
 * 
 * 管理向量索引的全局状态
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
  getQueryHistory
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
    // 加载状态
    loading: {
      list: false,
      create: false,
      delete: false,
      addVectors: false,
      search: false,
      statistics: false,
      history: false
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
      Object.values(state.loading).some(val => val)
  },

  actions: {
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
    async removeIndex(indexId) {
      this.loading.delete = true;
      this.error = null;
      
      try {
        await deleteIndex(indexId);
        this.indexes = this.indexes.filter(idx => idx.id !== indexId);
        
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
    }
  }
});
