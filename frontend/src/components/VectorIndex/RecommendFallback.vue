<template>
  <div v-if="visible" class="recommend-fallback">
    <t-alert
      theme="warning"
      :message="message"
      :close="true"
      @close="handleClose"
    >
      <template #icon>
        <t-icon name="info-circle-filled" />
      </template>
    </t-alert>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  /** 提示信息 */
  message: {
    type: String,
    default: '未精确匹配推荐规则，已使用通用默认值（HNSW + COSINE）。您可以手动修改索引算法和度量类型。'
  },
  /** 是否显示 */
  visible: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close'])

const handleClose = () => {
  emit('close')
}
</script>

<style scoped>
.recommend-fallback {
  margin-bottom: 12px;
}

.recommend-fallback :deep(.t-alert) {
  font-size: 12px;
}
</style>
