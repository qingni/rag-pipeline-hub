<template>
  <div class="index-progress">
    <t-card :bordered="false" class="progress-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">索引构建进度</span>
          <t-tag v-if="status" :theme="statusTheme" variant="light">
            {{ statusText }}
          </t-tag>
        </div>
      </template>

      <!-- 进度条 -->
      <div class="progress-section">
        <t-progress 
          :percentage="percentage" 
          :status="progressStatus"
          :label="progressLabel"
          size="large"
        />
        
        <div class="progress-info">
          <span class="count">{{ processed }} / {{ total }}</span>
          <span class="status-text">{{ statusMessage }}</span>
        </div>
      </div>

      <!-- 任务详情 -->
      <div v-if="taskId" class="task-details">
        <t-descriptions :column="2" size="small" bordered>
          <t-descriptions-item label="任务ID">
            <t-tooltip :content="taskId">
              <span class="task-id">{{ shortTaskId }}</span>
            </t-tooltip>
          </t-descriptions-item>
          <t-descriptions-item label="索引名称">
            {{ collectionName || '-' }}
          </t-descriptions-item>
          <t-descriptions-item label="开始时间">
            {{ formatDate(createdAt) }}
          </t-descriptions-item>
          <t-descriptions-item label="预计剩余">
            {{ estimatedRemaining }}
          </t-descriptions-item>
        </t-descriptions>
      </div>

      <!-- 错误信息 -->
      <div v-if="error" class="error-section">
        <t-alert theme="error" :message="error" close @close="$emit('clearError')">
          <template #operation>
            <t-button theme="danger" variant="text" size="small" @click="$emit('retry')">
              重试
            </t-button>
          </template>
        </t-alert>
      </div>

      <!-- 操作按钮 -->
      <div v-if="showActions" class="action-buttons">
        <t-button 
          v-if="canCancel" 
          theme="default" 
          variant="outline"
          :loading="cancelling"
          @click="$emit('cancel')"
        >
          取消任务
        </t-button>
      </div>
    </t-card>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  // 任务信息
  taskId: {
    type: String,
    default: ''
  },
  collectionName: {
    type: String,
    default: ''
  },
  // 进度信息
  status: {
    type: String,
    default: 'pending', // pending, running, completed, failed
    validator: (val) => ['pending', 'running', 'completed', 'failed'].includes(val)
  },
  percentage: {
    type: Number,
    default: 0
  },
  processed: {
    type: Number,
    default: 0
  },
  total: {
    type: Number,
    default: 0
  },
  // 时间信息
  createdAt: {
    type: String,
    default: ''
  },
  completedAt: {
    type: String,
    default: ''
  },
  // 错误信息
  error: {
    type: String,
    default: ''
  },
  // 控制
  showActions: {
    type: Boolean,
    default: true
  },
  cancelling: {
    type: Boolean,
    default: false
  }
});

defineEmits(['cancel', 'retry', 'clearError']);

// 计算属性
const statusTheme = computed(() => {
  const map = {
    pending: 'default',
    running: 'warning',
    completed: 'success',
    failed: 'danger'
  };
  return map[props.status] || 'default';
});

const statusText = computed(() => {
  const map = {
    pending: '等待中',
    running: '构建中',
    completed: '已完成',
    failed: '失败'
  };
  return map[props.status] || props.status;
});

const progressStatus = computed(() => {
  const map = {
    pending: 'active',
    running: 'active',
    completed: 'success',
    failed: 'error'
  };
  return map[props.status] || 'active';
});

const progressLabel = computed(() => {
  return props.percentage ? `${props.percentage.toFixed(1)}%` : '0%';
});

const statusMessage = computed(() => {
  if (props.status === 'pending') return '等待开始...';
  if (props.status === 'running') return '正在构建索引...';
  if (props.status === 'completed') return '索引构建完成';
  if (props.status === 'failed') return '索引构建失败';
  return '';
});

const shortTaskId = computed(() => {
  if (!props.taskId) return '-';
  return props.taskId.substring(0, 8) + '...';
});

const canCancel = computed(() => {
  return props.status === 'pending' || props.status === 'running';
});

const estimatedRemaining = computed(() => {
  if (props.status === 'completed') return '已完成';
  if (props.status === 'failed') return '-';
  if (!props.processed || !props.total || props.processed === 0) return '计算中...';
  
  // 简单估算：假设每个向量处理时间一致
  const remaining = props.total - props.processed;
  if (remaining <= 0) return '即将完成';
  
  // 基于已处理数量估算
  if (props.percentage > 0 && props.percentage < 100) {
    const remainingPercent = 100 - props.percentage;
    const estimatedSeconds = Math.ceil(remainingPercent / 10); // 粗略估计
    if (estimatedSeconds < 60) return `约 ${estimatedSeconds} 秒`;
    return `约 ${Math.ceil(estimatedSeconds / 60)} 分钟`;
  }
  
  return '计算中...';
});

// 工具函数
const formatDate = (dateString) => {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};
</script>

<style scoped>
.index-progress {
  width: 100%;
}

.progress-card {
  background: var(--td-bg-color-container);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
}

.progress-section {
  margin-bottom: 16px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  font-size: 14px;
}

.count {
  font-weight: 500;
  color: var(--td-brand-color);
}

.status-text {
  color: var(--td-text-color-secondary);
}

.task-details {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--td-component-border);
}

.task-id {
  font-family: monospace;
  font-size: 12px;
  cursor: pointer;
}

.error-section {
  margin-top: 16px;
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--td-component-border);
}
</style>
