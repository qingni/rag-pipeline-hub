<template>
  <t-card :bordered="false" class="embedding-result-card">
    <template v-if="!result">
      <t-empty description="暂无向量化结果，请选择文档并开始向量化" />
    </template>
    
    <template v-else>
      <!-- 结果头部信息 -->
      <div class="result-header">
        <div class="header-left">
          <Database :size="20" class="header-icon" />
          <h3 class="result-title">最新向量化结果</h3>
        </div>
        <div class="header-right">
          <t-tag :theme="getStatusTheme(result.status)" variant="light">
            {{ getStatusText(result.status) }}
          </t-tag>
          <span class="result-time">{{ formatTime(result.created_at) }}</span>
        </div>
      </div>
      
      <!-- 错误信息 -->
      <t-alert
        v-if="result.error_message"
        theme="error"
        :message="result.error_message"
        class="error-alert"
      />
    </template>
  </t-card>
</template>

<script setup>
import { computed } from 'vue'
import { Database } from 'lucide-vue-next'

const props = defineProps({
  result: {
    type: Object,
    default: null
  },
  documentInfo: {
    type: Object,
    default: null
  }
})

function getStatusTheme(status) {
  const themes = {
    'SUCCESS': 'success',
    'PARTIAL_SUCCESS': 'warning',
    'FAILED': 'danger'
  }
  return themes[status] || 'default'
}

function getStatusText(status) {
  const texts = {
    'SUCCESS': '成功',
    'PARTIAL_SUCCESS': '部分成功',
    'FAILED': '失败'
  }
  return texts[status] || status
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  // 小于1分钟
  if (diff < 60000) {
    return '刚刚'
  }
  // 小于1小时
  if (diff < 3600000) {
    return `${Math.floor(diff / 60000)} 分钟前`
  }
  // 小于24小时
  if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)} 小时前`
  }
  // 格式化日期
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.embedding-result-card :deep(.t-card__body) {
  padding: 0;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
  background-color: #f9fafb;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon {
  color: #3b82f6;
}

.result-title {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.result-time {
  font-size: 13px;
  color: #6b7280;
}

.error-alert {
  margin: 16px 24px;
}
</style>
