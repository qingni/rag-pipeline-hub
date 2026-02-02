<template>
  <div class="hybrid-visualizer">
    <!-- 类型分布概览 -->
    <div class="type-overview">
      <div class="overview-header">
        <h4>内容类型分布</h4>
        <span class="overview-total">共 {{ chunks.length }} 个块</span>
      </div>
      
      <div class="type-cards">
        <div 
          v-for="(group, type) in groupedChunks" 
          :key="type"
          class="type-card"
          :class="{ active: selectedType === type }"
          @click="toggleType(type)"
        >
          <div class="type-icon" :style="{ backgroundColor: getTypeColor(type) }">
            <t-icon :name="getTypeIcon(type)" size="20px" />
          </div>
          <div class="type-info">
            <div class="type-name">{{ getTypeName(type) }}</div>
            <div class="type-count">{{ group.length }} 个块</div>
          </div>
          <div class="type-percentage">
            {{ getTypePercentage(group.length) }}%
          </div>
        </div>
      </div>
    </div>
    
    <!-- 文档时间轴视图 -->
    <div class="timeline-section">
      <h4>文档结构时间轴</h4>
      <div class="timeline-container">
        <div class="timeline-bar">
          <div
            v-for="(chunk, index) in chunks"
            :key="getChunkId(chunk, index)"
            class="timeline-segment"
            :style="getTimelineSegmentStyle(chunk, index)"
            :class="{ 
              selected: selectedChunkId === getChunkId(chunk, index),
              filtered: selectedType && chunk.chunk_type !== selectedType
            }"
            @click="selectChunk(chunk)"
            @mouseenter="hoveredChunk = chunk"
            @mouseleave="hoveredChunk = null"
          >
            <t-popup 
              :content="getChunkTooltip(chunk, index)"
              placement="top"
            >
              <div class="segment-inner"></div>
            </t-popup>
          </div>
        </div>
        <div class="timeline-legend">
          <span>文档开头</span>
          <span>文档结尾</span>
        </div>
      </div>
    </div>
    
    <!-- 按类型分组展示 -->
    <div class="type-groups">
      <t-collapse v-model="expandedTypes" :expand-mutex="false">
        <t-collapse-panel 
          v-for="(group, type) in groupedChunks" 
          :key="type"
          :value="type"
          :header-right-content="group.length + ' 个'"
        >
          <template #header>
            <div class="group-header">
              <div 
                class="group-icon" 
                :style="{ backgroundColor: getTypeColor(type) }"
              >
                <t-icon :name="getTypeIcon(type)" size="16px" />
              </div>
              <span class="group-name">{{ getTypeName(type) }}</span>
            </div>
          </template>
          
          <div class="group-content">
            <!-- 类型统计 -->
            <div class="type-stats">
              <div class="stat-item">
                <span class="stat-label">总字符数</span>
                <span class="stat-value">{{ getGroupCharCount(group) }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">平均大小</span>
                <span class="stat-value">{{ getGroupAvgSize(group) }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">最小/最大</span>
                <span class="stat-value">{{ getGroupSizeRange(group) }}</span>
              </div>
            </div>
            
            <!-- 块列表 -->
            <div class="chunk-items">
              <div
                v-for="(chunk, idx) in group"
                :key="getChunkId(chunk, idx)"
                class="chunk-item"
                :class="{ selected: selectedChunkId === getChunkId(chunk, idx) }"
                @click="selectChunk(chunk)"
              >
                <div class="item-header">
                  <span class="item-index">#{{ chunk.sequence_number + 1 || idx + 1 }}</span>
                  <t-tag size="small" theme="primary" variant="light">
                    {{ getChunkSize(chunk) }} 字符
                  </t-tag>
                  <!-- 使用的分块策略 -->
                  <t-tag 
                    v-if="chunk.metadata?.strategy || chunk.metadata?.chunking_method" 
                    size="small"
                    variant="outline"
                  >
                    {{ chunk.metadata?.strategy || chunk.metadata?.chunking_method }}
                  </t-tag>
                </div>
                
                <!-- 表格元数据 -->
                <div v-if="type === 'table' && chunk.metadata" class="item-meta">
                  <span v-if="chunk.metadata.row_count">
                    {{ chunk.metadata.row_count }} 行 × {{ chunk.metadata.column_count || '?' }} 列
                  </span>
                  <span v-if="chunk.metadata.has_header">有表头</span>
                </div>
                
                <!-- 代码元数据 -->
                <div v-if="type === 'code' && chunk.metadata" class="item-meta">
                  <t-tag v-if="chunk.metadata.language" size="small" variant="light">
                    {{ chunk.metadata.language }}
                  </t-tag>
                  <span v-if="chunk.metadata.function_name">
                    函数: {{ chunk.metadata.function_name }}
                  </span>
                </div>
                
                <div class="item-preview">
                  {{ getPreview(chunk) }}
                </div>
              </div>
            </div>
          </div>
        </t-collapse-panel>
      </t-collapse>
    </div>
    
    <!-- 类型分布饼图 -->
    <div class="pie-chart-section">
      <h4>类型占比分析</h4>
      <div class="pie-chart-container">
        <div class="pie-chart" ref="pieChartRef"></div>
        <div class="pie-legend">
          <div 
            v-for="(group, type) in groupedChunks" 
            :key="type"
            class="pie-legend-item"
          >
            <span 
              class="legend-color" 
              :style="{ backgroundColor: getTypeColor(type) }"
            ></span>
            <span class="legend-label">{{ getTypeName(type) }}</span>
            <span class="legend-value">
              {{ group.length }} 块 ({{ getTypePercentage(group.length) }}%)
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { groupChunksByType, getChunkTypeColor } from './utils/visualizerUtils'

const props = defineProps({
  chunks: {
    type: Array,
    default: () => []
  },
  statistics: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['chunk-click'])

// 状态
const expandedTypes = ref(['text', 'table', 'code', 'image'])
const selectedType = ref(null)
const selectedChunkId = ref(null)
const hoveredChunk = ref(null)
const pieChartRef = ref(null)

// 按类型分组
const groupedChunks = computed(() => {
  return groupChunksByType(props.chunks)
})

// 总字符数
const totalCharacters = computed(() => {
  if (!props.chunks.length) return 0
  const lastChunk = props.chunks[props.chunks.length - 1]
  return lastChunk?.metadata?.end_position || 
    lastChunk?.end_position || 
    props.chunks.reduce((sum, c) => sum + getChunkSize(c), 0)
})

// 类型配置
const typeConfig = {
  text: { name: '文本', icon: 'file-text', color: '#1890ff' },
  table: { name: '表格', icon: 'table', color: '#52c41a' },
  code: { name: '代码', icon: 'code', color: '#722ed1' },
  image: { name: '图片', icon: 'image', color: '#faad14' }
}

const getTypeName = (type) => typeConfig[type]?.name || type
const getTypeIcon = (type) => typeConfig[type]?.icon || 'file'
const getTypeColor = (type) => typeConfig[type]?.color || '#999'

// 获取类型占比
const getTypePercentage = (count) => {
  if (!props.chunks.length) return 0
  return Math.round((count / props.chunks.length) * 100)
}

// 获取块ID
const getChunkId = (chunk, index) => {
  return chunk?.id || chunk?.metadata?.chunk_id || `chunk_${index}`
}

// 获取块大小
const getChunkSize = (chunk) => {
  return chunk?.metadata?.char_count || chunk?.token_count || chunk?.content?.length || 0
}

// 获取预览
const getPreview = (chunk, maxLength = 120) => {
  const content = chunk?.content || ''
  return content.length > maxLength ? content.slice(0, maxLength) + '...' : content
}

// 获取分组字符数
const getGroupCharCount = (group) => {
  const total = group.reduce((sum, c) => sum + getChunkSize(c), 0)
  return total.toLocaleString()
}

// 获取分组平均大小
const getGroupAvgSize = (group) => {
  if (!group.length) return 0
  const total = group.reduce((sum, c) => sum + getChunkSize(c), 0)
  return Math.round(total / group.length)
}

// 获取分组大小范围
const getGroupSizeRange = (group) => {
  if (!group.length) return '0 - 0'
  const sizes = group.map(c => getChunkSize(c))
  return `${Math.min(...sizes)} - ${Math.max(...sizes)}`
}

// 获取时间轴段样式
const getTimelineSegmentStyle = (chunk, index) => {
  const start = chunk?.metadata?.start_position || chunk?.start_position || 0
  const end = chunk?.metadata?.end_position || chunk?.end_position || 0
  const total = totalCharacters.value || 1
  
  const width = Math.max(((end - start) / total) * 100, 0.5)
  const left = (start / total) * 100
  const color = getTypeColor(chunk.chunk_type || 'text')
  
  return {
    width: `${width}%`,
    left: `${left}%`,
    backgroundColor: color
  }
}

// 获取块提示
const getChunkTooltip = (chunk, index) => {
  const type = getTypeName(chunk.chunk_type || 'text')
  const size = getChunkSize(chunk)
  return `${type} #${index + 1}: ${size} 字符`
}

// 切换类型筛选
const toggleType = (type) => {
  selectedType.value = selectedType.value === type ? null : type
}

// 选中块
const selectChunk = (chunk) => {
  selectedChunkId.value = getChunkId(chunk, 0)
  emit('chunk-click', chunk)
}

// 创建饼图
const createPieChart = () => {
  if (!pieChartRef.value) return
  
  const groups = groupedChunks.value
  const data = Object.entries(groups).map(([type, chunks]) => ({
    name: getTypeName(type),
    value: chunks.length,
    color: getTypeColor(type)
  }))
  
  const total = data.reduce((sum, d) => sum + d.value, 0)
  if (total === 0) return
  
  let currentAngle = -90
  const paths = []
  const cx = 80
  const cy = 80
  const r = 60
  
  data.forEach((item, idx) => {
    const angle = (item.value / total) * 360
    const startAngle = currentAngle
    const endAngle = currentAngle + angle
    currentAngle = endAngle
    
    const startRad = startAngle * Math.PI / 180
    const endRad = endAngle * Math.PI / 180
    
    const x1 = cx + r * Math.cos(startRad)
    const y1 = cy + r * Math.sin(startRad)
    const x2 = cx + r * Math.cos(endRad)
    const y2 = cy + r * Math.sin(endRad)
    
    const largeArc = angle > 180 ? 1 : 0
    
    paths.push(`
      <path 
        d="M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z"
        fill="${item.color}"
        stroke="#fff"
        stroke-width="2"
      >
        <title>${item.name}: ${item.value} 块 (${Math.round((item.value / total) * 100)}%)</title>
      </path>
    `)
  })
  
  const svg = `
    <svg viewBox="0 0 160 160" class="pie-svg">
      ${paths.join('')}
    </svg>
  `
  
  pieChartRef.value.innerHTML = svg
}

// 监听数据变化
watch(
  () => props.chunks,
  () => {
    nextTick(() => {
      createPieChart()
    })
  },
  { immediate: true, deep: true }
)

onMounted(() => {
  createPieChart()
})
</script>

<style scoped>
.hybrid-visualizer {
  padding: 16px;
}

/* 类型概览 */
.type-overview {
  margin-bottom: 24px;
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.overview-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--td-text-color-primary);
}

.overview-total {
  font-size: 13px;
  color: var(--td-text-color-secondary);
}

.type-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.type-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--td-bg-color-container);
  border: 1px solid var(--td-component-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.type-card:hover {
  border-color: var(--td-brand-color-light);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.type-card.active {
  border-color: var(--td-brand-color);
  background: var(--td-brand-color-light-hover);
}

.type-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: white;
  flex-shrink: 0;
}

.type-info {
  flex: 1;
  min-width: 0;
}

.type-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--td-text-color-primary);
}

.type-count {
  font-size: 12px;
  color: var(--td-text-color-secondary);
}

.type-percentage {
  font-size: 18px;
  font-weight: 600;
  color: var(--td-brand-color);
}

/* 时间轴 */
.timeline-section {
  margin-bottom: 24px;
  padding: 16px;
  background: var(--td-bg-color-container);
  border-radius: 8px;
  border: 1px solid var(--td-component-border);
}

.timeline-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--td-text-color-primary);
}

.timeline-container {
  padding: 0 8px;
}

.timeline-bar {
  position: relative;
  height: 28px;
  background: var(--td-bg-color-page);
  border-radius: 4px;
  overflow: hidden;
}

.timeline-segment {
  position: absolute;
  height: 100%;
  cursor: pointer;
  transition: all 0.15s;
  min-width: 2px;
}

.timeline-segment:hover {
  filter: brightness(1.1);
  z-index: 1;
}

.timeline-segment.selected {
  box-shadow: 0 0 0 2px var(--td-brand-color);
  z-index: 2;
}

.timeline-segment.filtered {
  opacity: 0.3;
}

.segment-inner {
  width: 100%;
  height: 100%;
}

.timeline-legend {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 12px;
  color: var(--td-text-color-placeholder);
}

/* 分组展示 */
.type-groups {
  margin-bottom: 24px;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.group-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  color: white;
}

.group-name {
  font-weight: 500;
  color: var(--td-text-color-primary);
}

.group-content {
  padding: 12px 0;
}

/* 类型统计 */
.type-stats {
  display: flex;
  gap: 24px;
  padding: 12px 16px;
  background: var(--td-bg-color-page);
  border-radius: 6px;
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: var(--td-text-color-secondary);
}

.stat-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--td-text-color-primary);
}

/* 块列表 */
.chunk-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chunk-item {
  padding: 12px;
  background: var(--td-bg-color-container);
  border: 1px solid var(--td-component-border);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.chunk-item:hover {
  border-color: var(--td-brand-color-light);
}

.chunk-item.selected {
  border-color: var(--td-brand-color);
  background: var(--td-brand-color-light-hover);
}

.item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.item-index {
  font-weight: 600;
  color: var(--td-text-color-primary);
}

.item-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--td-text-color-secondary);
  margin-bottom: 8px;
}

.item-preview {
  font-size: 13px;
  color: var(--td-text-color-secondary);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 饼图 */
.pie-chart-section {
  padding: 16px;
  background: var(--td-bg-color-container);
  border-radius: 8px;
  border: 1px solid var(--td-component-border);
}

.pie-chart-section h4 {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--td-text-color-primary);
}

.pie-chart-container {
  display: flex;
  align-items: center;
  gap: 24px;
}

.pie-chart {
  width: 160px;
  height: 160px;
  flex-shrink: 0;
}

.pie-chart :deep(.pie-svg) {
  width: 100%;
  height: 100%;
}

.pie-legend {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pie-legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
  flex-shrink: 0;
}

.legend-label {
  font-size: 13px;
  color: var(--td-text-color-primary);
}

.legend-value {
  font-size: 12px;
  color: var(--td-text-color-secondary);
  margin-left: auto;
}
</style>
