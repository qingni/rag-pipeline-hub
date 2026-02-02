<template>
  <div class="chunk-stats-chart">
    <!-- 概览卡片 -->
    <div class="stats-overview">
      <div class="stat-card">
        <div class="stat-icon">
          <t-icon name="layers" size="24px" />
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ statistics.total_chunks || 0 }}</div>
          <div class="stat-label">总块数</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon text">
          <t-icon name="file-text" size="24px" />
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ formatNumber(statistics.total_characters || 0) }}</div>
          <div class="stat-label">总字符数</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon avg">
          <t-icon name="chart-bar" size="24px" />
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ Math.round(statistics.avg_chunk_size || 0) }}</div>
          <div class="stat-label">平均块大小</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon range">
          <t-icon name="swap" size="24px" />
        </div>
        <div class="stat-info">
          <div class="stat-value">
            {{ statistics.min_chunk_size || 0 }} - {{ statistics.max_chunk_size || 0 }}
          </div>
          <div class="stat-label">块大小范围</div>
        </div>
      </div>
    </div>

    <!-- 父子块统计 (仅 parent_child 策略) -->
    <div v-if="statistics.parent_child_stats" class="parent-child-stats">
      <h4>父子块统计</h4>
      <div class="stats-row">
        <div class="stat-item">
          <div class="stat-item-value parent">{{ statistics.parent_child_stats.parent_count }}</div>
          <div class="stat-item-label">父块数</div>
        </div>
        <div class="stat-item">
          <div class="stat-item-value child">{{ statistics.parent_child_stats.child_count }}</div>
          <div class="stat-item-label">子块数</div>
        </div>
        <div class="stat-item">
          <div class="stat-item-value">{{ statistics.parent_child_stats.avg_children_per_parent?.toFixed(1) }}</div>
          <div class="stat-item-label">平均子块/父块</div>
        </div>
        <div class="stat-item">
          <div class="stat-item-value">{{ Math.round(statistics.parent_child_stats.avg_parent_size || 0) }}</div>
          <div class="stat-item-label">平均父块大小</div>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-container">
      <!-- 块大小分布图 -->
      <div class="chart-section">
        <h4>块大小分布</h4>
        <div class="chart-wrapper">
          <div ref="sizeChartRef" class="chart"></div>
        </div>
      </div>
      
      <!-- 类型分布图 (仅 hybrid 策略) -->
      <div v-if="hasMultipleTypes" class="chart-section">
        <h4>内容类型分布</h4>
        <div class="chart-wrapper">
          <div ref="typeChartRef" class="chart"></div>
        </div>
      </div>
      
      <!-- 标题层级分布 (仅 heading 策略) -->
      <div v-if="strategy === 'heading'" class="chart-section">
        <h4>标题层级分布</h4>
        <div class="chart-wrapper">
          <div ref="levelChartRef" class="chart"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick, onBeforeUnmount } from 'vue'
import { 
  calculateChunkStatistics, 
  groupChunksByType, 
  groupChunksByLevel,
  getChunkTypeColor,
  getHeadingLevelColor 
} from './utils/visualizerUtils'

const props = defineProps({
  chunks: {
    type: Array,
    default: () => []
  },
  parentChunks: {
    type: Array,
    default: () => []
  },
  strategy: {
    type: String,
    default: 'character'
  },
  externalStatistics: {
    type: Object,
    default: null
  }
})

// 图表引用
const sizeChartRef = ref(null)
const typeChartRef = ref(null)
const levelChartRef = ref(null)

// 图表实例
let sizeChart = null
let typeChart = null
let levelChart = null

// 计算统计信息
const statistics = computed(() => {
  // 如果有外部统计数据，使用它但可能需要补充 size_distribution
  if (props.externalStatistics) {
    const external = props.externalStatistics
    
    // 如果外部统计数据缺少 size_distribution，用本地 chunks 数据计算
    if (!external.size_distribution || external.size_distribution.length === 0) {
      const localStats = calculateChunkStatistics(props.chunks, props.parentChunks)
      return {
        ...external,
        // 补充 size_distribution（从本地计算）
        size_distribution: localStats.size_distribution,
        // 确保 parent_child_stats 结构正确
        parent_child_stats: external.parent_child_stats || (external.parent_count !== undefined ? {
          parent_count: external.parent_count,
          child_count: external.child_count || external.total_chunks,
          avg_children_per_parent: external.avg_children_per_parent,
          avg_parent_size: external.avg_parent_size || 0
        } : null)
      }
    }
    
    return external
  }
  return calculateChunkStatistics(props.chunks, props.parentChunks)
})

// 是否有多种类型
const hasMultipleTypes = computed(() => {
  const types = new Set(props.chunks.map(c => c.chunk_type || 'text'))
  return types.size > 1
})

// 格式化数字
const formatNumber = (num) => {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toLocaleString()
}

// 创建简单柱状图（纯 SVG 实现，无需 ECharts）
const createSizeChart = () => {
  if (!sizeChartRef.value) return
  
  const distribution = statistics.value.size_distribution || []
  if (distribution.length === 0) return
  
  const maxCount = Math.max(...distribution.map(d => d.count), 1)
  const width = 100 / distribution.length
  
  // 生成 SVG
  const svg = `
    <svg viewBox="0 0 400 200" class="bar-chart">
      <defs>
        <linearGradient id="barGradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" style="stop-color:#1890ff;stop-opacity:1" />
          <stop offset="100%" style="stop-color:#096dd9;stop-opacity:1" />
        </linearGradient>
      </defs>
      ${distribution.map((item, idx) => {
        const barHeight = (item.count / maxCount) * 150
        const x = idx * (400 / distribution.length) + 10
        const y = 180 - barHeight
        const barWidth = (400 / distribution.length) - 20
        return `
          <g class="bar-group">
            <rect 
              x="${x}" 
              y="${y}" 
              width="${barWidth}" 
              height="${barHeight}"
              fill="url(#barGradient)"
              rx="4"
              class="bar"
            >
              <title>${item.name}: ${item.count} 块</title>
            </rect>
            <text 
              x="${x + barWidth / 2}" 
              y="${y - 5}" 
              text-anchor="middle" 
              class="bar-value"
            >${item.count}</text>
            <text 
              x="${x + barWidth / 2}" 
              y="195" 
              text-anchor="middle" 
              class="bar-label"
            >${item.name}</text>
          </g>
        `
      }).join('')}
    </svg>
  `
  
  sizeChartRef.value.innerHTML = svg
}

// 创建类型分布图（饼图）
const createTypeChart = () => {
  if (!typeChartRef.value || !hasMultipleTypes.value) return
  
  const groups = groupChunksByType(props.chunks)
  const data = Object.entries(groups).map(([type, chunks]) => ({
    name: getTypeName(type),
    value: chunks.length,
    color: getChunkTypeColor(type)
  }))
  
  const total = data.reduce((sum, d) => sum + d.value, 0)
  let currentAngle = 0
  
  const paths = data.map((item, idx) => {
    const angle = (item.value / total) * 360
    const startAngle = currentAngle
    const endAngle = currentAngle + angle
    currentAngle = endAngle
    
    const startRad = (startAngle - 90) * Math.PI / 180
    const endRad = (endAngle - 90) * Math.PI / 180
    
    const x1 = 100 + 70 * Math.cos(startRad)
    const y1 = 100 + 70 * Math.sin(startRad)
    const x2 = 100 + 70 * Math.cos(endRad)
    const y2 = 100 + 70 * Math.sin(endRad)
    
    const largeArc = angle > 180 ? 1 : 0
    
    return `
      <path 
        d="M 100 100 L ${x1} ${y1} A 70 70 0 ${largeArc} 1 ${x2} ${y2} Z"
        fill="${item.color}"
        stroke="#fff"
        stroke-width="2"
      >
        <title>${item.name}: ${item.value} 块 (${((item.value / total) * 100).toFixed(1)}%)</title>
      </path>
    `
  }).join('')
  
  // 图例
  const legends = data.map((item, idx) => `
    <g transform="translate(210, ${30 + idx * 25})">
      <rect x="0" y="0" width="16" height="16" fill="${item.color}" rx="2"/>
      <text x="22" y="13" class="legend-text">${item.name}: ${item.value}</text>
    </g>
  `).join('')
  
  const svg = `
    <svg viewBox="0 0 350 200" class="pie-chart">
      <g transform="translate(0, 0)">
        ${paths}
      </g>
      ${legends}
    </svg>
  `
  
  typeChartRef.value.innerHTML = svg
}

// 创建标题层级分布图
const createLevelChart = () => {
  if (!levelChartRef.value || props.strategy !== 'heading') return
  
  const groups = groupChunksByLevel(props.chunks)
  const data = Object.entries(groups)
    .map(([level, chunks]) => ({
      level: parseInt(level),
      name: `H${level}`,
      value: chunks.length,
      color: getHeadingLevelColor(parseInt(level))
    }))
    .sort((a, b) => a.level - b.level)
  
  const maxCount = Math.max(...data.map(d => d.value), 1)
  
  const bars = data.map((item, idx) => {
    const barWidth = (item.value / maxCount) * 250
    const y = idx * 30 + 20
    return `
      <g class="bar-group">
        <text x="30" y="${y + 15}" text-anchor="end" class="level-label">${item.name}</text>
        <rect 
          x="40" 
          y="${y}" 
          width="${barWidth}" 
          height="22"
          fill="${item.color}"
          rx="4"
        >
          <title>${item.name}: ${item.value} 块</title>
        </rect>
        <text x="${45 + barWidth}" y="${y + 15}" class="bar-value-right">${item.value}</text>
      </g>
    `
  }).join('')
  
  const svg = `
    <svg viewBox="0 0 350 ${data.length * 30 + 40}" class="level-chart">
      ${bars}
    </svg>
  `
  
  levelChartRef.value.innerHTML = svg
}

// 类型名称映射
const getTypeName = (type) => {
  const names = {
    text: '文本',
    table: '表格',
    code: '代码',
    image: '图片'
  }
  return names[type] || type
}

// 初始化所有图表
const initCharts = () => {
  nextTick(() => {
    createSizeChart()
    createTypeChart()
    createLevelChart()
  })
}

// 销毁图表
const destroyCharts = () => {
  if (sizeChartRef.value) sizeChartRef.value.innerHTML = ''
  if (typeChartRef.value) typeChartRef.value.innerHTML = ''
  if (levelChartRef.value) levelChartRef.value.innerHTML = ''
}

// 监听数据变化
watch(
  () => [props.chunks, props.parentChunks, props.strategy, props.externalStatistics],
  () => {
    destroyCharts()
    initCharts()
  },
  { deep: true }
)

onMounted(() => {
  initCharts()
})

onBeforeUnmount(() => {
  destroyCharts()
})
</script>

<style scoped>
.chunk-stats-chart {
  padding: 16px;
}

/* 概览卡片 */
.stats-overview {
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
  background: var(--td-bg-color-container);
  border-radius: 8px;
  border: 1px solid var(--td-component-border);
}

.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  color: #fff;
}

.stat-icon.text {
  background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%);
}

.stat-icon.avg {
  background: linear-gradient(135deg, #722ed1 0%, #531dab 100%);
}

.stat-icon.range {
  background: linear-gradient(135deg, #faad14 0%, #d48806 100%);
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--td-text-color-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: var(--td-text-color-secondary);
  margin-top: 4px;
}

/* 父子块统计 */
.parent-child-stats {
  margin-bottom: 24px;
  padding: 16px;
  background: var(--td-bg-color-container);
  border-radius: 8px;
  border: 1px solid var(--td-component-border);
}

.parent-child-stats h4 {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--td-text-color-primary);
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-item {
  text-align: center;
  padding: 12px;
  background: var(--td-bg-color-page);
  border-radius: 6px;
}

.stat-item-value {
  font-size: 28px;
  font-weight: 600;
  color: var(--td-text-color-primary);
}

.stat-item-value.parent {
  color: #1890ff;
}

.stat-item-value.child {
  color: #52c41a;
}

.stat-item-label {
  font-size: 12px;
  color: var(--td-text-color-secondary);
  margin-top: 4px;
}

/* 图表区域 */
.charts-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
}

.chart-section {
  padding: 16px;
  background: var(--td-bg-color-container);
  border-radius: 8px;
  border: 1px solid var(--td-component-border);
}

.chart-section h4 {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--td-text-color-primary);
}

.chart-wrapper {
  width: 100%;
  overflow: hidden;
}

.chart {
  width: 100%;
  min-height: 200px;
}

/* SVG 图表样式 */
.chart :deep(.bar-chart),
.chart :deep(.pie-chart),
.chart :deep(.level-chart) {
  width: 100%;
  height: auto;
}

.chart :deep(.bar-value) {
  font-size: 12px;
  fill: var(--td-text-color-primary);
  font-weight: 500;
}

.chart :deep(.bar-label) {
  font-size: 11px;
  fill: var(--td-text-color-secondary);
}

.chart :deep(.bar-value-right) {
  font-size: 12px;
  fill: var(--td-text-color-primary);
  font-weight: 500;
}

.chart :deep(.level-label) {
  font-size: 13px;
  fill: var(--td-text-color-primary);
  font-weight: 500;
}

.chart :deep(.legend-text) {
  font-size: 12px;
  fill: var(--td-text-color-primary);
}

.chart :deep(.bar) {
  transition: opacity 0.2s;
  cursor: pointer;
}

.chart :deep(.bar:hover) {
  opacity: 0.8;
}

/* 响应式布局 */
@media (max-width: 768px) {
  .stats-overview {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .charts-container {
    grid-template-columns: 1fr;
  }
}
</style>
