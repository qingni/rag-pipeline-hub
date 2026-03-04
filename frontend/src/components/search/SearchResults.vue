<template>
  <div class="search-results">
    <!-- 结果统计 -->
    <div v-if="results.length > 0" class="results-summary">
      <div class="summary-main">
        <span>找到 <strong>{{ totalCount }}</strong> 条相关结果</span>
        <span v-if="executionTime > 0" class="execution-time">
          (耗时 {{ executionTime }}ms)
        </span>
      </div>
      <!-- 🆕 混合检索元数据 -->
      <div v-if="searchMode" class="summary-meta">
        <t-tag 
          :theme="searchMode === 'hybrid' ? 'primary' : 'default'" 
          variant="light" 
          size="small"
        >
          {{ searchMode === 'hybrid' ? '混合检索' : '纯稠密检索' }}
        </t-tag>
        <t-tag 
          v-if="rerankerAvailable !== undefined"
          :theme="rerankerAvailable ? 'success' : 'warning'" 
          variant="light" 
          size="small"
        >
          Reranker: {{ rerankerAvailable ? '已启用' : '未启用' }}
        </t-tag>
        <!-- 🆕 耗时明细 -->
        <span v-if="timing" class="timing-detail">
          <span v-if="timing.embedding_ms" class="timing-item">向量化 {{ timing.embedding_ms }}ms</span>
          <span v-if="timing.bm25_ms" class="timing-item">BM25 {{ timing.bm25_ms }}ms</span>
          <span v-if="timing.search_ms" class="timing-item">检索 {{ timing.search_ms }}ms</span>
          <span v-if="timing.reranker_ms" class="timing-item">精排 {{ timing.reranker_ms }}ms</span>
        </span>
      </div>
    </div>
    
    <!-- 结果列表 -->
    <div class="results-list">
      <ResultCard
        v-for="result in results"
        :key="result.id"
        :result="result"
        @view-detail="handleViewDetail"
      />
    </div>
    
    <!-- 加载更多 -->
    <div v-if="hasMore" class="load-more">
      <t-button
        variant="outline"
        :loading="isLoadingMore"
        @click="handleLoadMore"
      >
        加载更多
      </t-button>
    </div>
    
    <!-- 空状态 -->
    <div v-if="results.length === 0 && !isLoading" class="empty-state">
      <t-empty description="未找到相关内容，请尝试其他关键词" />
    </div>
    
    <!-- 结果详情弹窗 -->
    <ResultDetail
      v-model:visible="detailVisible"
      :result="selectedResult"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ResultCard from './ResultCard.vue'
import ResultDetail from './ResultDetail.vue'

const props = defineProps({
  results: {
    type: Array,
    default: () => []
  },
  totalCount: {
    type: Number,
    default: 0
  },
  executionTime: {
    type: Number,
    default: 0
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  hasMore: {
    type: Boolean,
    default: false
  },
  isLoadingMore: {
    type: Boolean,
    default: false
  },
  // 🆕 混合检索元数据
  searchMode: {
    type: String,
    default: ''
  },
  rerankerAvailable: {
    type: Boolean,
    default: undefined
  },
  timing: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['load-more'])

const detailVisible = ref(false)
const selectedResult = ref(null)

function handleViewDetail(result) {
  selectedResult.value = result
  detailVisible.value = true
}

function handleLoadMore() {
  emit('load-more')
}
</script>

<style scoped>
.search-results {
  padding: 1rem 0;
}

.results-summary {
  margin-bottom: 1rem;
}

.summary-main {
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.execution-time {
  color: #999;
  margin-left: 0.5rem;
}

.summary-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.timing-detail {
  font-size: 0.75rem;
  color: #999;
  display: flex;
  gap: 0.5rem;
}

.timing-item {
  padding: 2px 6px;
  background: #f0f0f0;
  border-radius: 3px;
}

.results-list {
  min-height: 200px;
}

.load-more {
  display: flex;
  justify-content: center;
  margin-top: 1rem;
}

.empty-state {
  padding: 3rem 0;
}
</style>
