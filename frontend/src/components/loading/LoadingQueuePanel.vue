<template>
  <div class="loading-queue-panel" :class="{ expanded: isExpanded }">
    <!-- 悬浮按钮（收起状态） -->
    <div 
      v-if="!isExpanded && hasActiveTasks" 
      class="queue-fab"
      @click="toggleExpand"
    >
      <div class="fab-content">
        <LoaderIcon class="fab-icon spinning" :size="20" />
        <span class="fab-count">{{ activeTaskCount }}</span>
      </div>
      <t-progress 
        :percentage="overallProgress" 
        :show-label="false"
        size="small"
        class="fab-progress"
      />
    </div>
    
    <!-- 展开的面板 -->
    <t-card 
      v-if="isExpanded" 
      class="queue-card"
      :bordered="true"
    >
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <LayersIcon :size="18" />
            <span class="header-title">加载队列</span>
            <t-tag 
              v-if="activeTaskCount > 0" 
              theme="primary" 
              size="small"
            >
              {{ activeTaskCount }} 个任务
            </t-tag>
          </div>
          <div class="header-actions">
            <t-button 
              v-if="completedTasks.length > 0"
              theme="default" 
              variant="text" 
              size="small"
              @click="clearCompleted"
            >
              清除已完成
            </t-button>
            <t-button
              theme="default"
              variant="text"
              size="small"
              @click="toggleExpand"
            >
              <MinimizeIcon :size="16" />
            </t-button>
          </div>
        </div>
      </template>
      
      <!-- 任务列表 -->
      <div class="task-list">
        <template v-if="taskList.length > 0">
          <div 
            v-for="task in taskList" 
            :key="task.task_id"
            class="task-item"
            :class="getTaskClass(task)"
          >
            <div class="task-info">
              <div class="task-main">
                <component :is="getTaskIcon(task)" :size="16" class="task-icon" />
                <span class="task-name">{{ getTaskName(task) }}</span>
              </div>
              <div class="task-meta">
                <span class="task-loader">{{ task.loader_type || task.loader_name || '-' }}</span>
                <span class="task-time">{{ formatTime(task) }}</span>
              </div>
            </div>
            
            <div class="task-status">
              <!-- 进度条 -->
              <t-progress 
                v-if="isTaskActive(task)"
                :percentage="task.progress || 0" 
                :show-label="false"
                size="small"
                class="task-progress"
              />
              
              <!-- 状态标签 -->
              <t-tag 
                :theme="getStatusTheme(task.status)" 
                size="small"
                class="status-tag"
              >
                {{ getStatusText(task.status) }}
              </t-tag>
              
              <!-- 操作按钮 -->
              <t-button
                v-if="isTaskActive(task)"
                theme="danger"
                variant="text"
                size="small"
                @click="cancelTask(task.task_id)"
              >
                <XIcon :size="14" />
              </t-button>
            </div>
          </div>
        </template>
        
        <div v-else class="empty-state">
          <CheckCircleIcon :size="32" class="empty-icon" />
          <p>暂无加载任务</p>
        </div>
      </div>
      
      <!-- 队列统计 -->
      <div v-if="hasActiveTasks" class="queue-stats">
        <t-progress 
          :percentage="overallProgress" 
          :show-label="true"
          theme="plum"
        />
      </div>
    </t-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useLoadingQueueStore, TaskStatus } from '../../stores/loadingQueueStore'
import { 
  Loader as LoaderIcon,
  Layers as LayersIcon, 
  Minimize2 as MinimizeIcon,
  X as XIcon,
  CheckCircle as CheckCircleIcon,
  FileText as FileTextIcon,
  AlertCircle as AlertCircleIcon,
  Clock as ClockIcon
} from 'lucide-vue-next'

const queueStore = useLoadingQueueStore()

// 展开/收起状态
const isExpanded = ref(false)

// Computed
const taskList = computed(() => queueStore.taskList)
const activeTasks = computed(() => queueStore.activeTasks)
const completedTasks = computed(() => queueStore.completedTasks)
const hasActiveTasks = computed(() => queueStore.hasActiveTasks)
const activeTaskCount = computed(() => queueStore.activeTaskCount)
const overallProgress = computed(() => queueStore.overallProgress)

// Methods
function toggleExpand() {
  isExpanded.value = !isExpanded.value
}

function isTaskActive(task) {
  return [TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.STARTED, TaskStatus.RUNNING].includes(task.status)
}

function getTaskClass(task) {
  return {
    'task-active': isTaskActive(task),
    'task-success': task.status === TaskStatus.SUCCESS,
    'task-failure': task.status === TaskStatus.FAILURE,
    'task-cancelled': task.status === TaskStatus.CANCELLED
  }
}

function getTaskIcon(task) {
  switch (task.status) {
    case TaskStatus.SUCCESS:
      return CheckCircleIcon
    case TaskStatus.FAILURE:
    case TaskStatus.TIMEOUT:
      return AlertCircleIcon
    case TaskStatus.PENDING:
    case TaskStatus.QUEUED:
      return ClockIcon
    case TaskStatus.STARTED:
    case TaskStatus.RUNNING:
      return LoaderIcon  // 使用加载图标
    default:
      return FileTextIcon
  }
}

function getTaskName(task) {
  // 优先使用 document_name，然后是 filename，最后用 task_id 前 8 位
  return task.document_name || task.filename || task.document_id?.slice(0, 8) || task.task_id.slice(0, 8)
}

function getStatusTheme(status) {
  switch (status) {
    case TaskStatus.SUCCESS:
      return 'success'
    case TaskStatus.FAILURE:
    case TaskStatus.TIMEOUT:
      return 'danger'
    case TaskStatus.CANCELLED:
      return 'warning'
    case TaskStatus.RUNNING:
    case TaskStatus.STARTED:  // 新增
      return 'primary'
    default:
      return 'default'
  }
}

function getStatusText(status) {
  const statusMap = {
    [TaskStatus.PENDING]: '等待中',
    [TaskStatus.QUEUED]: '排队中',
    [TaskStatus.STARTED]: '处理中',  // 新增
    [TaskStatus.RUNNING]: '加载中',
    [TaskStatus.SUCCESS]: '完成',
    [TaskStatus.FAILURE]: '失败',
    [TaskStatus.CANCELLED]: '已取消',
    [TaskStatus.TIMEOUT]: '超时'
  }
  return statusMap[status] || status
}

function formatTime(task) {
  if (task.processing_time) {
    return `${task.processing_time.toFixed(1)}s`
  }
  if (task.started_at) {
    const elapsed = (Date.now() - new Date(task.started_at).getTime()) / 1000
    return `${elapsed.toFixed(0)}s`
  }
  return ''
}

async function cancelTask(taskId) {
  await queueStore.cancelTask(taskId)
}

function clearCompleted() {
  queueStore.clearCompletedTasks()
}

// Lifecycle
onMounted(() => {
  queueStore.initialize()
})

onUnmounted(() => {
  // 不要在组件卸载时清理 store，因为其他组件可能还在使用
})
</script>

<style scoped>
.loading-queue-panel {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 1000;
}

/* 悬浮按钮 */
.queue-fab {
  width: 56px;
  height: 56px;
  border-radius: 28px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s, box-shadow 0.2s;
  padding: 8px;
}

.queue-fab:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.5);
}

.fab-content {
  display: flex;
  align-items: center;
  gap: 4px;
  color: white;
}

.fab-icon {
  color: white;
}

.fab-icon.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.fab-count {
  font-size: 14px;
  font-weight: 600;
}

.fab-progress {
  width: 40px;
  margin-top: 4px;
}

.fab-progress :deep(.t-progress__bar) {
  background: rgba(255, 255, 255, 0.3);
}

.fab-progress :deep(.t-progress__inner) {
  background: white;
}

/* 展开的卡片 */
.queue-card {
  width: 360px;
  max-height: 400px;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  border-radius: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-title {
  font-weight: 600;
  font-size: 14px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 任务列表 */
.task-list {
  max-height: 280px;
  overflow-y: auto;
}

.task-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.task-item:last-child {
  border-bottom: none;
}

.task-info {
  flex: 1;
  min-width: 0;
}

.task-main {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-icon {
  flex-shrink: 0;
  color: #666;
}

.task-active .task-icon {
  color: #667eea;
}

.task-success .task-icon {
  color: #52c41a;
}

.task-failure .task-icon {
  color: #ff4d4f;
}

.task-name {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 12px;
  color: #999;
}

.task-loader {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
}

.task-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-progress {
  width: 60px;
}

.status-tag {
  flex-shrink: 0;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 32px 16px;
  color: #999;
}

.empty-icon {
  color: #d9d9d9;
  margin-bottom: 8px;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

/* 队列统计 */
.queue-stats {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}
</style>
