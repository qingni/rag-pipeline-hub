<template>
  <div class="result-preview card">
    <div v-if="!result" class="text-center py-8 text-gray-600">
      暂无结果
    </div>
    
    <div v-else>
      <div class="mb-4 pb-4 border-b">
        <h4 class="font-semibold mb-2">处理信息</h4>
        <div class="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span class="text-gray-600">类型:</span>
            <span class="ml-2 font-medium">{{ result.processing_type }}</span>
          </div>
          <div>
            <span class="text-gray-600">提供商:</span>
            <span class="ml-2 font-medium">{{ result.provider || 'N/A' }}</span>
          </div>
          <div>
            <span class="text-gray-600">状态:</span>
            <span
              class="ml-2 px-2 py-1 rounded text-xs font-semibold"
              :class="getStatusClass(result.status)"
            >
              {{ getStatusText(result.status) }}
            </span>
          </div>
          <div>
            <span class="text-gray-600">创建时间:</span>
            <span class="ml-2 font-medium">{{ formatDate(result.created_at) }}</span>
          </div>
        </div>
      </div>
      
      <div v-if="result.metadata">
        <h4 class="font-semibold mb-2">元数据</h4>
        <pre class="bg-gray-50 p-4 rounded text-xs overflow-auto max-h-64">{{ JSON.stringify(result.metadata, null, 2) }}</pre>
      </div>
      
      <div v-if="result.result_path" class="mt-4">
        <p class="text-sm text-gray-600">
          结果文件: <code class="bg-gray-100 px-2 py-1 rounded text-xs">{{ result.result_path }}</code>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  result: {
    type: Object,
    default: null
  }
})

function formatDate(dateString) {
  if (!dateString) return '-'
  
  // 解析 ISO 8601 格式的UTC时间字符串
  const date = new Date(dateString)
  
  // 检查是否是有效日期
  if (isNaN(date.getTime())) return dateString
  
  // 使用本地时区格式化显示
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

function getStatusClass(status) {
  const classes = {
    pending: 'bg-gray-100 text-gray-800',
    running: 'bg-yellow-100 text-yellow-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800'
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}

function getStatusText(status) {
  const texts = {
    pending: '待处理',
    running: '运行中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status] || status
}
</script>
