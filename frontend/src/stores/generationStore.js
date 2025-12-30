/**
 * Generation Pinia Store
 * 文本生成功能的状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as generationApi from '../services/generationApi'
import { getAvailableIndexes, executeSearch } from '../services/searchApi'

export const useGenerationStore = defineStore('generation', () => {
  // ============== State ==============
  
  // 生成状态
  const isGenerating = ref(false)
  const currentRequestId = ref(null)
  const generatedContent = ref('')
  const generationError = ref(null)
  const tokenUsage = ref(null)
  const processingTime = ref(null)
  
  // 流式控制
  const streamController = ref(null)
  
  // 模型配置
  const availableModels = ref([])
  const selectedModel = ref('deepseek-v3')
  const temperature = ref(0.7)
  const maxTokens = ref(4096)
  
  // 索引配置（新增）
  const availableIndexes = ref([])
  const isLoadingIndexes = ref(false)
  const selectedIndexIds = ref([])
  const topK = ref(5)
  
  // 检索状态（新增）
  const isRetrieving = ref(false)
  const retrievedContext = ref([])
  
  // 上下文
  const context = ref([])
  const sources = ref([])
  
  // 历史记录
  const historyList = ref([])
  const historyTotal = ref(0)
  const historyPage = ref(1)
  const historyPageSize = ref(20)
  const historyLoading = ref(false)
  
  // ============== Getters ==============
  
  const hasContext = computed(() => context.value.length > 0)
  
  const canGenerate = computed(() => !isGenerating.value && !isRetrieving.value)
  
  const historyTotalPages = computed(() => 
    Math.ceil(historyTotal.value / historyPageSize.value)
  )
  
  const currentModelInfo = computed(() => 
    availableModels.value.find(m => m.name === selectedModel.value)
  )
  
  const hasSelectedIndexes = computed(() => selectedIndexIds.value.length > 0)
  
  // ============== Actions ==============
  
  /**
   * 加载可用模型列表
   */
  async function loadModels() {
    try {
      const response = await generationApi.getModels()
      availableModels.value = response.models || []
      
      // 设置默认模型
      if (availableModels.value.length > 0 && !selectedModel.value) {
        selectedModel.value = availableModels.value[0].name
      }
    } catch (error) {
      console.error('Failed to load models:', error)
    }
  }
  
  /**
   * 加载可用索引列表
   */
  async function loadAvailableIndexes() {
    isLoadingIndexes.value = true
    try {
      const response = await getAvailableIndexes()
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
   * 执行检索，获取相关文档
   * @param {string} query - 查询文本
   * @returns {Promise<Array>} 检索结果
   */
  async function retrieveContext(query) {
    if (selectedIndexIds.value.length === 0) {
      context.value = []
      sources.value = []
      return []
    }
    
    isRetrieving.value = true
    
    try {
      const params = {
        query_text: query,
        index_ids: selectedIndexIds.value,
        top_k: topK.value,
        threshold: 0.3,
        metric_type: 'cosine'
      }
      
      const response = await executeSearch(params)
      
      if (response.success && response.data?.results) {
        // 转换为 context 格式
        const contextItems = response.data.results.map((result, index) => ({
          content: result.text_content || result.content || result.text || '',
          source_file: result.source_document || result.document_name || result.metadata?.source || `来源 ${index + 1}`,
          similarity: result.similarity_score || result.score || result.similarity || 0,
          chunk_id: result.chunk_id || null,
          metadata: result.metadata
        }))
        
        context.value = contextItems
        sources.value = contextItems.map((item, index) => ({
          index: index + 1,
          source_file: item.source_file,
          similarity: item.similarity,
          content: item.content
        }))
        
        return contextItems
      }
      
      return []
    } catch (error) {
      console.error('Failed to retrieve context:', error)
      return []
    } finally {
      isRetrieving.value = false
    }
  }
  
  /**
   * 设置检索上下文
   * @param {Array} contextItems - 上下文项列表
   */
  function setContext(contextItems) {
    context.value = contextItems || []
    // 提取来源信息
    sources.value = contextItems.map((item, index) => ({
      index: index + 1,
      source_file: item.source_file,
      similarity: item.similarity,
      content: item.content
    }))
  }
  
  /**
   * 清除上下文
   */
  function clearContext() {
    context.value = []
    sources.value = []
  }
  
  /**
   * 流式生成文本（带自动检索）
   * @param {string} question - 用户问题
   */
  async function generateStream(question) {
    if (isGenerating.value || isRetrieving.value) return
    
    isGenerating.value = true
    generatedContent.value = ''
    generationError.value = null
    tokenUsage.value = null
    processingTime.value = null
    currentRequestId.value = null
    
    // 如果选择了索引，先执行检索
    if (selectedIndexIds.value.length > 0) {
      await retrieveContext(question)
    } else {
      context.value = []
      sources.value = []
    }
    
    const request = {
      question,
      model: selectedModel.value,
      temperature: temperature.value,
      max_tokens: maxTokens.value,
      context: context.value
    }
    
    streamController.value = generationApi.generateTextStream(
      request,
      // onChunk
      (chunk) => {
        if (chunk.request_id && !currentRequestId.value) {
          currentRequestId.value = chunk.request_id
        }
        if (chunk.content) {
          generatedContent.value += chunk.content
        }
        if (chunk.done && chunk.token_usage) {
          tokenUsage.value = chunk.token_usage
        }
        if (chunk.done && chunk.processing_time_ms) {
          processingTime.value = chunk.processing_time_ms
        }
      },
      // onError
      (error) => {
        generationError.value = error.message
        isGenerating.value = false
        streamController.value = null
      },
      // onComplete
      () => {
        isGenerating.value = false
        streamController.value = null
      }
    )
  }
  
  /**
   * 非流式生成文本（带自动检索）
   * @param {string} question - 用户问题
   */
  async function generate(question) {
    if (isGenerating.value || isRetrieving.value) return
    
    isGenerating.value = true
    generatedContent.value = ''
    generationError.value = null
    tokenUsage.value = null
    processingTime.value = null
    
    try {
      // 如果选择了索引，先执行检索
      if (selectedIndexIds.value.length > 0) {
        await retrieveContext(question)
      } else {
        context.value = []
        sources.value = []
      }
      
      const request = {
        question,
        model: selectedModel.value,
        temperature: temperature.value,
        max_tokens: maxTokens.value,
        context: context.value
      }
      
      const response = await generationApi.generateText(request)
      
      currentRequestId.value = response.request_id
      generatedContent.value = response.answer
      tokenUsage.value = response.token_usage
      processingTime.value = response.processing_time_ms
      // 如果响应包含 sources，合并更新
      if (response.sources && response.sources.length > 0) {
        sources.value = response.sources
      }
    } catch (error) {
      generationError.value = error.message
    } finally {
      isGenerating.value = false
    }
  }
  
  /**
   * 取消当前生成
   */
  async function cancelGeneration() {
    if (streamController.value) {
      streamController.value.abort()
      streamController.value = null
    }
    
    if (currentRequestId.value) {
      try {
        await generationApi.cancelGeneration(currentRequestId.value)
      } catch (error) {
        console.error('Failed to cancel generation:', error)
      }
    }
    
    isGenerating.value = false
  }
  
  /**
   * 重置生成状态
   */
  function resetGeneration() {
    isGenerating.value = false
    currentRequestId.value = null
    generatedContent.value = ''
    generationError.value = null
    tokenUsage.value = null
    processingTime.value = null
    streamController.value = null
  }
  
  /**
   * 更新模型配置
   * @param {Object} config - 配置对象
   */
  function updateConfig(config) {
    if (config.model !== undefined) selectedModel.value = config.model
    if (config.temperature !== undefined) temperature.value = config.temperature
    if (config.maxTokens !== undefined) maxTokens.value = config.maxTokens
  }
  
  /**
   * 加载历史记录列表
   * @param {Object} params - 查询参数
   */
  async function loadHistory(params = {}) {
    historyLoading.value = true
    
    try {
      const response = await generationApi.getHistoryList({
        page: params.page || historyPage.value,
        page_size: params.page_size || historyPageSize.value,
        status: params.status
      })
      
      historyList.value = response.items || []
      historyTotal.value = response.total || 0
      historyPage.value = response.page || 1
      historyPageSize.value = response.page_size || 20
    } catch (error) {
      console.error('Failed to load history:', error)
    } finally {
      historyLoading.value = false
    }
  }
  
  /**
   * 删除历史记录
   * @param {number} id - 记录ID
   */
  async function deleteHistoryItem(id) {
    try {
      await generationApi.deleteHistory(id)
      // 重新加载列表
      await loadHistory()
    } catch (error) {
      console.error('Failed to delete history:', error)
      throw error
    }
  }
  
  /**
   * 清空所有历史
   */
  async function clearAllHistory() {
    try {
      await generationApi.clearHistory()
      historyList.value = []
      historyTotal.value = 0
    } catch (error) {
      console.error('Failed to clear history:', error)
      throw error
    }
  }
  
  return {
    // State
    isGenerating,
    isRetrieving,
    currentRequestId,
    generatedContent,
    generationError,
    tokenUsage,
    processingTime,
    availableModels,
    selectedModel,
    temperature,
    maxTokens,
    context,
    sources,
    historyList,
    historyTotal,
    historyPage,
    historyPageSize,
    historyLoading,
    // 新增：索引相关
    availableIndexes,
    isLoadingIndexes,
    selectedIndexIds,
    topK,
    
    // Getters
    hasContext,
    canGenerate,
    historyTotalPages,
    currentModelInfo,
    hasSelectedIndexes,
    
    // Actions
    loadModels,
    loadAvailableIndexes,
    retrieveContext,
    setContext,
    clearContext,
    generateStream,
    generate,
    cancelGeneration,
    resetGeneration,
    updateConfig,
    loadHistory,
    deleteHistoryItem,
    clearAllHistory
  }
})
