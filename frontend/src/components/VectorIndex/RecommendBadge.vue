<template>
  <div v-if="visible" class="recommend-badge">
    <t-tag
      :theme="isFallback ? 'warning' : 'primary'"
      variant="light"
      size="small"
    >
      <template #icon>
        <t-icon :name="isFallback ? 'info-circle' : 'thumb-up'" />
      </template>
      {{ displayReason }}
    </t-tag>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** 推荐理由文案 */
  reason: {
    type: String,
    default: ''
  },
  /** 是否为兜底推荐 */
  isFallback: {
    type: Boolean,
    default: false
  },
  /** 是否显示 */
  visible: {
    type: Boolean,
    default: true
  }
})

const displayReason = computed(() => {
  if (props.isFallback) {
    return props.reason || '未精确匹配推荐规则，已使用通用默认值'
  }
  return props.reason || '智能推荐'
})
</script>

<style scoped>
.recommend-badge {
  display: inline-flex;
  align-items: flex-start;
  margin-left: 0;
}

.recommend-badge :deep(.t-tag) {
  max-width: 100%;
  white-space: normal;
  height: auto;
  line-height: 1.4;
  padding: 4px 8px;
}
</style>
