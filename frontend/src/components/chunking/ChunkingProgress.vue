<template>
  <div class="chunking-progress">
    <t-card v-if="task" title="分块进度" :bordered="false">
      <div class="progress-content">
        <t-steps :current="currentStep" :status="stepStatus">
          <t-step-item title="准备中" content="初始化分块任务" />
          <t-step-item title="处理中" content="正在执行分块操作" />
          <t-step-item title="完成" :content="completionMessage" />
        </t-steps>

        <div class="status-info">
          <t-space direction="vertical" size="large" style="width: 100%">
            <div class="info-item">
              <span class="label">任务状态：</span>
              <t-tag :theme="statusTheme">{{ statusText }}</t-tag>
            </div>

            <div v-if="task.error_message" class="info-item">
              <span class="label">错误信息：</span>
              <t-alert theme="error" :message="task.error_message" />
            </div>

            <div v-if="task.started_at" class="info-item">
              <span class="label">开始时间：</span>
              <span>{{ formatTime(task.started_at) }}</span>
            </div>

            <div v-if="task.completed_at" class="info-item">
              <span class="label">完成时间：</span>
              <span>{{ formatTime(task.completed_at) }}</span>
            </div>

            <div v-if="task.total_chunks" class="info-item">
              <span class="label">生成块数：</span>
              <t-tag theme="success" variant="light">
                {{ task.total_chunks }} 个
              </t-tag>
            </div>
          </t-space>
        </div>

        <t-divider />

        <div class="actions">
          <t-space>
            <t-button
              v-if="isCompleted && task.result_id"
              theme="primary"
              size="large"
              @click="handleViewResult"
            >
              <template #icon>
                <t-icon name="check-circle" />
              </template>
              查看分块结果
            </t-button>
            
            <t-button
              v-if="isProcessing"
              theme="default"
              disabled
              size="large"
            >
              <template #icon>
                <t-icon name="loading" />
              </template>
              处理中，请稍候...
            </t-button>

            <t-button
              v-if="isFailed"
              theme="danger"
              variant="outline"
              size="large"
              @click="$emit('retry')"
            >
              <template #icon>
                <t-icon name="refresh" />
              </template>
              重新尝试
            </t-button>
          </t-space>
        </div>
      </div>
    </t-card>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  task: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['viewResult', 'retry'])

const currentStep = computed(() => {
  if (!props.task) return 0
  if (props.task.status === 'pending') return 0
  if (props.task.status === 'processing') return 1
  return 2
})

const stepStatus = computed(() => {
  if (!props.task) return 'process'
  if (props.task.status === 'failed') return 'error'
  if (props.task.status === 'completed') return 'finish'
  return 'process'
})

const statusTheme = computed(() => {
  if (!props.task) return 'default'
  const themeMap = {
    'pending': 'warning',
    'processing': 'primary',
    'completed': 'success',
    'failed': 'danger'
  }
  return themeMap[props.task.status] || 'default'
})

const statusText = computed(() => {
  if (!props.task) return '-'
  const textMap = {
    'pending': '等待中',
    'processing': '处理中',
    'completed': '已完成',
    'failed': '失败'
  }
  return textMap[props.task.status] || props.task.status
})

const completionMessage = computed(() => {
  if (!props.task) return '分块完成'
  if (props.task.status === 'completed') {
    return `成功生成 ${props.task.total_chunks || 0} 个文本块`
  }
  if (props.task.status === 'failed') {
    return '分块失败'
  }
  return '分块完成'
})

const isCompleted = computed(() => props.task?.status === 'completed')
const isProcessing = computed(() => ['pending', 'processing'].includes(props.task?.status))
const isFailed = computed(() => props.task?.status === 'failed')

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

const handleViewResult = () => {
  emit('viewResult', props.task.result_id)
}
</script>

<style scoped>
.chunking-progress {
  width: 100%;
}

.chunking-progress :deep(.t-card) {
  box-shadow: var(--td-shadow-1);
}

.chunking-progress :deep(.t-card__title) {
  font-size: 18px;
  font-weight: 600;
}

.progress-content {
  padding: 24px 0;
}

.progress-content :deep(.t-steps) {
  padding: 0 40px;
}

.status-info {
  margin-top: 32px;
  padding: 24px;
  background-color: var(--td-bg-color-container-hover);
  border-radius: 6px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
}

.label {
  font-weight: 500;
  min-width: 100px;
  color: var(--td-text-color-secondary);
}

.actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 24px;
}
</style>
