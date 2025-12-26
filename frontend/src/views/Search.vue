<template>
  <div class="flex flex-1">
    <ControlPanel title="搜索配置" description="配置搜索参数">
      <SearchConfig
        :config="searchStore.config"
        :available-indexes="searchStore.availableIndexes"
        :is-loading-indexes="searchStore.isLoadingIndexes"
        @update:config="searchStore.updateConfig"
        @reset="searchStore.resetConfig"
      />
    </ControlPanel>
    
    <ContentArea title="搜索查询">
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
import { ref, onMounted } from 'vue'
import ControlPanel from '../components/layout/ControlPanel.vue'
import ContentArea from '../components/layout/ContentArea.vue'
import SearchInput from '../components/Search/SearchInput.vue'
import SearchConfig from '../components/Search/SearchConfig.vue'
import SearchResults from '../components/Search/SearchResults.vue'
import SearchHistory from '../components/Search/SearchHistory.vue'
import { useSearchStore } from '../stores/searchStore'

const searchStore = useSearchStore()
const activeTab = ref('results')

// 页面加载时获取可用索引和历史记录
onMounted(async () => {
  await Promise.all([
    searchStore.loadAvailableIndexes(),
    searchStore.loadHistory()
  ])
})

// 执行搜索
async function handleSearch() {
  await searchStore.search()
  activeTab.value = 'results'
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
