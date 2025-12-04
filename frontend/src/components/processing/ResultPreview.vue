<template>
  <div class="result-preview card">
    <div v-if="!result" class="text-center py-8 text-gray-600">
      暂无结果
    </div>
    
    <div v-else>
      <div class="mb-4 pb-4 border-b relative">
        <h4 class="font-semibold mb-2">处理信息</h4>
        <div class="absolute top-0 right-0">
          <slot name="actions"></slot>
        </div>
        <div class="grid grid-cols-2 gap-4 text-sm pr-24">
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
      
      <div v-if="result.metadata || result.extra_metadata" class="mt-4">
        <h4 class="font-semibold mb-2">元数据</h4>
        <div class="bg-gray-50 p-4 rounded text-sm">
          <div v-if="result.extra_metadata" class="grid grid-cols-2 gap-3 mb-3">
            <div v-if="result.extra_metadata.total_pages">
              <span class="text-gray-600">总页数:</span>
              <span class="ml-2 font-medium">{{ result.extra_metadata.total_pages }}</span>
            </div>
            <div v-if="result.extra_metadata.total_chars">
              <span class="text-gray-600">总字符数:</span>
              <span class="ml-2 font-medium">{{ result.extra_metadata.total_chars.toLocaleString() }}</span>
            </div>
            <div v-if="result.extra_metadata.loader_type">
              <span class="text-gray-600">加载器:</span>
              <span class="ml-2 font-medium">{{ result.extra_metadata.loader_type }}</span>
            </div>
            <div v-if="result.extra_metadata.file_format">
              <span class="text-gray-600">文件格式:</span>
              <span class="ml-2 font-medium">{{ result.extra_metadata.file_format.toUpperCase() }}</span>
            </div>
          </div>
          <div v-if="result.metadata" class="mt-3 pt-3 border-t">
            <details class="cursor-pointer">
              <summary class="text-xs text-gray-600 font-medium">查看完整元数据</summary>
              <pre class="mt-2 text-xs overflow-auto max-h-64">{{ JSON.stringify(result.metadata, null, 2) }}</pre>
            </details>
          </div>
        </div>
      </div>
      
      <!-- 显示加载结果数据摘要 -->
      <div v-if="result.result_data" class="mt-4">
        <h4 class="font-semibold mb-2">加载结果统计</h4>
        <div class="bg-blue-50 p-4 rounded text-sm">
          <div class="grid grid-cols-2 gap-3">
            <div v-if="result.result_data.total_pages">
              <span class="text-gray-600">提取页数:</span>
              <span class="ml-2 font-medium text-blue-700">{{ result.result_data.total_pages }}</span>
            </div>
            <div v-if="result.result_data.total_chars">
              <span class="text-gray-600">提取字符:</span>
              <span class="ml-2 font-medium text-blue-700">{{ result.result_data.total_chars.toLocaleString() }}</span>
            </div>
            <div v-if="result.result_data.success !== undefined">
              <span class="text-gray-600">处理状态:</span>
              <span class="ml-2 font-medium" :class="result.result_data.success ? 'text-green-600' : 'text-red-600'">
                {{ result.result_data.success ? '✓ 成功' : '✗ 失败' }}
              </span>
            </div>
            <div v-if="result.result_data.pages && result.result_data.pages.length > 0">
              <span class="text-gray-600">提取页面:</span>
              <span class="ml-2 font-medium text-blue-700">{{ result.result_data.pages.length }} 页</span>
            </div>
          </div>
          
          <!-- 显示每页字符分布统计 -->
          <div v-if="result.result_data.pages && result.result_data.pages.length > 0" class="mt-3 pt-3 border-t border-blue-200">
            <div class="text-xs text-gray-600 mb-2">页面字符分布:</div>
            <div class="flex items-center gap-2 flex-wrap">
              <div 
                v-for="(page, index) in result.result_data.pages.slice(0, 10)" 
                :key="index"
                class="px-2 py-1 bg-white rounded border border-blue-200 text-xs"
                :title="`第 ${page.page_number || index + 1} 页: ${page.char_count || 0} 字符`"
              >
                P{{ page.page_number || index + 1 }}: {{ formatNumber(page.char_count || 0) }}
              </div>
              <div v-if="result.result_data.pages.length > 10" class="text-xs text-gray-500">
                ... +{{ result.result_data.pages.length - 10 }} 页
              </div>
            </div>
          </div>
        </div>
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

function formatNumber(num) {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}
</script>

<style scoped>
.line-clamp-4 {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
