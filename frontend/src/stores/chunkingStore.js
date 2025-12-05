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

    // Strategy selection
    strategies: [],
    selectedStrategy: null,
    strategyParameters: {},
    strategiesLoading: false,

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

    // History
    historyList: [],
    historyPage: 1,
    historyPageSize: 20,
    historyTotalCount: 0,
    historyFilters: {},
    historyLoading: false,

    // Queue status
    queueStatus: null,

    // UI state
    activeTab: 'chunking', // 'chunking' or 'history'
    selectedChunk: null,
    compareMode: false,
    selectedResults: []
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
    }
  },

  actions: {
    /**
     * Load parsed documents
     */
    async loadParsedDocuments(page = 1, pageSize = 20) {
      this.documentsLoading = true
      try {
        const response = await chunkingService.getParsedDocuments(page, pageSize)
        console.log('API Response:', response)
        if (response.success && response.data) {
          // Check if data has items (paginated response)
          if (response.data.items) {
            this.parsedDocuments = response.data.items
          } else if (Array.isArray(response.data)) {
            // Direct array response
            this.parsedDocuments = response.data
          } else {
            console.error('Unexpected data structure:', response.data)
            this.parsedDocuments = []
          }
          console.log('Parsed documents set to:', this.parsedDocuments.length, this.parsedDocuments)
        } else {
          console.error('API returned success=false or no data:', response)
          this.parsedDocuments = []
        }
      } catch (error) {
        console.error('Failed to load parsed documents:', error)
        this.parsedDocuments = []
        throw error
      } finally {
        this.documentsLoading = false
      }
    },

    /**
     * Select document for chunking
     */
    selectDocument(document) {
      this.selectedDocument = document
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
      this.selectedStrategy = strategy
      // Initialize parameters with defaults
      this.strategyParameters = { ...strategy.default_parameters }
    },

    /**
     * Update strategy parameters
     */
    updateParameters(params) {
      this.strategyParameters = { ...this.strategyParameters, ...params }
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
    }
  }
})
