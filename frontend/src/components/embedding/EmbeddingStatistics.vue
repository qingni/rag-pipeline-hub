<template>
  <div class="embedding-statistics">
    <!-- 标题 -->
    <div class="stats-header">
      <h3>向量化统计</h3>
      <div class="header-actions">
        <el-button text size="small" @click="exportData">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
      </div>
    </div>
    
    <!-- 概览卡片 -->
    <div class="overview-cards">
      <div class="stat-card success">
        <div class="card-icon">
          <el-icon><CircleCheckFilled /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-value">{{ stats.successful_count }}</div>
          <div class="card-label">成功</div>
        </div>
      </div>
      
      <div class="stat-card danger">
        <div class="card-icon">
          <el-icon><CircleCloseFilled /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-value">{{ stats.failed_count }}</div>
          <div class="card-label">失败</div>
        </div>
      </div>
      
      <div class="stat-card info">
        <div class="card-icon">
          <el-icon><Timer /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-value">{{ formatDuration(stats.processing_time_ms) }}</div>
          <div class="card-label">耗时</div>
        </div>
      </div>
      
      <div class="stat-card warning">
        <div class="card-icon">
          <el-icon><Coin /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-value">{{ stats.cache_hit_rate || '0%' }}</div>
          <div class="card-label">缓存命中</div>
        </div>
      </div>
    </div>
    
    <!-- 图表区域 -->
    <div class="charts-container">
      <!-- 成功率饼图 -->
      <div class="chart-item">
        <div class="chart-title">处理结果分布</div>
        <div class="pie-chart" ref="pieChartRef"></div>
      </div>
      
      <!-- 处理时间柱状图 -->
      <div class="chart-item">
        <div class="chart-title">分块处理时间分布</div>
        <div class="bar-chart" ref="barChartRef"></div>
      </div>
    </div>
    
    <!-- 详细统计 -->
    <div class="detail-stats">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="模型">
          {{ stats.model || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="向量维度">
          {{ stats.dimension || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="总分块数">
          {{ stats.total_chunks || 0 }}
        </el-descriptions-item>
        <el-descriptions-item label="平均处理速度">
          {{ formatSpeed(stats.avg_speed) }}
        </el-descriptions-item>
        <el-descriptions-item label="重试次数">
          {{ stats.retry_count || 0 }}
        </el-descriptions-item>
        <el-descriptions-item label="速率限制次数">
          {{ stats.rate_limit_hits || 0 }}
        </el-descriptions-item>
        <el-descriptions-item label="开始时间">
          {{ formatTime(stats.started_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="完成时间">
          {{ formatTime(stats.completed_at) }}
        </el-descriptions-item>
      </el-descriptions>
    </div>
    
    <!-- 分块类型统计 -->
    <div class="chunk-type-stats" v-if="chunkTypeData.length > 0">
      <div class="section-title">分块类型统计</div>
      <div class="type-bars">
        <div 
          v-for="item in chunkTypeData" 
          :key="item.type"
          class="type-bar-item"
        >
          <div class="type-label">{{ item.label }}</div>
          <div class="type-bar">
            <div 
              class="type-bar-fill"
              :style="{ width: `${item.percentage}%`, backgroundColor: item.color }"
            ></div>
          </div>
          <div class="type-value">{{ item.count }} ({{ item.percentage.toFixed(1) }}%)</div>
        </div>
      </div>
    </div>
    
    <!-- 失败详情 -->
    <div class="failure-details" v-if="stats.failures && stats.failures.length > 0">
      <div class="section-title">
        <el-icon><WarningFilled /></el-icon>
        失败详情
      </div>
      <el-table :data="stats.failures" size="small" max-height="200">
        <el-table-column prop="index" label="序号" width="60" />
        <el-table-column prop="text_preview" label="内容预览" show-overflow-tooltip />
        <el-table-column prop="error_type" label="错误类型" width="140">
          <template #default="{ row }">
            <el-tag type="danger" size="small">{{ row.error_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" show-overflow-tooltip />
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import {
  Download,
  CircleCheckFilled,
  CircleCloseFilled,
  Timer,
  Coin,
  WarningFilled,
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

const props = defineProps({
  /**
   * 统计数据
   */
  stats: {
    type: Object,
    default: () => ({}),
  },
  /**
   * 分块详情（用于生成分布图）
   */
  chunks: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['export'])

// 图表引用
const pieChartRef = ref(null)
const barChartRef = ref(null)
let pieChart = null
let barChart = null

// 分块类型数据
const chunkTypeData = computed(() => {
  if (!props.chunks || props.chunks.length === 0) return []
  
  const typeCounts = {}
  props.chunks.forEach(chunk => {
    const type = chunk.chunk_type || 'text'
    typeCounts[type] = (typeCounts[type] || 0) + 1
  })
  
  const typeColors = {
    text: '#1890ff',
    image: '#52c41a',
    table: '#faad14',
    code: '#722ed1',
    other: '#8c8c8c',
  }
  
  const typeLabels = {
    text: '文本',
    image: '图片',
    table: '表格',
    code: '代码',
    other: '其他',
  }
  
  const total = props.chunks.length
  return Object.entries(typeCounts).map(([type, count]) => ({
    type,
    label: typeLabels[type] || type,
    count,
    percentage: (count / total) * 100,
    color: typeColors[type] || '#8c8c8c',
  })).sort((a, b) => b.count - a.count)
})

// 方法
function formatDuration(ms) {
  if (!ms) return '-'
  if (ms < 1000) return `${ms.toFixed(0)}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}min`
}

function formatSpeed(speed) {
  if (!speed) return '-'
  return `${speed.toFixed(1)} 个/秒`
}

function formatTime(timestamp) {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleString('zh-CN')
}

function initPieChart() {
  if (!pieChartRef.value) return
  
  if (!pieChart) {
    pieChart = echarts.init(pieChartRef.value)
  }
  
  const successCount = props.stats.successful_count || 0
  const failedCount = props.stats.failed_count || 0
  const cachedCount = props.stats.cached_count || 0
  
  pieChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 4,
        borderColor: '#fff',
        borderWidth: 2,
      },
      label: {
        show: false,
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 14,
          fontWeight: 'bold',
        },
      },
      data: [
        { value: successCount - cachedCount, name: '新计算', itemStyle: { color: '#52c41a' } },
        { value: cachedCount, name: '缓存命中', itemStyle: { color: '#1890ff' } },
        { value: failedCount, name: '失败', itemStyle: { color: '#f5222d' } },
      ].filter(d => d.value > 0),
    }],
  })
}

function initBarChart() {
  if (!barChartRef.value || !props.chunks || props.chunks.length === 0) return
  
  if (!barChart) {
    barChart = echarts.init(barChartRef.value)
  }
  
  // 生成处理时间分布数据
  const times = props.chunks
    .map(c => c.processing_time_ms || 0)
    .filter(t => t > 0)
  
  if (times.length === 0) {
    barChart.setOption({
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center',
        textStyle: { color: '#8c8c8c', fontSize: 14 },
      },
    })
    return
  }
  
  // 分桶统计
  const buckets = [
    { label: '<10ms', min: 0, max: 10, count: 0 },
    { label: '10-50ms', min: 10, max: 50, count: 0 },
    { label: '50-100ms', min: 50, max: 100, count: 0 },
    { label: '100-500ms', min: 100, max: 500, count: 0 },
    { label: '>500ms', min: 500, max: Infinity, count: 0 },
  ]
  
  times.forEach(t => {
    for (const bucket of buckets) {
      if (t >= bucket.min && t < bucket.max) {
        bucket.count++
        break
      }
    }
  })
  
  barChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    xAxis: {
      type: 'category',
      data: buckets.map(b => b.label),
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: '分块数',
    },
    series: [{
      type: 'bar',
      data: buckets.map(b => b.count),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#1890ff' },
          { offset: 1, color: '#69c0ff' },
        ]),
        borderRadius: [4, 4, 0, 0],
      },
      barWidth: '60%',
    }],
    grid: {
      left: '10%',
      right: '5%',
      top: '15%',
      bottom: '15%',
    },
  })
}

function exportData() {
  const exportObj = {
    stats: props.stats,
    chunks: props.chunks,
    exportedAt: new Date().toISOString(),
  }
  
  const blob = new Blob([JSON.stringify(exportObj, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `embedding-stats-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('导出成功')
  emit('export', exportObj)
}

// 监听数据变化
watch(() => props.stats, () => {
  nextTick(() => {
    initPieChart()
    initBarChart()
  })
}, { deep: true, immediate: true })

watch(() => props.chunks, () => {
  nextTick(() => {
    initBarChart()
  })
}, { deep: true })

onMounted(() => {
  nextTick(() => {
    initPieChart()
    initBarChart()
  })
})
</script>

<style scoped>
.embedding-statistics {
  background: #fff;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  padding: 20px;
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.stats-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

/* 概览卡片 */
.overview-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 8px;
  background: #fafafa;
}

.stat-card.success {
  background: linear-gradient(135deg, #f6ffed 0%, #fff 100%);
  border: 1px solid #b7eb8f;
}

.stat-card.danger {
  background: linear-gradient(135deg, #fff1f0 0%, #fff 100%);
  border: 1px solid #ffa39e;
}

.stat-card.info {
  background: linear-gradient(135deg, #e6f7ff 0%, #fff 100%);
  border: 1px solid #91d5ff;
}

.stat-card.warning {
  background: linear-gradient(135deg, #fffbe6 0%, #fff 100%);
  border: 1px solid #ffe58f;
}

.card-icon {
  font-size: 32px;
}

.stat-card.success .card-icon {
  color: #52c41a;
}

.stat-card.danger .card-icon {
  color: #f5222d;
}

.stat-card.info .card-icon {
  color: #1890ff;
}

.stat-card.warning .card-icon {
  color: #faad14;
}

.card-value {
  font-size: 24px;
  font-weight: 700;
  color: #262626;
}

.card-label {
  font-size: 12px;
  color: #8c8c8c;
}

/* 图表区域 */
.charts-container {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.chart-item {
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
}

.chart-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 12px;
  color: #595959;
}

.pie-chart,
.bar-chart {
  height: 200px;
}

/* 详细统计 */
.detail-stats {
  margin-bottom: 24px;
}

/* 分块类型统计 */
.chunk-type-stats {
  margin-bottom: 24px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 12px;
  color: #595959;
}

.type-bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.type-bar-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.type-label {
  width: 50px;
  font-size: 13px;
  color: #595959;
}

.type-bar {
  flex: 1;
  height: 16px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.type-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.type-value {
  width: 80px;
  font-size: 12px;
  color: #8c8c8c;
  text-align: right;
}

/* 失败详情 */
.failure-details {
  background: #fff1f0;
  border: 1px solid #ffa39e;
  border-radius: 8px;
  padding: 16px;
}

.failure-details .section-title {
  color: #cf1322;
}
</style>
