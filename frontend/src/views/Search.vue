<template>
  <div class="flex flex-1">
    <ControlPanel title="搜索配置">
      <template #icon><SearchCheck :size="20" class="text-emerald-500" /></template>
      <SearchConfig
        :config="searchStore.config"
        :available-indexes="searchStore.availableIndexes"
        :available-collections="searchStore.availableCollections"
        :is-loading-indexes="searchStore.isLoadingIndexes"
        :is-loading-collections="searchStore.isLoadingCollections"
        :search-mode="searchStore.searchMode"
        :reranker-health="searchStore.rerankerHealth"
        @update:config="searchStore.updateConfig"
        @reset="searchStore.resetConfig"
      />
    </ControlPanel>
    
    <ContentArea title="搜索查询">
      <template #icon><SearchCheck :size="24" class="text-emerald-500" /></template>
      <!-- 搜索输入框 -->
      <SearchInput
        v-model="searchStore.queryText"
        :is-searching="searchStore.isSearching"
        :error="searchStore.searchError"
        @search="handleSearch"
        @clear="handleClear"
      />
      
      <!-- Tab 切换 -->
      <t-tabs v-model="activeTab" class="search-tabs">
        <t-tab-panel value="results" label="搜索结果">
          <!-- 加载状态 -->
          <div v-if="searchStore.isSearching" class="loading-state">
            <t-loading text="正在搜索..." />
          </div>
          
          <!-- 搜索结果 -->
          <SearchResults
            v-else
            :results="searchStore.results"
            :total-count="searchStore.totalCount"
            :execution-time="searchStore.executionTimeMs"
            :is-loading="searchStore.isSearching"
            :search-mode="searchStore.searchMode"
            :reranker-available="searchStore.rerankerAvailable"
            :timing="searchStore.searchTiming"
          />
        </t-tab-panel>
        
        <t-tab-panel value="history" label="搜索历史">
          <SearchHistory
            :history="searchStore.history"
            :total="searchStore.historyTotal"
            :is-loading="searchStore.isLoadingHistory"
            @select="handleHistorySelect"
            @delete="handleHistoryDelete"
            @clear="handleHistoryClear"
            @load-more="handleHistoryLoadMore"
          />
        </t-tab-panel>
      </t-tabs>
    </ContentArea>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { SearchCheck } from 'lucide-vue-next'
import ControlPanel from '../components/layout/ControlPanel.vue'
import ContentArea from '../components/layout/ContentArea.vue'
import SearchInput from '../components/Search/SearchInput.vue'
import SearchConfig from '../components/Search/SearchConfig.vue'
import SearchResults from '../components/Search/SearchResults.vue'
import SearchHistory from '../components/Search/SearchHistory.vue'
import { useSearchStore } from '../stores/searchStore'

const searchStore = useSearchStore()
const activeTab = ref('results')

// 搜索防抖（300ms）
let searchDebounceTimer = null
const SEARCH_DEBOUNCE_MS = 300
const SEARCH_TIMEOUT_MS = 30000  // 30 秒超时

// 页面加载时获取可用索引、Collection 列表、Reranker 健康状态和历史记录
onMounted(async () => {
  await Promise.all([
    searchStore.loadAvailableIndexes(),
    searchStore.loadAvailableCollections(),
    searchStore.loadRerankerHealth(),
    searchStore.loadHistory()
  ])
})

onUnmounted(() => {
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
  }
})

// 执行搜索（含防抖 + 超时保护）
async function handleSearch() {
  // 清除上次防抖定时器
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
  }
  
  searchDebounceTimer = setTimeout(async () => {
    // 超时保护：Promise.race
    const searchPromise = searchStore.search()
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error('搜索超时，请稍后重试')), SEARCH_TIMEOUT_MS)
    })
    
    try {
      await Promise.race([searchPromise, timeoutPromise])
    } catch (error) {
      if (error.message === '搜索超时，请稍后重试') {
        searchStore.searchError = error.message
        searchStore.isSearching = false
      }
    }
    
    activeTab.value = 'results'
  }, SEARCH_DEBOUNCE_MS)
}

// 清空搜索
function handleClear() {
  searchStore.clearResults()
}

// 从历史记录搜索
function handleHistorySelect(item) {
  searchStore.searchFromHistory(item)
  activeTab.value = 'results'
}

// 删除历史记录
function handleHistoryDelete(id) {
  searchStore.deleteHistory(id)
}

// 清空历史记录
function handleHistoryClear() {
  searchStore.clearHistory()
}

// 加载更多历史
function handleHistoryLoadMore() {
  const currentCount = searchStore.history.length
  searchStore.loadHistory({ limit: 20, offset: currentCount })
}
</script>

<style scoped>
.search-tabs {
  margin-top: 1rem;
}

.loading-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}
</style>
