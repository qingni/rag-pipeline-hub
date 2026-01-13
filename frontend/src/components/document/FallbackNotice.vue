<template>
  <t-alert
    v-if="showNotice"
    :theme="alertTheme"
    :message="alertMessage"
    :close="true"
    @close="handleClose"
    class="fallback-notice"
  >
    <template #operation>
      <t-link theme="primary" @click="showDetails = !showDetails">
        {{ showDetails ? '收起详情' : '查看详情' }}
      </t-link>
    </template>
  </t-alert>
  
  <t-collapse v-if="showDetails && showNotice" class="fallback-details">
    <t-collapse-panel header="降级详情">
      <div class="detail-content">
        <div class="detail-item">
          <span class="label">主解析器:</span>
          <span class="value">{{ primaryLoader }}</span>
        </div>
        <div class="detail-item">
          <span class="label">实际使用:</span>
          <span class="value">{{ actualLoader }}</span>
        </div>
        <div v-if="fallbackReason" class="detail-item">
          <span class="label">降级原因:</span>
          <span class="value">{{ fallbackReason }}</span>
        </div>
        <div v-if="fallbackChain.length > 0" class="detail-item">
          <span class="label">降级链:</span>
          <div class="fallback-chain">
            <t-tag 
              v-for="(loader, index) in fallbackChain" 
              :key="loader"
              :theme="index === fallbackChain.length - 1 ? 'success' : 'default'"
              size="small"
            >
              {{ loader }}
            </t-tag>
            <span v-if="index < fallbackChain.length - 1" class="chain-arrow">→</span>
          </div>
        </div>
      </div>
    </t-collapse-panel>
  </t-collapse>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  /**
   * 加载结果对象，包含降级信息
   */
  loadResult: {
    type: Object,
    default: null
  },
  /**
   * 是否显示通知
   */
  visible: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['close'])

const showDetails = ref(false)

// 计算是否显示通知
const showNotice = computed(() => {
  if (!props.visible || !props.loadResult) return false
  return props.loadResult.fallback_used === true
})

// 主解析器
const primaryLoader = computed(() => {
  return props.loadResult?.primary_loader || 'docling'
})

// 实际使用的解析器
const actualLoader = computed(() => {
  return props.loadResult?.loader_used || props.loadResult?.loader || 'unknown'
})

// 降级原因
const fallbackReason = computed(() => {
  return props.loadResult?.fallback_reason || ''
})

// 降级链
const fallbackChain = computed(() => {
  if (!props.loadResult?.fallback_chain) return []
  return props.loadResult.fallback_chain
})

// Alert 主题
const alertTheme = computed(() => {
  // 如果成功降级，显示警告；如果降级失败，显示错误
  if (props.loadResult?.success) {
    return 'warning'
  }
  return 'error'
})

// Alert 消息
const alertMessage = computed(() => {
  if (!showNotice.value) return ''
  
  if (props.loadResult?.success) {
    return `文档已使用备用解析器 "${actualLoader.value}" 成功加载`
  }
  return `主解析器不可用，已降级到 "${actualLoader.value}"`
})

function handleClose() {
  emit('close')
}
</script>

<style scoped>
.fallback-notice {
  margin-bottom: 12px;
}

.fallback-details {
  margin-top: 8px;
  margin-bottom: 12px;
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.detail-item .label {
  color: #6b7280;
  font-size: 13px;
  min-width: 80px;
  flex-shrink: 0;
}

.detail-item .value {
  color: #374151;
  font-size: 13px;
  font-weight: 500;
}

.fallback-chain {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.chain-arrow {
  color: #9ca3af;
  font-size: 12px;
  margin: 0 2px;
}
</style>
