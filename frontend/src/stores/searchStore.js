/**
 * 搜索查询 Pinia Store
 * 
 * 管理搜索状态、配置、结果和历史记录
 * 支持混合检索（hybrid）和纯稠密检索（dense_only）
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  executeSearch as apiExecuteSearch,
  executeHybridSearch as apiExecuteHybridSearch,
  getAvailableIndexes as apiGetAvailableIndexes,
  getAvailableCollections as apiGetAvailableCollections,
  getRerankerHealth as apiGetRerankerHealth,
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
  
  // 🆕 混合检索结果元数据
  const searchMode = ref('auto')        // 实际使用的检索模式
  const rerankerAvailable = ref(false)   // Reranker 是否可用
  const rrfK = ref(null)                 // RRF k 值
  const searchTiming = ref(null)         // 各阶段耗时明细
  
  // 搜索配置
  const config = ref({
    selectedIndexIds: [],
    selectedCollectionIds: [],  // 🆕 Collection 选择
    topK: 10,
    threshold: 0.5,
    metricType: 'cosine',
    rerankerTopN: 20,          // 🆕 Reranker 候选集大小
    rerankerTopK: null,        // 🆕 Reranker 最终返回数（null 时使用 topK）
  })
  
  // 可用索引
  const availableIndexes = ref([])
  const isLoadingIndexes = ref(false)
  
  // 🆕 可用 Collection（含 has_sparse 标识）
  const availableCollections = ref([])
  const isLoadingCollections = ref(false)
  
  // 🆕 Reranker 健康状态
  const rerankerHealth = ref(null)
  
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
  
  // 🆕 是否混合检索模式
  const isHybridMode = computed(() => searchMode.value === 'hybrid')
  
  // 🆕 当前检索模式标签
  const searchModeLabel = computed(() => {
    const modeMap = {
      hybrid: '混合检索',
      dense_only: '纯稠密检索',
      auto: '自动检测'
    }
    return modeMap[searchMode.value] || searchMode.value
  })
  
  // ==================== 搜索操作 (US1 + US2) ====================
  
  /**
   * 执行搜索（自动选择纯稠密或混合检索）
   */
  async function search() {
    if (!queryText.value.trim()) {
      searchError.value = '请输入查询内容'
      return
    }
    
    isSearching.value = true
    searchError.value = null
    
    try {
      // 使用混合检索端点（支持自动降级）
      const params = {
        query_text: queryText.value.trim(),
        top_k: config.value.topK,
        threshold: config.value.threshold,
        metric_type: config.value.metricType,
        search_mode: 'auto',
        reranker_top_n: config.value.rerankerTopN,
      }
      
      if (config.value.rerankerTopK) {
        params.reranker_top_k = config.value.rerankerTopK
      }
      
      // 优先使用 Collection IDs
      if (config.value.selectedCollectionIds.length > 0) {
        params.collection_ids = config.value.selectedCollectionIds
      } else if (config.value.selectedIndexIds.length > 0) {
        params.collection_ids = config.value.selectedIndexIds
      }
      
      const response = await apiExecuteHybridSearch(params)
      
      if (response.success && response.data) {
        results.value = response.data.results || []
        totalCount.value = response.data.total_count || 0
        executionTimeMs.value = response.data.execution_time_ms || 0
        queryId.value = response.data.query_id
        
        // 🆕 混合检索元数据
        searchMode.value = response.data.search_mode || 'dense_only'
        rerankerAvailable.value = response.data.reranker_available || false
        rrfK.value = response.data.rrf_k || null
        searchTiming.value = response.data.timing || null
      } else {
        throw new Error(response.error?.message || '搜索失败')
      }
    } catch (error) {
      searchError.value = error.response?.data?.detail?.error?.message || error.message || '搜索请求失败'
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
    searchMode.value = 'auto'
    rerankerAvailable.value = false
    rrfK.value = null
    searchTiming.value = null
  }
  
  // ==================== 配置操作 ====================
  
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
   * 🆕 加载可用 Collection 列表（含 has_sparse 标识）
   */
  async function loadAvailableCollections() {
    isLoadingCollections.value = true
    
    try {
      const response = await apiGetAvailableCollections()
      
      if (response.success) {
        availableCollections.value = response.data || []
      }
    } catch (error) {
      console.error('Failed to load collections:', error)
    } finally {
      isLoadingCollections.value = false
    }
  }
  
  /**
   * 🆕 加载 Reranker 健康状态
   */
  async function loadRerankerHealth() {
    try {
      const response = await apiGetRerankerHealth()
      if (response.success) {
        rerankerHealth.value = response.data || null
      }
    } catch (error) {
      console.error('Failed to load reranker health:', error)
      rerankerHealth.value = { available: false }
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
      selectedCollectionIds: [],
      topK: 10,
      threshold: 0.5,
      metricType: 'cosine',
      rerankerTopN: 20,
      rerankerTopK: null,
    }
    searchMode.value = 'auto'
  }
  
  // ==================== 历史记录操作 ====================
  
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
    // 历史记录中的 index_ids 是数据库主键（数字ID），不是 collection_name，
    // 不能直接赋值给 selectedCollectionIds（期望的是 collection_name 字符串）。
    // 尝试根据 index_ids 反查匹配的 collection name，如果匹配不上则清空选择（搜索所有）。
    const matchedCollectionIds = []
    if (historyItem.index_ids && historyItem.index_ids.length > 0 && availableCollections.value.length > 0) {
      // 构建 collection name → id 映射
      const validIds = new Set(availableCollections.value.map(c => c.id))
      for (const id of historyItem.index_ids) {
        const strId = String(id)
        if (validIds.has(strId)) {
          matchedCollectionIds.push(strId)
        }
      }
    }
    config.value = {
      ...config.value,
      selectedIndexIds: matchedCollectionIds,
      selectedCollectionIds: matchedCollectionIds,
      topK: historyItem.config?.top_k || 10,
      threshold: historyItem.config?.threshold || 0.5,
      metricType: historyItem.config?.metric_type || 'cosine',
      rerankerTopN: historyItem.config?.reranker_top_n || 20,
      rerankerTopK: null,
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
    availableCollections,
    isLoadingCollections,
    rerankerHealth,
    history,
    historyTotal,
    isLoadingHistory,
    
    // 🆕 混合检索元数据
    searchMode,
    rerankerAvailable,
    rrfK,
    searchTiming,
    
    // 计算属性
    hasResults,
    hasHistory,
    selectedIndexNames,
    isHybridMode,
    searchModeLabel,
    
    // 方法
    search,
    clearResults,
    loadAvailableIndexes,
    loadAvailableCollections,
    loadRerankerHealth,
    updateConfig,
    resetConfig,
    loadHistory,
    deleteHistory,
    clearHistory,
    searchFromHistory
  }
})
