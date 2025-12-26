<template>
  <div class="search-results">
    <!-- 结果统计 -->
    <div v-if="results.length > 0" class="results-summary">
      <span>找到 <strong>{{ totalCount }}</strong> 条相关结果</span>
      <span v-if="executionTime > 0" class="execution-time">
        (耗时 {{ executionTime }}ms)
      </span>
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
  font-size: 0.875rem;
  color: #666;
}

.execution-time {
  color: #999;
  margin-left: 0.5rem;
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
