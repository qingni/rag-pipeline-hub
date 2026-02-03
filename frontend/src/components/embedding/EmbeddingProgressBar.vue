<template>
  <div class="embedding-progress-bar">
    <!-- 头部信息 -->
    <div class="progress-header">
      <div class="progress-title">
        <t-icon :name="statusIcon" :class="statusClass" />
        <span>{{ statusText }}</span>
      </div>
      <div class="progress-stats">
        <span class="stat">{{ progress.completed }}/{{ progress.total }}</span>
        <span class="percentage">{{ progress.percentage?.toFixed(1) || 0 }}%</span>
      </div>
    </div>
    
    <!-- 进度条 -->
    <div class="progress-bar-container">
      <div class="progress-bar">
        <div 
          class="progress-fill completed" 
          :style="{ width: completedWidth }"
        ></div>
        <div 
          class="progress-fill cached" 
          :style="{ width: cachedWidth, left: completedWidth }"
        ></div>
        <div 
          class="progress-fill failed" 
          :style="{ width: failedWidth, left: processedWidth }"
        ></div>
      </div>
    </div>
    
    <!-- 详细统计 -->
    <div class="progress-details" v-if="showDetails">
      <div class="detail-item">
        <span class="label">已完成</span>
        <span class="value success">{{ progress.completed }}</span>
      </div>
      <div class="detail-item" v-if="progress.cached > 0">
        <span class="label">缓存命中</span>
        <span class="value cached">{{ progress.cached }}</span>
      </div>
      <div class="detail-item" v-if="progress.failed > 0">
        <span class="label">失败</span>
        <span class="value error">{{ progress.failed }}</span>
      </div>
      <div class="detail-item">
        <span class="label">速度</span>
        <span class="value">{{ speed }}</span>
      </div>
      <div class="detail-item" v-if="eta">
        <span class="label">预计剩余</span>
        <span class="value">{{ eta }}</span>
      </div>
    </div>
    
    <!-- 当前处理项 -->
    <div class="current-item" v-if="progress.current_item && isProcessing">
      <t-icon name="loading" class="spinning" />
      <span>{{ progress.current_item }}</span>
    </div>
    
    <!-- 操作按钮 -->
    <div class="progress-actions" v-if="showActions && isProcessing">
      <t-button 
        variant="text" 
        theme="danger" 
        size="small"
        @click="$emit('cancel')"
      >
        取消
      </t-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  progress: {
    type: Object,
    required: true,
    default: () => ({
      total: 0,
      completed: 0,
      failed: 0,
      cached: 0,
      speed: 0,
      eta_seconds: 0,
      status: 'pending',
      percentage: 0,
      current_item: null,
    }),
  },
  showDetails: {
    type: Boolean,
    default: true,
  },
  showActions: {
    type: Boolean,
    default: true,
  },
});

const emit = defineEmits(['cancel']);

// Computed
const isProcessing = computed(() => {
  return props.progress.status === 'processing';
});

const statusIcon = computed(() => {
  switch (props.progress.status) {
    case 'completed': return 'check-circle';
    case 'failed': return 'close-circle';
    case 'cancelled': return 'error-circle';
    case 'partial': return 'error-circle';
    case 'processing': return 'loading';
    default: return 'time';
  }
});

const statusClass = computed(() => {
  switch (props.progress.status) {
    case 'completed': return 'success';
    case 'failed': return 'error';
    case 'cancelled': return 'warning';
    case 'partial': return 'warning';
    case 'processing': return 'processing';
    default: return 'pending';
  }
});

const statusText = computed(() => {
  switch (props.progress.status) {
    case 'completed': return '向量化完成';
    case 'failed': return '向量化失败';
    case 'cancelled': return '已取消';
    case 'partial': return '部分完成';
    case 'processing': return '向量化中...';
    default: return '准备中';
  }
});

const completedWidth = computed(() => {
  const total = props.progress.total || 1;
  return `${(props.progress.completed / total) * 100}%`;
});

const cachedWidth = computed(() => {
  const total = props.progress.total || 1;
  return `${(props.progress.cached / total) * 100}%`;
});

const failedWidth = computed(() => {
  const total = props.progress.total || 1;
  return `${(props.progress.failed / total) * 100}%`;
});

const processedWidth = computed(() => {
  const total = props.progress.total || 1;
  const processed = props.progress.completed + props.progress.cached;
  return `${(processed / total) * 100}%`;
});

const speed = computed(() => {
  const s = props.progress.speed || 0;
  if (s < 1) return `${(s * 60).toFixed(1)} 块/分钟`;
  return `${s.toFixed(1)} 块/秒`;
});

const eta = computed(() => {
  const seconds = props.progress.eta_seconds || 0;
  if (seconds <= 0) return null;
  if (seconds < 60) return `${Math.ceil(seconds)} 秒`;
  if (seconds < 3600) return `${Math.ceil(seconds / 60)} 分钟`;
  return `${(seconds / 3600).toFixed(1)} 小时`;
});
</script>

<style scoped>
.embedding-progress-bar {
  background: var(--td-bg-color-container);
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 8px;
  padding: 16px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.progress-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.progress-title .success {
  color: var(--td-success-color);
}

.progress-title .error {
  color: var(--td-error-color);
}

.progress-title .warning {
  color: var(--td-warning-color);
}

.progress-title .processing {
  color: var(--td-brand-color);
  animation: spin 1s linear infinite;
}

.progress-title .pending {
  color: var(--td-text-color-secondary);
}

.progress-stats {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-stats .stat {
  font-size: 13px;
  color: var(--td-text-color-secondary);
}

.progress-stats .percentage {
  font-size: 16px;
  font-weight: 600;
  color: var(--td-brand-color);
}

.progress-bar-container {
  margin-bottom: 12px;
}

.progress-bar {
  position: relative;
  height: 8px;
  background: var(--td-gray-color-3);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  position: absolute;
  top: 0;
  height: 100%;
  transition: width 0.3s ease;
}

.progress-fill.completed {
  background: var(--td-success-color);
}

.progress-fill.cached {
  background: var(--td-brand-color);
}

.progress-fill.failed {
  background: var(--td-error-color);
}

.progress-details {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 12px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.detail-item .label {
  color: var(--td-text-color-secondary);
}

.detail-item .value {
  font-weight: 500;
}

.detail-item .value.success {
  color: var(--td-success-color);
}

.detail-item .value.cached {
  color: var(--td-brand-color);
}

.detail-item .value.error {
  color: var(--td-error-color);
}

.current-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 8px 12px;
  background: var(--td-bg-color-secondarycontainer);
  border-radius: 4px;
  font-size: 12px;
  color: var(--td-text-color-secondary);
}

.current-item .spinning {
  animation: spin 1s linear infinite;
}

.progress-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
