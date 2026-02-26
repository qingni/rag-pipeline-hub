<template>
  <div v-if="visible" class="index-progress">
    <t-card :bordered="false" class="progress-card">
      <template #header>
        <div class="progress-header">
          <span class="progress-title">索引构建进度</span>
          <t-tag :theme="statusTheme" variant="light" size="small">
            {{ statusText }}
          </t-tag>
        </div>
      </template>

      <div class="progress-body">
        <!-- 进度条 -->
        <t-progress
          :percentage="percentage"
          :status="progressStatus"
          :stroke-width="8"
          :label="progressLabel"
        />

        <!-- 进度详情 -->
        <div class="progress-detail">
          <div class="detail-item">
            <span class="detail-label">已处理</span>
            <span class="detail-value">{{ processedCount }} / {{ totalCount }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">索引算法</span>
            <span class="detail-value">{{ indexType }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">耗时</span>
            <span class="detail-value">{{ elapsedTime }}</span>
          </div>
        </div>

        <!-- 错误信息 -->
        <t-alert
          v-if="errorMessage"
          theme="error"
          :message="errorMessage"
          class="progress-error"
        />
      </div>
    </t-card>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** 是否显示 */
  visible: {
    type: Boolean,
    default: false
  },
  /** 任务状态: pending / running / completed / failed */
  status: {
    type: String,
    default: 'pending'
  },
  /** 进度百分比 0-100 */
  percentage: {
    type: Number,
    default: 0
  },
  /** 已处理条数 */
  processedCount: {
    type: Number,
    default: 0
  },
  /** 总条数 */
  totalCount: {
    type: Number,
    default: 0
  },
  /** 索引算法类型 */
  indexType: {
    type: String,
    default: 'FLAT'
  },
  /** 开始时间 */
  startTime: {
    type: [Date, String],
    default: null
  },
  /** 错误信息 */
  errorMessage: {
    type: String,
    default: ''
  }
})

const statusTheme = computed(() => {
  const map = {
    pending: 'default',
    running: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return map[props.status] || 'default'
})

const statusText = computed(() => {
  const map = {
    pending: '等待中',
    running: '构建中',
    completed: '已完成',
    failed: '失败'
  }
  return map[props.status] || props.status
})

const progressStatus = computed(() => {
  if (props.status === 'failed') return 'error'
  if (props.status === 'completed') return 'success'
  return 'active'
})

const progressLabel = computed(() => {
  if (props.status === 'completed') return '完成'
  if (props.status === 'failed') return '失败'
  return `${props.percentage}%`
})

const elapsedTime = computed(() => {
  if (!props.startTime) return '-'
  const start = new Date(props.startTime)
  const now = new Date()
  const diff = Math.floor((now - start) / 1000)
  if (diff < 60) return `${diff}s`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ${diff % 60}s`
  return `${Math.floor(diff / 3600)}h ${Math.floor((diff % 3600) / 60)}m`
})
</script>

<style scoped>
.index-progress {
  margin-bottom: 16px;
}

.progress-card {
  background: var(--td-bg-color-container);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-title {
  font-size: 14px;
  font-weight: 600;
}

.progress-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.progress-detail {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: 12px;
  color: var(--td-text-color-secondary);
}

.detail-value {
  font-size: 14px;
  font-weight: 500;
  font-family: monospace;
}

.progress-error {
  margin-top: 8px;
}
</style>
