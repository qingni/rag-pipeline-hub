/**
 * 搜索查询 Pinia Store
 * 
 * 管理搜索状态、配置、结果和历史记录
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  executeSearch as apiExecuteSearch,
  getAvailableIndexes as apiGetAvailableIndexes,
  getSearchHistory as apiGetSearchHistory,
  deleteSearchHistory as apiDeleteSearchHistory,
  clearSearchHistory as apiClearSearchHistory
} from '../services/searchApi'

export const useSearchStore = defineStore('search', () => {
  // ==================== 状态 ====================
  
  // 搜索状态
  const queryText = ref('')
  const isSearching = ref(false)
  const searchError = ref(null)
  
  // 搜索结果
  const results = ref([])
  const totalCount = ref(0)
  const executionTimeMs = ref(0)
  const queryId = ref(null)
  
  // 搜索配置
  const config = ref({
    selectedIndexIds: [],
    topK: 10,
    threshold: 0.5,
    metricType: 'cosine'
  })
  
  // 可用索引
  const availableIndexes = ref([])
  const isLoadingIndexes = ref(false)
  
  // 搜索历史
  const history = ref([])
  const historyTotal = ref(0)
  const isLoadingHistory = ref(false)
  
  // ==================== 计算属性 ====================
  
  const hasResults = computed(() => results.value.length > 0)
  const hasHistory = computed(() => history.value.length > 0)
  const selectedIndexNames = computed(() => {
    if (config.value.selectedIndexIds.length === 0) return '默认索引'
    return availableIndexes.value
      .filter(idx => config.value.selectedIndexIds.includes(idx.id))
      .map(idx => idx.name)
      .join(', ')
  })
  
  // ==================== 搜索操作 (US1) ====================
  
  /**
   * 执行搜索
   */
  async function search() {
    if (!queryText.value.trim()) {
      searchError.value = '请输入查询内容'
      return
    }
    
    isSearching.value = true
    searchError.value = null
    
    try {
      const params = {
        query_text: queryText.value.trim(),
        top_k: config.value.topK,
        threshold: config.value.threshold,
        metric_type: config.value.metricType
      }
      
      if (config.value.selectedIndexIds.length > 0) {
        params.index_ids = config.value.selectedIndexIds
      }
      
      const response = await apiExecuteSearch(params)
      
      if (response.success && response.data) {
        results.value = response.data.results || []
        totalCount.value = response.data.total_count || 0
        executionTimeMs.value = response.data.execution_time_ms || 0
        queryId.value = response.data.query_id
      } else {
        throw new Error(response.error?.message || '搜索失败')
      }
    } catch (error) {
      searchError.value = error.message || '搜索请求失败'
      results.value = []
      totalCount.value = 0
    } finally {
      isSearching.value = false
    }
  }
  
  /**
   * 清空搜索结果
   */
  function clearResults() {
    results.value = []
    totalCount.value = 0
    executionTimeMs.value = 0
    queryId.value = null
    searchError.value = null
  }
  
  // ==================== 配置操作 (US3) ====================
  
  /**
   * 加载可用索引列表
   */
  async function loadAvailableIndexes() {
    isLoadingIndexes.value = true
    
    try {
      const response = await apiGetAvailableIndexes()
      
      if (response.success) {
        availableIndexes.value = response.data || []
      }
    } catch (error) {
      console.error('Failed to load indexes:', error)
    } finally {
      isLoadingIndexes.value = false
    }
  }
  
  /**
   * 更新搜索配置
   * @param {Object} newConfig - 新配置
   */
  function updateConfig(newConfig) {
    config.value = { ...config.value, ...newConfig }
  }
  
  /**
   * 重置配置为默认值
   */
  function resetConfig() {
    config.value = {
      selectedIndexIds: [],
      topK: 10,
      threshold: 0.5,
      metricType: 'cosine'
    }
  }
  
  // ==================== 历史记录操作 (US4) ====================
  
  /**
   * 加载搜索历史
   * @param {Object} params - 分页参数
   */
  async function loadHistory(params = { limit: 20, offset: 0 }) {
    isLoadingHistory.value = true
    
    try {
      const response = await apiGetSearchHistory(params)
      
      if (response.success && response.data) {
        history.value = response.data.items || []
        historyTotal.value = response.data.total || 0
      }
    } catch (error) {
      console.error('Failed to load history:', error)
    } finally {
      isLoadingHistory.value = false
    }
  }
  
  /**
   * 删除单条历史记录
   * @param {string} historyId - 历史记录ID
   */
  async function deleteHistory(historyId) {
    try {
      const response = await apiDeleteSearchHistory(historyId)
      
      if (response.success) {
        history.value = history.value.filter(h => h.id !== historyId)
        historyTotal.value = Math.max(0, historyTotal.value - 1)
      }
    } catch (error) {
      console.error('Failed to delete history:', error)
    }
  }
  
  /**
   * 清空所有历史记录
   */
  async function clearHistory() {
    try {
      const response = await apiClearSearchHistory()
      
      if (response.success) {
        history.value = []
        historyTotal.value = 0
      }
    } catch (error) {
      console.error('Failed to clear history:', error)
    }
  }
  
  /**
   * 从历史记录执行搜索
   * @param {Object} historyItem - 历史记录项
   */
  function searchFromHistory(historyItem) {
    queryText.value = historyItem.query_text
    config.value = {
      selectedIndexIds: historyItem.index_ids || [],
      topK: historyItem.config?.top_k || 10,
      threshold: historyItem.config?.threshold || 0.5,
      metricType: historyItem.config?.metric_type || 'cosine'
    }
    search()
  }
  
  return {
    // 状态
    queryText,
    isSearching,
    searchError,
    results,
    totalCount,
    executionTimeMs,
    queryId,
    config,
    availableIndexes,
    isLoadingIndexes,
    history,
    historyTotal,
    isLoadingHistory,
    
    // 计算属性
    hasResults,
    hasHistory,
    selectedIndexNames,
    
    // 方法
    search,
    clearResults,
    loadAvailableIndexes,
    updateConfig,
    resetConfig,
    loadHistory,
    deleteHistory,
    clearHistory,
    searchFromHistory
  }
})
