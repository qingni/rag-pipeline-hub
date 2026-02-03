<template>
  <div class="cache-status" :class="statusClass">
    <!-- 紧凑模式 -->
    <div v-if="compact" class="compact-view" @click="expanded = !expanded">
      <el-tooltip :content="tooltipContent" placement="top">
        <div class="compact-content">
          <el-icon :class="statusIconClass"><component :is="statusIcon" /></el-icon>
          <span class="hit-rate">{{ hitRateText }}</span>
          <el-icon class="expand-icon" :class="{ 'is-expanded': expanded }">
            <ArrowDown />
          </el-icon>
        </div>
      </el-tooltip>
    </div>
    
    <!-- 展开详情 -->
    <transition name="slide">
      <div v-if="!compact || expanded" class="detail-view">
        <div class="status-header">
          <div class="status-title">
            <el-icon :class="statusIconClass"><component :is="statusIcon" /></el-icon>
            <span>向量缓存</span>
            <el-tag :type="statusTagType" size="small" effect="light">
              {{ statusText }}
            </el-tag>
          </div>
          <el-button
            text
            size="small"
            @click="refreshStats"
            :loading="loading"
          >
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
        
        <div class="stats-grid">
          <!-- 命中率 -->
          <div class="stat-item primary">
            <div class="stat-label">命中率</div>
            <div class="stat-value">{{ hitRateText }}</div>
            <el-progress
              :percentage="hitRatePercent"
              :color="hitRateColor"
              :stroke-width="4"
              :show-text="false"
            />
          </div>
          
          <!-- 缓存条目 -->
          <div class="stat-item">
            <div class="stat-label">缓存条目</div>
            <div class="stat-value">{{ formatNumber(stats.total_entries) }}</div>
          </div>
          
          <!-- 内存使用 -->
          <div class="stat-item">
            <div class="stat-label">内存使用</div>
            <div class="stat-value">{{ memorySizeText }}</div>
          </div>
          
          <!-- 命中/未命中 -->
          <div class="stat-item">
            <div class="stat-label">命中 / 未命中</div>
            <div class="stat-value">
              <span class="hit">{{ formatNumber(stats.hit_count) }}</span>
              <span class="separator">/</span>
              <span class="miss">{{ formatNumber(stats.miss_count) }}</span>
            </div>
          </div>
        </div>
        
        <!-- 建议 -->
        <div v-if="recommendations.length > 0" class="recommendations">
          <el-icon><InfoFilled /></el-icon>
          <span>{{ recommendations[0] }}</span>
        </div>
        
        <!-- 操作按钮 -->
        <div class="actions" v-if="showActions">
          <el-popconfirm
            title="确定要清空所有缓存吗？"
            confirm-button-text="确定"
            cancel-button-text="取消"
            @confirm="clearCache"
          >
            <template #reference>
              <el-button type="danger" text size="small" :loading="clearing">
                <el-icon><Delete /></el-icon>
                清空缓存
              </el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import {
  ArrowDown,
  Refresh,
  Delete,
  InfoFilled,
  CircleCheckFilled,
  WarningFilled,
  Loading,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  /**
   * 紧凑模式
   */
  compact: {
    type: Boolean,
    default: false,
  },
  /**
   * 显示操作按钮
   */
  showActions: {
    type: Boolean,
    default: true,
  },
  /**
   * 自动刷新间隔（毫秒），0 表示不自动刷新
   */
  autoRefreshInterval: {
    type: Number,
    default: 0,
  },
})

const emit = defineEmits(['stats-updated', 'cache-cleared'])

// 状态
const loading = ref(false)
const clearing = ref(false)
const expanded = ref(false)
const stats = ref({
  total_entries: 0,
  total_size_bytes: 0,
  hit_count: 0,
  miss_count: 0,
  hit_rate: 0,
  eviction_count: 0,
})
const healthStatus = ref('warming')
const recommendations = ref([])

// 计算属性
const hitRatePercent = computed(() => {
  return Math.round(stats.value.hit_rate * 100)
})

const hitRateText = computed(() => {
  return `${hitRatePercent.value}%`
})

const hitRateColor = computed(() => {
  const rate = hitRatePercent.value
  if (rate >= 80) return '#52c41a'
  if (rate >= 50) return '#faad14'
  return '#f5222d'
})

const memorySizeText = computed(() => {
  const bytes = stats.value.total_size_bytes
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
})

const statusText = computed(() => {
  switch (healthStatus.value) {
    case 'healthy': return '正常'
    case 'warming': return '预热中'
    case 'unhealthy': return '需优化'
    case 'error': return '错误'
    default: return '未知'
  }
})

const statusTagType = computed(() => {
  switch (healthStatus.value) {
    case 'healthy': return 'success'
    case 'warming': return 'warning'
    case 'unhealthy': return 'danger'
    default: return 'info'
  }
})

const statusIcon = computed(() => {
  switch (healthStatus.value) {
    case 'healthy': return CircleCheckFilled
    case 'warming': return Loading
    case 'unhealthy': return WarningFilled
    default: return InfoFilled
  }
})

const statusIconClass = computed(() => {
  return `status-icon-${healthStatus.value}`
})

const statusClass = computed(() => {
  return `status-${healthStatus.value}`
})

const tooltipContent = computed(() => {
  return `缓存命中率: ${hitRateText.value} | 条目: ${stats.value.total_entries}`
})

// 方法
function formatNumber(num) {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
  return String(num)
}

async function refreshStats() {
  loading.value = true
  try {
    const response = await fetch('/api/v1/embedding/cache/stats')
    if (!response.ok) throw new Error('Failed to fetch stats')
    const data = await response.json()
    stats.value = data
    
    // 获取健康状态
    const healthResponse = await fetch('/api/v1/embedding/cache/health')
    if (healthResponse.ok) {
      const healthData = await healthResponse.json()
      healthStatus.value = healthData.status
      recommendations.value = healthData.recommendations || []
    }
    
    emit('stats-updated', stats.value)
  } catch (error) {
    console.error('Failed to refresh cache stats:', error)
    ElMessage.error('获取缓存状态失败')
  } finally {
    loading.value = false
  }
}

async function clearCache() {
  clearing.value = true
  try {
    const response = await fetch('/api/v1/embedding/cache/clear?confirm=true', {
      method: 'DELETE',
    })
    if (!response.ok) throw new Error('Failed to clear cache')
    const data = await response.json()
    
    ElMessage.success(`已清空 ${data.entries_removed} 条缓存`)
    emit('cache-cleared', data.entries_removed)
    
    // 刷新统计
    await refreshStats()
  } catch (error) {
    console.error('Failed to clear cache:', error)
    ElMessage.error('清空缓存失败')
  } finally {
    clearing.value = false
  }
}

// 自动刷新
let refreshTimer = null
watch(() => props.autoRefreshInterval, (interval) => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  if (interval > 0) {
    refreshTimer = setInterval(refreshStats, interval)
  }
}, { immediate: true })

// 生命周期
onMounted(() => {
  refreshStats()
})
</script>

<style scoped>
.cache-status {
  background: #fff;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  overflow: hidden;
  transition: all 0.3s ease;
}

.cache-status.status-healthy {
  border-color: #b7eb8f;
}

.cache-status.status-warming {
  border-color: #ffe58f;
}

.cache-status.status-unhealthy {
  border-color: #ffccc7;
}

/* 紧凑模式 */
.compact-view {
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
}

.compact-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hit-rate {
  font-weight: 600;
  font-size: 14px;
}

.expand-icon {
  transition: transform 0.3s ease;
}

.expand-icon.is-expanded {
  transform: rotate(180deg);
}

/* 详情视图 */
.detail-view {
  padding: 16px;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.status-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.status-icon-healthy {
  color: #52c41a;
}

.status-icon-warming {
  color: #faad14;
}

.status-icon-unhealthy {
  color: #f5222d;
}

/* 统计网格 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.stat-item {
  background: #fafafa;
  padding: 12px;
  border-radius: 6px;
}

.stat-item.primary {
  grid-column: span 2;
  background: linear-gradient(135deg, #f6ffed 0%, #fff 100%);
  border: 1px solid #b7eb8f;
}

.stat-label {
  font-size: 12px;
  color: #8c8c8c;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #262626;
}

.stat-value .hit {
  color: #52c41a;
}

.stat-value .miss {
  color: #f5222d;
}

.stat-value .separator {
  color: #d9d9d9;
  margin: 0 4px;
}

/* 建议 */
.recommendations {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  background: #fffbe6;
  border-radius: 6px;
  font-size: 13px;
  color: #ad8b00;
  margin-bottom: 12px;
}

.recommendations .el-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

/* 操作按钮 */
.actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
  border-top: 1px dashed #f0f0f0;
}

/* 动画 */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  max-height: 0;
  opacity: 0;
  padding: 0;
}

.slide-enter-to,
.slide-leave-from {
  max-height: 400px;
  opacity: 1;
}
</style>
