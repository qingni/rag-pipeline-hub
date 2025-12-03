<template>
  <div class="processing-progress">
    <div v-if="status === 'idle'" class="text-center py-4 text-gray-600">
      准备就绪
    </div>
    
    <div v-else-if="status === 'processing'" class="text-center py-4">
      <div class="spinner mx-auto mb-2"></div>
      <p class="font-semibold">处理中...</p>
      <p class="text-sm text-gray-600 mt-1">请稍候</p>
    </div>
    
    <div v-else-if="status === 'completed'" class="text-center py-4">
      <div class="text-4xl mb-2">✓</div>
      <p class="font-semibold text-green-600">处理完成</p>
    </div>
    
    <div v-else-if="status === 'failed'" class="text-center py-4">
      <div class="text-4xl mb-2">✗</div>
      <p class="font-semibold text-red-600">处理失败</p>
      <p v-if="error" class="text-sm text-red-600 mt-1">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  status: {
    type: String,
    default: 'idle' // idle, processing, completed, failed
  },
  error: {
    type: String,
    default: null
  }
})
</script>
