/**
 * Loading Queue Store - 管理多任务加载队列
 * 
 * 功能：
 * 1. 多任务状态管理
 * 2. 批量状态轮询（减少请求数）
 * 3. 任务进度跟踪
 * 4. 完成通知
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient, { pollingClient } from '../services/api'

// 任务状态枚举
export const TaskStatus = {
  PENDING: 'pending',
  QUEUED: 'queued',
  STARTED: 'started',   // Docling Serve 返回的 "已开始" 状态
  RUNNING: 'running',
  SUCCESS: 'success',
  FAILURE: 'failure',
  CANCELLED: 'cancelled',
  TIMEOUT: 'timeout'
}

// 活跃状态集合（需要继续轮询的状态）
const ACTIVE_STATUSES = new Set([
  TaskStatus.PENDING, 
  TaskStatus.QUEUED, 
  TaskStatus.STARTED,   // 新增
  TaskStatus.RUNNING
])

export const useLoadingQueueStore = defineStore('loadingQueue', () => {
  // ==================== State ====================
  
  // 任务映射：task_id -> task
  const tasks = ref(new Map())
  
  // 队列统计信息
  const queueStats = ref({
    total_tasks: 0,
    status_counts: {},
    category_counts: {}
  })
  
  // 轮询状态
  const isPolling = ref(false)
  const pollingInterval = ref(null)
  const pollIntervalMs = ref(3000) // 3秒轮询一次
  
  // 防止并发轮询
  const isPollingInProgress = ref(false)
  
  // 错误状态
  const error = ref(null)
  
  // ==================== Computed ====================
  
  // 所有任务列表（按创建时间倒序）
  const taskList = computed(() => {
    return Array.from(tasks.value.values())
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  })
  
  // 活跃任务（pending, queued, running）
  const activeTasks = computed(() => {
    return taskList.value.filter(t => ACTIVE_STATUSES.has(t.status))
  })
  
  // 已完成任务
  const completedTasks = computed(() => {
    return taskList.value.filter(t => !ACTIVE_STATUSES.has(t.status))
  })
  
  // 是否有活跃任务
  const hasActiveTasks = computed(() => activeTasks.value.length > 0)
  
  // 活跃任务数量
  const activeTaskCount = computed(() => activeTasks.value.length)
  
  // 总体进度（所有活跃任务的平均进度）
  const overallProgress = computed(() => {
    if (activeTasks.value.length === 0) return 100
    const totalProgress = activeTasks.value.reduce((sum, t) => sum + (t.progress || 0), 0)
    return Math.round(totalProgress / activeTasks.value.length)
  })
  
  // ==================== Actions ====================
  
  /**
   * 添加任务到队列
   */
  function addTask(task) {
    console.log('[LoadingQueue] addTask 被调用:', {
      task_id: task.task_id?.slice(0, 8),
      external_task_id: task.external_task_id?.slice(0, 8),
      status: task.status
    })
    
    const newMap = new Map(tasks.value)
    newMap.set(task.task_id, {
      ...task,
      addedAt: new Date().toISOString()
    })
    tasks.value = newMap  // 强制触发响应式更新
    
    // 如果有活跃任务且未开始轮询，启动轮询
    const isActive = ACTIVE_STATUSES.has(task.status)
    console.log('[LoadingQueue] 任务状态检查:', {
      status: task.status,
      isActive,
      isPolling: isPolling.value,
      willStartPolling: isActive && !isPolling.value
    })
    
    if (isActive && !isPolling.value) {
      startPolling()
    }
  }
  
  /**
   * 更新任务状态
   */
  function updateTask(taskId, updates) {
    const task = tasks.value.get(taskId)
    if (task) {
      console.log('[LoadingQueue] updateTask:', {
        taskId: taskId?.slice(0, 8),
        oldStatus: task.status,
        newStatus: updates.status,
        oldProgress: task.progress,
        newProgress: updates.progress
      })
      
      // 检查是否有实际变化
      const hasChange = task.status !== updates.status || task.progress !== updates.progress
      
      // 更新任务，确保成功状态的进度为 100%
      const updatedTask = { ...task, ...updates }
      if (updatedTask.status === TaskStatus.SUCCESS) {
        updatedTask.progress = 100
      }
      
      // 使用新 Map 强制触发响应式更新
      const newMap = new Map(tasks.value)
      newMap.set(taskId, updatedTask)
      tasks.value = newMap
      
      console.log('[LoadingQueue] updateTask 完成:', {
        taskId: taskId?.slice(0, 8),
        hasChange,
        finalStatus: updatedTask.status,
        finalProgress: updatedTask.progress,
        tasksCount: tasks.value.size
      })
    } else {
      console.warn('[LoadingQueue] updateTask: 任务不存在:', taskId?.slice(0, 8))
    }
  }
  
  /**
   * 移除任务
   */
  function removeTask(taskId) {
    const newMap = new Map(tasks.value)
    newMap.delete(taskId)
    tasks.value = newMap  // 强制触发响应式更新
  }
  
  /**
   * 清除已完成的任务
   */
  function clearCompletedTasks() {
    const newMap = new Map()
    for (const [taskId, task] of tasks.value.entries()) {
      if (ACTIVE_STATUSES.has(task.status)) {
        newMap.set(taskId, task)
      }
    }
    tasks.value = newMap  // 强制触发响应式更新
  }
  
  /**
   * 批量获取任务状态
   */
  async function fetchBatchStatus(taskIds) {
    if (taskIds.length === 0) return {}
    
    try {
      const response = await apiClient.post('/processing/load/queue/batch-status', {
        task_ids: taskIds
      })
      
      if (response.success) {
        const statuses = response.data.statuses
        
        // 更新本地状态
        for (const [taskId, status] of Object.entries(statuses)) {
          updateTask(taskId, status)
          
          // 触发完成事件
          if (status.status === TaskStatus.SUCCESS) {
            emitTaskComplete(taskId, status)
          } else if (status.status === TaskStatus.FAILURE) {
            emitTaskError(taskId, status)
          }
        }
        
        return statuses
      }
    } catch (err) {
      console.error('Failed to fetch batch status:', err)
      error.value = err.message
    }
    
    return {}
  }
  
  /**
   * 获取队列统计信息
   */
  async function fetchQueueStats() {
    try {
      const response = await apiClient.get('/processing/load/queue/stats')
      
      if (response.success) {
        queueStats.value = response.data
      }
    } catch (err) {
      console.error('Failed to fetch queue stats:', err)
    }
  }
  
  /**
   * 获取单个任务状态（从后端数据库查询异步任务）
   * 
   * 增加超时重试机制：
   * - 超时时自动重试一次
   * - 连续超时后降低轮询频率
   */
  async function fetchTaskStatus(taskId) {
    console.log('[LoadingQueue] fetchTaskStatus 被调用:', taskId?.slice(0, 8))
    
    // 最多重试 2 次（包括首次请求）
    const maxRetries = 2
    let lastError = null
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        // 使用 pollingClient（10秒超时）
        const response = await pollingClient.get(`/processing/load/task/${taskId}/status`)
        
        console.log('[LoadingQueue] fetchTaskStatus 响应:', response)
        
        if (response.success) {
          const status = response.data
          updateTask(taskId, status)
          
          // 触发完成事件
          if (status.status === TaskStatus.SUCCESS) {
            emitTaskComplete(taskId, status)
          } else if (status.status === TaskStatus.FAILURE) {
            emitTaskError(taskId, status)
          }
          
          return status
        }
      } catch (err) {
        lastError = err
        console.warn(`[LoadingQueue] fetchTaskStatus 第 ${attempt} 次尝试失败:`, err.message)
        
        // 如果是超时且还有重试机会，等待 1 秒后重试
        if (err.isTimeout && attempt < maxRetries) {
          await new Promise(resolve => setTimeout(resolve, 1000))
          continue
        }
        
        // 不是超时或已用完重试次数，跳出循环
        break
      }
    }
    
    // 所有重试都失败了
    console.error('[LoadingQueue] fetchTaskStatus 最终失败:', lastError?.message)
    error.value = lastError?.message
    
    return null
  }
  
  /**
   * 执行一次轮询
   */
  async function performPoll() {
    // 防止并发轮询（前一次还没完成）
    if (isPollingInProgress.value) {
      console.log('[LoadingQueue] 上一次轮询尚未完成，跳过本次')
      return
    }
    
    // 获取活跃任务 ID（在设置 isPollingInProgress 之前获取快照）
    const activeTasksSnapshot = activeTasks.value.slice()
    const activeIds = activeTasksSnapshot.map(t => t.task_id)
    
    console.log('[LoadingQueue] performPoll 开始:', {
      activeCount: activeIds.length,
      tasks: activeTasksSnapshot.map(t => ({
        id: t.task_id?.slice(0, 8),
        status: t.status,
        progress: t.progress
      }))
    })
    
    if (activeIds.length === 0) {
      console.log('[LoadingQueue] 没有活跃任务，停止轮询')
      stopPolling()
      return
    }
    
    isPollingInProgress.value = true
    
    try {
      // 分别处理本地队列任务和异步任务
      const localTaskIds = []
      const asyncTaskIds = []
      
      for (const task of activeTasksSnapshot) {
        if (task.external_task_id) {
          asyncTaskIds.push(task.task_id)
        } else {
          localTaskIds.push(task.task_id)
        }
      }
      
      console.log('[LoadingQueue] 轮询任务分类:', { 
        local: localTaskIds.length, 
        async: asyncTaskIds.length
      })
      
      // 批量获取本地任务状态
      if (localTaskIds.length > 0) {
        await fetchBatchStatus(localTaskIds)
      }
      
      // 并行获取异步任务状态（改为并行提高响应速度）
      if (asyncTaskIds.length > 0) {
        const promises = asyncTaskIds.map(taskId => fetchTaskStatus(taskId))
        await Promise.all(promises)
      }
      
      console.log('[LoadingQueue] performPoll 完成')
    } catch (err) {
      console.error('[LoadingQueue] performPoll 错误:', err)
    } finally {
      isPollingInProgress.value = false
    }
  }
  
  /**
   * 启动轮询
   */
  function startPolling() {
    if (isPolling.value) return
    
    isPolling.value = true
    console.log('[LoadingQueue] 启动轮询')
    
    // 立即执行第一次轮询
    performPoll()
    
    // 然后每隔 pollIntervalMs 执行一次
    pollingInterval.value = setInterval(performPoll, pollIntervalMs.value)
  }
  
  /**
   * 停止轮询
   */
  function stopPolling() {
    if (pollingInterval.value) {
      clearInterval(pollingInterval.value)
      pollingInterval.value = null
    }
    isPolling.value = false
  }
  
  /**
   * 暂停轮询（用于文件上传期间减少并发请求）
   */
  function pausePolling() {
    if (pollingInterval.value) {
      clearInterval(pollingInterval.value)
      pollingInterval.value = null
      console.log('[LoadingQueue] 轮询已暂停')
    }
  }
  
  /**
   * 恢复轮询
   */
  function resumePolling() {
    if (isPolling.value && !pollingInterval.value && hasActiveTasks.value) {
      pollingInterval.value = setInterval(performPoll, pollIntervalMs.value)
      console.log('[LoadingQueue] 轮询已恢复')
    }
  }
  
  /**
   * 取消任务
   * @param {string} taskId - 任务 ID
   * @param {boolean} forceRemove - 是否强制从本地队列移除（即使后端取消失败）
   */
  async function cancelTask(taskId, forceRemove = true) {
    let serverCancelled = false
    
    try {
      const response = await apiClient.post(`/processing/load/task/${taskId}/cancel`)
      
      if (response.success) {
        serverCancelled = true
      }
    } catch (err) {
      // 404 表示任务在后端不存在，可以安全地从本地移除
      // 其他错误也记录日志，但如果 forceRemove 为 true，仍然移除本地任务
      console.warn('Cancel task request failed:', err.message)
      
      // 如果是 404，认为后端已经没有这个任务了
      if (err.response?.status === 404 || err.message?.includes('404')) {
        console.info('Task not found on server, removing from local queue')
        serverCancelled = true  // 任务不存在也算"取消成功"
      }
    }
    
    // 根据结果更新本地状态
    if (serverCancelled || forceRemove) {
      // 先标记为已取消
      updateTask(taskId, { status: TaskStatus.CANCELLED })
      // 然后从队列中移除
      removeTask(taskId)
      return true
    }
    
    return false
  }
  
  // ==================== Events ====================
  
  // 任务完成回调
  const completionCallbacks = new Map()
  
  /**
   * 注册任务完成回调
   */
  function onTaskComplete(taskId, callback) {
    if (!completionCallbacks.has(taskId)) {
      completionCallbacks.set(taskId, [])
    }
    completionCallbacks.get(taskId).push(callback)
  }
  
  /**
   * 触发任务完成事件
   */
  function emitTaskComplete(taskId, result) {
    const callbacks = completionCallbacks.get(taskId) || []
    for (const callback of callbacks) {
      try {
        callback(result)
      } catch (err) {
        console.error('Callback error:', err)
      }
    }
    completionCallbacks.delete(taskId)
    
    // 发送全局事件
    window.dispatchEvent(new CustomEvent('loading-task-complete', {
      detail: { taskId, result }
    }))
  }
  
  /**
   * 触发任务错误事件
   */
  function emitTaskError(taskId, error) {
    window.dispatchEvent(new CustomEvent('loading-task-error', {
      detail: { taskId, error }
    }))
  }
  
  // ==================== Lifecycle ====================
  
  /**
   * 初始化：加载活跃任务
   */
  async function initialize() {
    try {
      const response = await apiClient.get('/processing/load/queue/active')
      
      if (response.success && response.data.tasks) {
        for (const task of response.data.tasks) {
          addTask(task)
        }
      }
      
      await fetchQueueStats()
      
      // 如果有活跃任务，启动轮询
      if (hasActiveTasks.value) {
        startPolling()
      }
    } catch (err) {
      console.error('Failed to initialize loading queue:', err)
    }
  }
  
  /**
   * 清理
   */
  function cleanup() {
    stopPolling()
    tasks.value.clear()
    completionCallbacks.clear()
  }
  
  return {
    // State
    tasks,
    queueStats,
    isPolling,
    error,
    
    // Computed
    taskList,
    activeTasks,
    completedTasks,
    hasActiveTasks,
    activeTaskCount,
    overallProgress,
    
    // Actions
    addTask,
    updateTask,
    removeTask,
    clearCompletedTasks,
    fetchBatchStatus,
    fetchQueueStats,
    fetchTaskStatus,
    startPolling,
    stopPolling,
    pausePolling,
    resumePolling,
    cancelTask,
    onTaskComplete,
    initialize,
    cleanup
  }
})
