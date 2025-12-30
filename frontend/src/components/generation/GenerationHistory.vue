<template>
  <div class="generation-history">
    <div class="history-header">
      <h4 class="history-title">
        <History :size="18" />
        生成历史
      </h4>
      <div class="header-actions">
        <t-button
          variant="text"
          size="small"
          @click="handleRefresh"
          :loading="loading"
        >
          <template #icon>
            <RefreshCw :size="14" />
          </template>
          刷新
        </t-button>
        <t-popconfirm
          content="确定要清空所有历史记录吗？此操作不可恢复。"
          @confirm="handleClearAll"
        >
          <t-button
            variant="text"
            size="small"
            theme="danger"
            :disabled="items.length === 0"
          >
            <template #icon>
              <Trash2 :size="14" />
            </template>
            清空
          </t-button>
        </t-popconfirm>
      </div>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="loading && items.length === 0" class="loading-state">
      <t-loading size="small" />
      <span>加载中...</span>
    </div>
    
    <!-- 空状态 -->
    <div v-else-if="items.length === 0" class="empty-state">
      <FileText :size="32" />
      <p>暂无生成历史</p>
    </div>
    
    <!-- 历史列表 -->
    <div v-else class="history-list">
      <div
        v-for="item in items"
        :key="item.id"
        class="history-item"
        @click="handleItemClick(item)"
      >
        <div class="item-header">
          <span class="item-model">{{ item.model }}</span>
          <span :class="['item-status', `status-${item.status}`]">
            {{ getStatusText(item.status) }}
          </span>
        </div>
        <div class="item-question">{{ item.question }}</div>
        <div class="item-preview" v-if="item.answer_preview">
          {{ item.answer_preview }}
        </div>
        <div class="item-footer">
          <span class="item-time">{{ formatTime(item.created_at) }}</span>
          <t-button
            variant="text"
            size="small"
            theme="danger"
            @click.stop="handleDelete(item)"
          >
            <template #icon>
              <Trash2 :size="14" />
            </template>
          </t-button>
        </div>
      </div>
    </div>
    
    <!-- 分页 -->
    <div v-if="totalPages > 1" class="pagination">
      <t-pagination
        v-model:current="currentPage"
        :total="total"
        :page-size="pageSize"
        size="small"
        @change="handlePageChange"
      />
    </div>
    
    <!-- 详情弹窗 -->
    <t-dialog
      v-model:visible="detailVisible"
      header="生成详情"
      width="700px"
      :footer="false"
    >
      <div v-if="detailData" class="detail-content">
        <div class="detail-section">
          <h5>问题</h5>
          <p class="detail-text">{{ detailData.question }}</p>
        </div>
        
        <div class="detail-section">
          <h5>回答</h5>
          <div class="detail-answer" v-html="formatAnswer(detailData.answer)"></div>
        </div>
        
        <div class="detail-section" v-if="detailData.context_sources?.length">
          <h5>引用来源</h5>
          <div class="detail-sources">
            <div 
              v-for="source in detailData.context_sources" 
              :key="source.index"
              class="source-item"
            >
              <span class="source-index">[{{ source.index || detailData.context_sources.indexOf(source) + 1 }}]</span>
              <span class="source-file">{{ source.source_file }}</span>
            </div>
          </div>
        </div>
        
        <div class="detail-meta">
          <div class="meta-item">
            <span class="meta-label">模型</span>
            <span class="meta-value">{{ detailData.model }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">温度</span>
            <span class="meta-value">{{ detailData.temperature }}</span>
          </div>
          <div class="meta-item" v-if="detailData.token_usage">
            <span class="meta-label">Token 使用</span>
            <span class="meta-value">{{ detailData.token_usage.total_tokens }}</span>
          </div>
          <div class="meta-item" v-if="detailData.processing_time_ms">
            <span class="meta-label">耗时</span>
            <span class="meta-value">{{ formatDuration(detailData.processing_time_ms) }}</span>
          </div>
        </div>
      </div>
    </t-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { History, RefreshCw, Trash2, FileText } from 'lucide-vue-next'
import * as generationApi from '../../services/generationApi'

const props = defineProps({
  items: {
    type: Array,
    default: () => []
  },
  total: {
    type: Number,
    default: 0
  },
  page: {
    type: Number,
    default: 1
  },
  pageSize: {
    type: Number,
    default: 20
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['refresh', 'delete', 'clear', 'page-change'])

const currentPage = ref(props.page)
const detailVisible = ref(false)
const detailData = ref(null)

const totalPages = computed(() => Math.ceil(props.total / props.pageSize))

function getStatusText(status) {
  const statusMap = {
    pending: '等待中',
    generating: '生成中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return statusMap[status] || status
}

function formatTime(dateStr) {
  // 后端返回的是 UTC 时间，需要转换为本地时间
  // 如果时间字符串没有时区标识，添加 'Z' 表示 UTC
  let date
  if (dateStr.endsWith('Z') || dateStr.includes('+') || dateStr.includes('-', 10)) {
    date = new Date(dateStr)
  } else {
    date = new Date(dateStr + 'Z')
  }
  
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDuration(ms) {
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function formatAnswer(answer) {
  if (!answer) return ''
  return answer
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\[(\d+)\]/g, '<span class="source-ref">[$1]</span>')
    .replace(/\n/g, '<br>')
}

function handleRefresh() {
  emit('refresh')
}

function handleClearAll() {
  emit('clear')
}

function handleDelete(item) {
  emit('delete', item.id)
}

function handlePageChange(page) {
  currentPage.value = page
  emit('page-change', page)
}

async function handleItemClick(item) {
  try {
    const detail = await generationApi.getHistoryDetail(item.id)
    detailData.value = detail
    detailVisible.value = true
  } catch (error) {
    console.error('Failed to load detail:', error)
  }
}
</script>

<style scoped>
.generation-history {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  height: 100%;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.history-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 500;
  color: #1f2937;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 4px;
}

.loading-state,
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #9ca3af;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  background: #f9fafb;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.history-item:hover {
  background: #f3f4f6;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.item-model {
  font-size: 12px;
  font-weight: 500;
  color: #6366f1;
  background: #eef2ff;
  padding: 2px 8px;
  border-radius: 4px;
}

.item-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}

.status-completed {
  background: #dcfce7;
  color: #16a34a;
}

.status-failed {
  background: #fee2e2;
  color: #dc2626;
}

.status-cancelled {
  background: #fef3c7;
  color: #d97706;
}

.status-generating {
  background: #dbeafe;
  color: #2563eb;
}

.status-pending {
  background: #f3f4f6;
  color: #6b7280;
}

.item-question {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.item-preview {
  font-size: 13px;
  color: #6b7280;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 8px;
}

.item-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.item-time {
  font-size: 12px;
  color: #9ca3af;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

/* Detail Dialog */
.detail-content {
  max-height: 60vh;
  overflow-y: auto;
}

.detail-section {
  margin-bottom: 20px;
}

.detail-section h5 {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin: 0 0 8px 0;
}

.detail-text {
  color: #4b5563;
  line-height: 1.6;
  margin: 0;
}

.detail-answer {
  background: #f9fafb;
  border-radius: 8px;
  padding: 16px;
  line-height: 1.7;
  color: #374151;
}

.detail-answer :deep(.source-ref) {
  display: inline-block;
  background: #eef2ff;
  color: #6366f1;
  padding: 0 4px;
  border-radius: 4px;
  font-weight: 500;
  font-size: 0.85em;
}

.detail-sources {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.source-index {
  font-weight: 600;
  color: #6366f1;
}

.source-file {
  color: #4b5563;
}

.detail-meta {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  background: #f9fafb;
  border-radius: 8px;
  padding: 16px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 12px;
  color: #6b7280;
}

.meta-value {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}
</style>
