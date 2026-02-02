/**
 * Chunking Store - State management for document chunking
 */
import { defineStore } from 'pinia'
import chunkingService from '../services/chunkingService'

export const useChunkingStore = defineStore('chunking', {
  state: () => ({
    // Document selection
    parsedDocuments: [],
    selectedDocument: null,
    documentsLoading: false,
    documentsPage: 1,
    documentsPageSize: 50,
    documentsTotalCount: 0,
    documentsFilters: {
      search: '',
      format: null,
      sortBy: 'upload_time',
      sortOrder: 'desc'
    },

    // Strategy selection
    strategies: [],
    selectedStrategy: null,
    strategyParameters: {},
    strategiesLoading: false,

    // Strategy recommendation (NEW)
    recommendations: [],
    documentFeatures: null,
    recommendationsLoading: false,

    // Chunking task
    currentTask: null,
    taskPollingInterval: null,

    // Chunking results
    currentResult: null,
    chunks: [],
    chunksPage: 1,
    chunksPageSize: 50,
    chunksTotalCount: 0,
    resultLoading: false,

    // Parent chunks for parent-child chunking (NEW)
    parentChunks: [],
    parentChunksLoading: false,
    selectedParentChunk: null,

    // History
    historyList: [],
    historyPage: 1,
    historyPageSize: 20,
    historyTotalCount: 0,
    historyFilters: {},
    historyLoading: false,

    // Preview and comparison (NEW)
    previewResult: null,
    previewLoading: false,
    comparisonResults: [],
    comparisonLoading: false,

    // Queue status
    queueStatus: null,

    // UI state
    activeTab: 'chunking', // 'chunking' or 'history'
    selectedChunk: null,
    compareMode: false,
    selectedResults: [],
    viewMode: 'list', // 'list' or 'tree' (for parent-child)
    
    // Flag to prevent auto-strategy selection when user explicitly applies recommendation
    userExplicitlySelectedStrategy: false
  }),

  getters: {
    /**
     * Check if a document is selected
     */
    hasSelectedDocument: (state) => !!state.selectedDocument,

    /**
     * Check if a strategy is selected
     */
    hasSelectedStrategy: (state) => !!state.selectedStrategy,

    /**
     * Check if chunking is in progress
     */
    isChunking: (state) => {
      return state.currentTask && ['pending', 'processing'].includes(state.currentTask.status)
    },

    /**
     * Get strategy by type
     */
    getStrategyByType: (state) => (type) => {
      return state.strategies.find(s => s.type === type)
    },

    /**
     * Check if recommendations are available (NEW)
     */
    hasRecommendations: (state) => state.recommendations.length > 0,

    /**
     * Get top recommendation (NEW)
     */
    topRecommendation: (state) => {
      return state.recommendations.find(r => r.is_top) || state.recommendations[0]
    },

    /**
     * Check if current result is parent-child type (NEW)
     */
    isParentChildResult: (state) => {
      return state.currentResult?.strategy_type === 'parent_child'
    }
  },

  actions: {
    /**
     * Load parsed documents
     */
    async loadParsedDocuments(page = 1, filters = null) {
      this.documentsLoading = true
      try {
        // Use provided filters or default to stored filters
        const appliedFilters = filters || this.documentsFilters
        
        const response = await chunkingService.getParsedDocuments(
          page, 
          this.documentsPageSize,
          appliedFilters
        )
        console.log('API Response:', response)
        if (response.success && response.data) {
          // Check if data has items (paginated response)
          if (response.data.items) {
            this.parsedDocuments = response.data.items
            this.documentsTotalCount = response.data.total || 0
            this.documentsPage = page
          } else if (Array.isArray(response.data)) {
            // Direct array response
            this.parsedDocuments = response.data
            this.documentsTotalCount = response.data.length
          } else {
            console.error('Unexpected data structure:', response.data)
            this.parsedDocuments = []
            this.documentsTotalCount = 0
          }
          console.log('Parsed documents set to:', this.parsedDocuments.length, this.parsedDocuments)
        } else {
          console.error('API returned success=false or no data:', response)
          this.parsedDocuments = []
          this.documentsTotalCount = 0
        }
      } catch (error) {
        console.error('Failed to load parsed documents:', error)
        this.parsedDocuments = []
        this.documentsTotalCount = 0
        throw error
      } finally {
        this.documentsLoading = false
      }
    },
    
    /**
     * Update document filters
     */
    updateDocumentFilters(filters) {
      this.documentsFilters = { ...this.documentsFilters, ...filters }
    },

    /**
     * Select document for chunking
     */
    selectDocument(document) {
      this.selectedDocument = document
      // Reset strategy selection when changing documents
      this.selectedStrategy = null
      this.strategyParameters = {}
      this.userExplicitlySelectedStrategy = false
      
      // Clear previous task and result immediately to avoid showing stale data
      this.currentTask = null
      this.currentResult = null
      this.chunks = []
      this.chunksTotalCount = 0
      this.selectedChunk = null
      
      // Load latest chunking result for this document (async)
      this.loadLatestResultForDocument(document.id)
    },

    /**
     * Load latest chunking result for selected document
     */
    async loadLatestResultForDocument(documentId, strategyType = null, parameters = null) {
      try {
        const response = await chunkingService.getLatestResultForDocument(
          documentId,
          strategyType,
          parameters
        )
        
        if (response.success && response.data) {
          // Load the full result with chunks
          await this.loadChunkingResult(response.data.result_id)
          
          // 如果是父子分块，加载父块（树状视图需要父块数据，includeChildren=true获取子块）
          if (this.isParentChildResult) {
            await this.loadParentChunks(null, true)
          }
          
          // 不再自动选中历史策略，让用户根据智能推荐或手动选择策略
          // 只有当用户明确指定了策略类型时才更新选中状态
          if (strategyType) {
            const matchingStrategy = this.strategies.find(s => s.type === strategyType)
            if (matchingStrategy) {
              this.selectedStrategy = matchingStrategy
              this.strategyParameters = { ...response.data.parameters }
            }
          }
        } else {
          // No existing result, clear current result
          this.currentResult = null
          this.chunks = []
          this.selectedChunk = null
        }
      } catch (error) {
        console.error('Failed to load latest result for document:', error)
        // Don't throw - it's okay if there's no existing result
      }
    },

    /**
     * Load chunking strategies
     */
    async loadStrategies() {
      this.strategiesLoading = true
      try {
        const response = await chunkingService.getChunkingStrategies()
        console.log('Strategies API Response:', response)
        if (response.success && response.data) {
          if (response.data.strategies) {
            this.strategies = response.data.strategies
          } else if (Array.isArray(response.data)) {
            this.strategies = response.data
          } else {
            console.error('Unexpected strategies data structure:', response.data)
            this.strategies = []
          }
          console.log('Strategies set to:', this.strategies.length, this.strategies)
        } else {
          console.error('API returned success=false or no data:', response)
          this.strategies = []
        }
      } catch (error) {
        console.error('Failed to load strategies:', error)
        this.strategies = []
        throw error
      } finally {
        this.strategiesLoading = false
      }
    },

    /**
     * Select chunking strategy
     */
    selectStrategy(strategy) {
      const previousStrategy = this.selectedStrategy?.type
      this.selectedStrategy = strategy
      // Initialize parameters with defaults
      this.strategyParameters = { ...strategy.default_parameters }
      
      // If a document is already selected and strategy changed, load latest result for this strategy
      if (this.selectedDocument && previousStrategy !== strategy.type) {
        this.loadLatestResultForDocument(this.selectedDocument.id, strategy.type)
      }
    },

    /**
     * Update strategy parameters
     */
    updateParameters(params) {
      this.strategyParameters = { ...this.strategyParameters, ...params }
      
      // Note: We don't automatically load results on parameter change to avoid excessive API calls
      // Users can manually trigger chunking if they want to see results with new parameters
      // Or we can add a debounced search feature in the future
    },

    /**
     * Create chunking task
     */
    async createChunkingTask() {
      if (!this.selectedDocument || !this.selectedStrategy) {
        throw new Error('Please select document and strategy')
      }

      try {
        const response = await chunkingService.createChunkingTask(
          this.selectedDocument.id,
          this.selectedStrategy.type,
          this.strategyParameters
        )

        if (response.success) {
          this.currentTask = response.data
          // Start polling for task status
          this.startTaskPolling()
          return response.data
        }
      } catch (error) {
        console.error('Failed to create chunking task:', error)
        throw error
      }
    },

    /**
     * Start polling task status
     */
    startTaskPolling() {
      if (this.taskPollingInterval) {
        clearInterval(this.taskPollingInterval)
      }

      this.taskPollingInterval = setInterval(async () => {
        if (this.currentTask && ['pending', 'processing'].includes(this.currentTask.status)) {
          await this.updateTaskStatus()
        } else {
          this.stopTaskPolling()
        }
      }, 2000) // Poll every 2 seconds
    },

    /**
     * Stop polling task status
     */
    stopTaskPolling() {
      if (this.taskPollingInterval) {
        clearInterval(this.taskPollingInterval)
        this.taskPollingInterval = null
      }
    },

    /**
     * Update task status
     */
    async updateTaskStatus() {
      if (!this.currentTask) return

      try {
        const response = await chunkingService.getChunkingTask(this.currentTask.task_id)
        if (response.success) {
          const oldStatus = this.currentTask.status
          this.currentTask = response.data

          // If completed, load result automatically
          if (this.currentTask.status === 'completed' && this.currentTask.result_id) {
            if (oldStatus !== 'completed') {
              // Only load once when status changes to completed
              await this.loadChunkingResult(this.currentTask.result_id)
              // Auto-select first chunk for preview
              if (this.chunks.length > 0) {
                this.selectChunk(this.chunks[0])
              }
              // Refresh history list to show the new result
              if (this.historyList.length > 0) {
                await this.loadHistory(this.historyPage, this.historyFilters)
              }
            }
          }
        }
      } catch (error) {
        console.error('Failed to update task status:', error)
      }
    },

    /**
     * Load chunking result
     */
    async loadChunkingResult(resultId, page = 1) {
      this.resultLoading = true
      try {
        const response = await chunkingService.getChunkingResult(
          resultId,
          true,
          page,
          this.chunksPageSize
        )

        if (response.success) {
          this.currentResult = response.data
          if (response.data.chunks) {
            this.chunks = response.data.chunks.items
            this.chunksTotalCount = response.data.chunks.total
            this.chunksPage = page
          }
        }
      } catch (error) {
        console.error('Failed to load chunking result:', error)
        throw error
      } finally {
        this.resultLoading = false
      }
    },

    /**
     * Select a chunk for detailed view
     */
    selectChunk(chunk) {
      this.selectedChunk = chunk
    },

    /**
     * Load history
     */
    async loadHistory(page = 1, filters = {}) {
      this.historyLoading = true
      try {
        const response = await chunkingService.getChunkingHistory({
          page,
          page_size: this.historyPageSize,
          ...filters
        })

        if (response.success) {
          this.historyList = response.data.items
          this.historyTotalCount = response.data.total
          this.historyPage = page
          this.historyFilters = filters
        }
      } catch (error) {
        console.error('Failed to load history:', error)
        throw error
      } finally {
        this.historyLoading = false
      }
    },

    /**
     * Delete chunking result
     */
    async deleteResult(resultId) {
      try {
        const response = await chunkingService.deleteChunkingResult(resultId)
        if (response.success) {
          // Refresh history list
          await this.loadHistory(this.historyPage, this.historyFilters)
        }
        return response
      } catch (error) {
        console.error('Failed to delete result:', error)
        throw error
      }
    },

    /**
     * Batch delete chunking results
     */
    async batchDeleteResults(resultIds) {
      try {
        const response = await chunkingService.batchDeleteResults(resultIds)
        if (response.success) {
          // Refresh history list
          await this.loadHistory(this.historyPage, this.historyFilters)
        }
        return response
      } catch (error) {
        console.error('Failed to batch delete results:', error)
        throw error
      }
    },

    /**
     * Reset state
     */
    reset() {
      this.stopTaskPolling()
      this.selectedDocument = null
      this.selectedStrategy = null
      this.strategyParameters = {}
      this.currentTask = null
      this.currentResult = null
      this.chunks = []
      this.selectedChunk = null
    },

    /**
     * Switch tab
     */
    switchTab(tab) {
      this.activeTab = tab
    },

    /**
     * Load strategy recommendations for selected document (NEW)
     */
    async loadRecommendations(documentId = null) {
      const docId = documentId || this.selectedDocument?.id
      if (!docId) return

      this.recommendationsLoading = true
      try {
        const response = await chunkingService.getRecommendations(docId)
        if (response.success && response.data) {
          this.recommendations = response.data.recommendations || []
          this.documentFeatures = response.data.features || null
        }
      } catch (error) {
        console.error('Failed to load recommendations:', error)
        this.recommendations = []
        this.documentFeatures = null
      } finally {
        this.recommendationsLoading = false
      }
    },

    /**
     * Analyze document features (NEW)
     */
    async analyzeDocument(documentId = null) {
      const docId = documentId || this.selectedDocument?.id
      if (!docId) return null

      try {
        const response = await chunkingService.analyzeDocument(docId)
        if (response.success && response.data) {
          this.documentFeatures = response.data.features
          return response.data.features
        }
      } catch (error) {
        console.error('Failed to analyze document:', error)
      }
      return null
    },

    /**
     * Apply recommendation as current strategy (NEW)
     */
    applyRecommendation(recommendation) {
      // Find matching strategy
      const strategy = this.strategies.find(s => s.type === recommendation.strategy)
      if (strategy) {
        // Set flag to prevent auto-selection from overriding
        this.userExplicitlySelectedStrategy = true
        this.selectedStrategy = strategy
        // Use suggested params from recommendation
        this.strategyParameters = { ...recommendation.suggested_params }
      }
    },

    /**
     * Load parent chunks for parent-child result (NEW)
     * 注意：为了树状视图能正确显示，需要加载所有父块
     * includeChildren=true 时会同时返回每个父块的子块数据
     */
    async loadParentChunks(resultId = null, includeChildren = true) {
      const rId = resultId || this.currentResult?.result_id
      if (!rId) return

      this.parentChunksLoading = true
      try {
        // 使用较大的 pageSize 加载所有父块，确保树状视图能完整显示
        // 后端 API 限制最大 100，如果父块超过 100 个需要分页加载
        const pageSize = 100
        const response = await chunkingService.getParentChunks(rId, includeChildren, 1, pageSize)
        if (response.success && response.data) {
          this.parentChunks = response.data.items || []
          
          // 如果父块总数超过当前加载的数量，继续加载剩余的父块
          const total = response.data.total || 0
          if (total > pageSize) {
            const totalPages = Math.ceil(total / pageSize)
            for (let page = 2; page <= totalPages; page++) {
              const moreResponse = await chunkingService.getParentChunks(rId, includeChildren, page, pageSize)
              if (moreResponse.success && moreResponse.data?.items) {
                this.parentChunks = [...this.parentChunks, ...moreResponse.data.items]
              }
            }
          }
        }
      } catch (error) {
        console.error('Failed to load parent chunks:', error)
        this.parentChunks = []
      } finally {
        this.parentChunksLoading = false
      }
    },

    /**
     * Load chunks filtered by parent (NEW)
     */
    async loadChunksByParent(parentId, page = 1) {
      const resultId = this.currentResult?.result_id
      if (!resultId || !parentId) return []

      try {
        const response = await chunkingService.getChunksByParent(resultId, parentId, page)
        if (response.success && response.data) {
          return response.data.items || []
        }
      } catch (error) {
        console.error('Failed to load chunks by parent:', error)
      }
      return []
    },

    /**
     * Get single parent chunk with children (NEW)
     */
    async getParentWithChildren(parentId) {
      const resultId = this.currentResult?.result_id
      if (!resultId || !parentId) return null

      try {
        // Load parent chunks with children included
        const response = await chunkingService.getParentChunks(resultId, true)
        if (response.success && response.data?.items) {
          return response.data.items.find(p => p.id === parentId)
        }
      } catch (error) {
        console.error('Failed to get parent with children:', error)
      }
      return null
    },

    /**
     * Select parent chunk for detailed view (NEW)
     */
    selectParentChunk(parentChunk) {
      this.selectedParentChunk = parentChunk
      this.selectedChunk = null  // Clear child selection when viewing parent
    },

    /**
     * Clear parent chunk selection (NEW)
     */
    clearParentSelection() {
      this.selectedParentChunk = null
    },

    /**
     * Preview chunking result (NEW)
     */
    async previewChunking(strategyType = null, params = null) {
      const docId = this.selectedDocument?.id
      if (!docId) return

      const strategy = strategyType || this.selectedStrategy?.type
      const strategyParams = params || this.strategyParameters

      this.previewLoading = true
      try {
        const response = await chunkingService.preview(docId, strategy, strategyParams)
        if (response.success && response.data) {
          this.previewResult = response.data
        }
      } catch (error) {
        console.error('Failed to preview chunking:', error)
        this.previewResult = null
      } finally {
        this.previewLoading = false
      }
    },

    /**
     * Compare multiple strategies (NEW)
     */
    async compareStrategies(strategies) {
      const docId = this.selectedDocument?.id
      if (!docId || !strategies?.length) return

      this.comparisonLoading = true
      try {
        const response = await chunkingService.compare(docId, strategies)
        if (response.success && response.data) {
          this.comparisonResults = response.data.comparisons || []
        }
      } catch (error) {
        console.error('Failed to compare strategies:', error)
        this.comparisonResults = []
      } finally {
        this.comparisonLoading = false
      }
    },

    /**
     * Set view mode (list or tree) (NEW)
     */
    setViewMode(mode) {
      this.viewMode = mode
    },

    /**
     * Clear recommendations (NEW)
     */
    clearRecommendations() {
      this.recommendations = []
      this.documentFeatures = null
    }
  }
})
