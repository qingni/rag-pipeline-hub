<template>
  <div class="search-history">
    <!-- 历史列表头部 -->
    <div class="history-header">
      <span class="history-title">搜索历史</span>
      <t-button
        v-if="history.length > 0"
        variant="text"
        theme="danger"
        size="small"
        @click="handleClearAll"
      >
        清空历史
      </t-button>
    </div>
    
    <!-- 历史列表 -->
    <div v-if="history.length > 0" class="history-list">
      <div
        v-for="item in history"
        :key="item.id"
        class="history-item"
        @mousedown="onMouseDown"
        @click="handleItemClick($event, item)"
      >
        <div class="item-content">
          <div class="query-text">{{ item.query_text }}</div>
          <div class="item-meta">
            <!-- 🆕 检索模式标签 -->
            <t-tag 
              v-if="item.config?.search_mode"
              :theme="item.config.search_mode === 'hybrid' ? 'primary' : 'default'"
              variant="light"
              size="small"
            >
              {{ item.config.search_mode === 'hybrid' ? '混合' : '稠密' }}
            </t-tag>
            <span>{{ item.result_count }} 条结果</span>
            <span v-if="item.execution_time_ms">{{ item.execution_time_ms }}ms</span>
            <span>{{ formatTime(item.created_at) }}</span>
          </div>
        </div>
        <t-button
          variant="text"
          theme="default"
          size="small"
          shape="circle"
          class="delete-btn"
          @click.stop="handleDelete(item.id)"
        >
          <template #icon>
            <close-icon size="20px" />
          </template>
        </t-button>
      </div>
    </div>
    
    <!-- 空状态 -->
    <div v-else class="empty-history">
      <t-empty description="暂无搜索历史" size="small" />
    </div>
    
    <!-- 加载更多 -->
    <div v-if="hasMore" class="load-more">
      <t-button
        variant="text"
        size="small"
        :loading="isLoading"
        @click="handleLoadMore"
      >
        加载更多
      </t-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { CloseIcon } from 'tdesign-icons-vue-next'

const props = defineProps({
  history: {
    type: Array,
    default: () => []
  },
  total: {
    type: Number,
    default: 0
  },
  isLoading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['select', 'delete', 'clear', 'load-more'])

const hasMore = computed(() => {
  return props.history.length < props.total
})

// 记录鼠标按下位置，用于区分点击与文本选中
let mouseDownX = 0
let mouseDownY = 0

function onMouseDown(e) {
  mouseDownX = e.clientX
  mouseDownY = e.clientY
}

function handleItemClick(e, item) {
  // 如果用户拖拽选中了文本（鼠标移动超过 5px），不触发搜索
  const dx = Math.abs(e.clientX - mouseDownX)
  const dy = Math.abs(e.clientY - mouseDownY)
  if (dx > 5 || dy > 5) return

  // 如果当前有选中文本，也不触发搜索
  const selection = window.getSelection()
  if (selection && selection.toString().trim().length > 0) return

  emit('select', item)
}

function handleDelete(id) {
  emit('delete', id)
}

function handleClearAll() {
  emit('clear')
}

function handleLoadMore() {
  emit('load-more')
}

function formatTime(dateStr) {
  if (!dateStr) return ''
  
  // 处理 UTC 时间字符串，确保正确解析为本地时间
  let date
  if (typeof dateStr === 'string') {
    // 如果时间字符串没有时区信息，假设是 UTC 时间，添加 'Z' 后缀
    if (!dateStr.endsWith('Z') && !dateStr.includes('+') && !dateStr.includes('-', 10)) {
      date = new Date(dateStr + 'Z')
    } else {
      date = new Date(dateStr)
    }
  } else {
    date = new Date(dateStr)
  }
  
  const now = new Date()
  const diff = now - date
  
  // 小于1分钟
  if (diff < 60000) return '刚刚'
  // 小于1小时
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  // 小于24小时
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  // 小于7天
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`
  
  // 其他显示日期
  return date.toLocaleDateString()
}
</script>

<style scoped>
.search-history {
  padding: 0.5rem 0;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.history-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: #333;
}

.history-list {
  max-height: 400px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.history-item:hover {
  background-color: #f5f7fa;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.query-text {
  font-size: 0.875rem;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 0.25rem;
  user-select: text;
}

.item-meta {
  display: flex;
  gap: 0.75rem;
  font-size: 0.75rem;
  color: #999;
}

.empty-history {
  padding: 2rem 0;
}

.load-more {
  display: flex;
  justify-content: center;
  margin-top: 0.5rem;
}

/* 删除按钮样式 */
.delete-btn {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  color: #999;
}

.delete-btn:hover {
  color: #e34d59;
  background-color: rgba(227, 77, 89, 0.1);
}
</style>
