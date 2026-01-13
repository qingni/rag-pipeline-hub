<template>
  <div class="processing-progress">
    <div v-if="status === 'idle'" class="text-center py-4 text-gray-600">
      准备就绪
    </div>
    
    <div v-else-if="status === 'processing'" class="text-center py-4">
      <div class="spinner mx-auto mb-2"></div>
      <p class="font-semibold">处理中...</p>
      <p class="text-sm text-gray-600 mt-1">复杂文档可能需要较长时间，请耐心等待</p>
    </div>
    
    <div v-else-if="status === 'completed'" class="text-center py-4">
      <div class="text-4xl mb-2">✓</div>
      <p class="font-semibold text-green-600">处理完成</p>
    </div>
    
    <div v-else-if="status === 'failed'" class="text-center py-4">
      <div class="text-4xl mb-2">✗</div>
      <p class="font-semibold text-red-600">处理失败</p>
      <p v-if="error" class="text-sm text-red-600 mt-1">{{ formatError(error) }}</p>
      <p v-if="isTimeoutError" class="text-sm text-orange-600 mt-2">
        💡 提示：对于复杂文档，可以尝试选择 "PyMuPDF" 加载器以获得更快的处理速度
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    default: 'idle' // idle, processing, completed, failed
  },
  error: {
    type: String,
    default: null
  }
})

const isTimeoutError = computed(() => {
  if (!props.error) return false
  const errorLower = props.error.toLowerCase()
  return errorLower.includes('timeout') || errorLower.includes('exceeded')
})

function formatError(error) {
  if (!error) return ''
  // 简化超时错误信息
  if (error.toLowerCase().includes('timeout')) {
    return '处理超时，文档可能过于复杂'
  }
  return error
}
</script>
