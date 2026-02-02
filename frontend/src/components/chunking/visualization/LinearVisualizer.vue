<template>
  <div class="linear-visualizer">
    <!-- 文档总览条 -->
    <div class="document-overview">
      <div class="overview-header">
        <span class="overview-title">文档分块总览</span>
        <span class="overview-info">
          <template v-if="hasMoreChunks">
            显示前 {{ chunks.length }} 个块（共 {{ actualTotalCount }} 个），{{ formatNumber(totalCharacters) }} 字符
          </template>
          <template v-else>
            共 {{ chunks.length }} 个块，{{ formatNumber(totalCharacters) }} 字符
          </template>
        </span>
      </div>
      <div class="overview-bar" ref="overviewBarRef">
        <div
          v-for="(chunk, index) in displayChunks"
          :key="getChunkId(chunk, index)"
          class="chunk-segment"
          :style="getSegmentStyle(chunk, index)"
          :class="{ 
            selected: selectedIndex === index,
            hovered: hoveredIndex === index
          }"
          @click="selectChunk(index)"
          @mouseenter="handleMouseEnter(index)"
          @mouseleave="handleMouseLeave"
        >
          <!-- 重叠区域标记 -->
          <div 
            v-if="showOverlap && getOverlapWidth(chunk)" 
            class="overlap-indicator"
            :style="{ width: getOverlapWidth(chunk) + '%' }"
          />
        </div>
      </div>
      <div class="overview-scale">
        <span>0</span>
        <span v-if="showPercentage">
          {{ Math.round((displayChunks.length / chunks.length) * 100) }}% 显示
        </span>
        <span>{{ formatNumber(totalCharacters) }} 字符</span>
      </div>
    </div>
    
    <!-- 悬浮提示 -->
    <div 
      v-if="hoveredIndex >= 0 && tooltipPosition" 
      class="chunk-tooltip"
      :style="{ left: tooltipPosition.x + 'px', top: tooltipPosition.y + 'px' }"
    >
      <div class="tooltip-header">块 #{{ hoveredIndex + 1 }}</div>
      <div class="tooltip-content">
        <div class="tooltip-row">
          <span class="tooltip-label">大小:</span>
          <span class="tooltip-value">{{ getChunkSize(displayChunks[hoveredIndex]) }} 字符</span>
        </div>
        <div v-if="strategy === 'semantic'" class="tooltip-row">
          <span class="tooltip-label">相似度:</span>
          <span class="tooltip-value">{{ getSimilarity(displayChunks[hoveredIndex]) }}%</span>
        </div>
        <div v-if="displayChunks[hoveredIndex]?.chunk_type" class="tooltip-row">
          <span class="tooltip-label">类型:</span>
          <span class="tooltip-value">{{ getTypeName(displayChunks[hoveredIndex].chunk_type) }}</span>
        </div>
      </div>
      <div class="tooltip-preview">
        {{ getPreview(displayChunks[hoveredIndex]) }}
      </div>
    </div>
    
    <!-- 分块列表 -->
    <div class="chunk-list-container">
      <div class="list-header">
        <span>分块列表</span>
        <div class="list-controls">
          <!-- 类型筛选 -->
          <t-select
            v-if="hasMultipleTypes"
            v-model="filterType"
            :options="typeFilterOptions"
            placeholder="筛选类型"
            size="small"
            style="width: 100px"
            clearable
          />
          <!-- 排序 -->
          <t-select
            v-model="sortBy"
            :options="sortOptions"
            size="small"
            style="width: 100px"
          />
        </div>
      </div>
      
      <div class="chunk-list" ref="listRef">
        <div
          v-for="(chunk, index) in filteredAndSortedChunks"
          :key="getChunkId(chunk, index)"
          :ref="el => setChunkRef(el, index)"
          class="chunk-card"
          :class="{ 
            selected: selectedIndex === index,
            [`type-${chunk.chunk_type || 'text'}`]: true
          }"
          @click="selectChunk(index)"
        >
          <div class="chunk-card-header">
            <div class="chunk-info">
              <span class="chunk-index">#{{ chunk.sequence_number + 1 || index + 1 }}</span>
              <t-tag size="small" :theme="getSizeTheme(chunk)" variant="light">
                {{ getChunkSize(chunk) }} 字符
              </t-tag>
              
              <!-- 语义分块显示相似度 -->
              <t-tag 
                v-if="strategy === 'semantic' && chunk.metadata?.avg_similarity"
                theme="primary"
                variant="light"
                size="small"
              >
                <t-icon name="link" size="12px" style="margin-right: 2px" />
                {{ getSimilarity(chunk) }}%
              </t-tag>
              
              <!-- 混合分块显示类型 -->
              <t-tag 
                v-if="chunk.chunk_type && chunk.chunk_type !== 'text'"
                :theme="getTypeTheme(chunk.chunk_type)"
                size="small"
                variant="light"
              >
                <t-icon :name="getTypeIcon(chunk.chunk_type)" size="12px" style="margin-right: 2px" />
                {{ getTypeName(chunk.chunk_type) }}
              </t-tag>
              
              <!-- 字符分块显示重叠 -->
              <t-tag 
                v-if="showOverlap && chunk.metadata?.overlap_chars"
                theme="warning"
                size="small"
                variant="outline"
              >
                重叠: {{ chunk.metadata.overlap_chars }}
              </t-tag>
            </div>
            
            <t-button
              theme="primary"
              variant="text"
              size="small"
              @click.stop="$emit('chunk-click', chunk)"
            >
              详情
            </t-button>
          </div>
          
          <div class="chunk-card-content">
            {{ getPreview(chunk, 150) }}
          </div>
          
          <div class="chunk-card-footer">
            <span class="position-info">
              位置: {{ getStartPosition(chunk) }} - {{ getEndPosition(chunk) }}
            </span>
            <div class="position-bar">
              <div 
                class="position-indicator"
                :style="getPositionBarStyle(chunk)"
              />
            </div>
          </div>
        </div>
        
        <!-- 加载更多（前端分批显示） -->
        <div v-if="chunks.length > displayLimit" class="load-more">
          <t-button 
            variant="text" 
            theme="default"
            @click="loadMore"
          >
            加载更多 (还有 {{ chunks.length - displayLimit }} 个)
          </t-button>
        </div>
        
        <!-- 后端数据未全部加载提示 -->
        <div v-else-if="hasMoreChunks" class="more-data-hint">
          <t-icon name="info-circle" size="16px" />
          <span>已显示全部已加载的 {{ chunks.length }} 个分块，后端实际共有 {{ actualTotalCount }} 个分块</span>
        </div>
      </div>
    </div>
    
    <!-- 语义相似度分布 (仅语义分块) -->
    <div v-if="strategy === 'semantic'" class="similarity-section">
      <h4>语义相似度分布</h4>
      <div class="similarity-chart" ref="similarityChartRef"></div>
      <div class="similarity-legend">
        <div class="legend-item">
          <span class="legend-color low"></span>
          <span>低相似度 (&lt;50%)</span>
        </div>
        <div class="legend-item">
          <span class="legend-color medium"></span>
          <span>中等相似度 (50-80%)</span>
        </div>
        <div class="legend-item">
          <span class="legend-color high"></span>
          <span>高相似度 (&gt;80%)</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { getChunkTypeColor } from './utils/visualizerUtils'

const props = defineProps({
  chunks: {
    type: Array,
    default: () => []
  },
  strategy: {
    type: String,
    default: 'character'
  },
  showOverlap: {
    type: Boolean,
    default: false
  },
  // 后端实际的总块数（用于显示分页提示）
  totalCount: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['chunk-click'])

// 状态
const selectedIndex = ref(-1)
const hoveredIndex = ref(-1)
const tooltipPosition = ref(null)
const displayLimit = ref(50)
const filterType = ref(null)
const sortBy = ref('sequence')
const overviewBarRef = ref(null)
const listRef = ref(null)
const chunkRefs = ref({})

// 显示的块（限制数量）
const displayChunks = computed(() => {
  return props.chunks.slice(0, displayLimit.value)
})

// 总字符数
const totalCharacters = computed(() => {
  if (!props.chunks.length) return 0
  const lastChunk = props.chunks[props.chunks.length - 1]
  return getEndPosition(lastChunk) || 
    props.chunks.reduce((sum, c) => sum + getChunkSize(c), 0)
})

// 是否显示百分比
const showPercentage = computed(() => {
  return displayChunks.value.length < props.chunks.length
})

// 后端实际的总块数
const actualTotalCount = computed(() => {
  return props.totalCount || props.chunks.length
})

// 是否还有更多数据未加载（后端有更多数据）
const hasMoreChunks = computed(() => {
  return props.totalCount > 0 && props.totalCount > props.chunks.length
})

// 是否有多种类型
const hasMultipleTypes = computed(() => {
  const types = new Set(props.chunks.map(c => c.chunk_type || 'text'))
  return types.size > 1
})

// 类型筛选选项
const typeFilterOptions = computed(() => {
  const types = [...new Set(props.chunks.map(c => c.chunk_type || 'text'))]
  return [
    { label: '全部', value: null },
    ...types.map(type => ({
      label: getTypeName(type),
      value: type
    }))
  ]
})

// 排序选项
const sortOptions = [
  { label: '按顺序', value: 'sequence' },
  { label: '按大小↓', value: 'size_desc' },
  { label: '按大小↑', value: 'size_asc' }
]

// 筛选和排序后的块
const filteredAndSortedChunks = computed(() => {
  let result = [...displayChunks.value]
  
  // 类型筛选
  if (filterType.value) {
    result = result.filter(c => (c.chunk_type || 'text') === filterType.value)
  }
  
  // 排序
  if (sortBy.value === 'size_desc') {
    result.sort((a, b) => getChunkSize(b) - getChunkSize(a))
  } else if (sortBy.value === 'size_asc') {
    result.sort((a, b) => getChunkSize(a) - getChunkSize(b))
  }
  
  return result
})

// 获取块ID
const getChunkId = (chunk, index) => {
  return chunk?.id || chunk?.metadata?.chunk_id || `chunk_${index}`
}

// 获取块大小
const getChunkSize = (chunk) => {
  return chunk?.metadata?.char_count || 
    chunk?.token_count || 
    chunk?.content?.length || 0
}

// 获取起始位置
const getStartPosition = (chunk) => {
  return chunk?.metadata?.start_position || chunk?.start_position || 0
}

// 获取结束位置
const getEndPosition = (chunk) => {
  return chunk?.metadata?.end_position || chunk?.end_position || 0
}

// 获取相似度
const getSimilarity = (chunk) => {
  const sim = chunk?.metadata?.avg_similarity || 0
  return Math.round(sim * 100)
}

// 获取预览文本
const getPreview = (chunk, maxLength = 100) => {
  const content = chunk?.content || ''
  if (content.length <= maxLength) return content
  return content.slice(0, maxLength) + '...'
}

// 格式化数字
const formatNumber = (num) => {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toLocaleString()
}

// 获取段样式
const getSegmentStyle = (chunk, index) => {
  const start = getStartPosition(chunk)
  const end = getEndPosition(chunk)
  const total = totalCharacters.value || 1
  
  const width = Math.max(((end - start) / total) * 100, 0.5)
  const left = (start / total) * 100
  
  // 根据策略选择颜色
  let color = '#1890ff'
  if (props.strategy === 'semantic') {
    const similarity = chunk?.metadata?.avg_similarity || 0.5
    const hue = 200 + similarity * 60
    color = `hsl(${hue}, 70%, 50%)`
  } else if (props.strategy === 'hybrid' && chunk.chunk_type) {
    color = getChunkTypeColor(chunk.chunk_type)
  } else if (props.strategy === 'paragraph') {
    color = index % 2 === 0 ? '#1890ff' : '#52c41a'
  } else if (props.strategy === 'character') {
    // 渐变色
    const ratio = index / Math.max(displayChunks.value.length - 1, 1)
    const hue = 200 + ratio * 40
    color = `hsl(${hue}, 70%, 50%)`
  }
  
  return {
    width: `${width}%`,
    left: `${left}%`,
    backgroundColor: color
  }
}

// 获取重叠宽度
const getOverlapWidth = (chunk) => {
  const overlap = chunk?.metadata?.overlap_chars || 0
  const total = getChunkSize(chunk) || 1
  return (overlap / total) * 100
}

// 获取位置条样式
const getPositionBarStyle = (chunk) => {
  const start = getStartPosition(chunk)
  const end = getEndPosition(chunk)
  const total = totalCharacters.value || 1
  
  return {
    left: `${(start / total) * 100}%`,
    width: `${((end - start) / total) * 100}%`
  }
}

// 大小主题
const getSizeTheme = (chunk) => {
  const size = getChunkSize(chunk)
  if (size < 200) return 'warning'
  if (size > 1000) return 'danger'
  return 'primary'
}

// 类型配置
const typeConfig = {
  text: { name: '文本', theme: 'primary', icon: 'file-text' },
  table: { name: '表格', theme: 'success', icon: 'table' },
  image: { name: '图片', theme: 'warning', icon: 'image' },
  code: { name: '代码', theme: 'danger', icon: 'code' }
}

const getTypeName = (type) => typeConfig[type]?.name || type
const getTypeTheme = (type) => typeConfig[type]?.theme || 'default'
const getTypeIcon = (type) => typeConfig[type]?.icon || 'file'

// 选中块
const selectChunk = (index) => {
  selectedIndex.value = index
  const chunk = filteredAndSortedChunks.value[index]
  if (chunk) {
    emit('chunk-click', chunk)
  }
}

// 鼠标悬浮
const handleMouseEnter = (index) => {
  hoveredIndex.value = index
  
  // 计算提示框位置
  if (overviewBarRef.value) {
    const bar = overviewBarRef.value
    const rect = bar.getBoundingClientRect()
    const chunk = displayChunks.value[index]
    const start = getStartPosition(chunk)
    const total = totalCharacters.value || 1
    const x = (start / total) * rect.width + rect.left
    
    tooltipPosition.value = {
      x: Math.min(x, window.innerWidth - 250),
      y: rect.bottom + 10
    }
  }
}

const handleMouseLeave = () => {
  hoveredIndex.value = -1
  tooltipPosition.value = null
}

// 设置块引用
const setChunkRef = (el, index) => {
  if (el) {
    chunkRefs.value[index] = el
  }
}

// 加载更多
const loadMore = () => {
  displayLimit.value = Math.min(displayLimit.value + 50, props.chunks.length)
}

// 创建语义相似度图表
const similarityChartRef = ref(null)

const createSimilarityChart = () => {
  if (!similarityChartRef.value || props.strategy !== 'semantic') return
  
  const similarities = displayChunks.value.map((chunk, idx) => ({
    index: idx + 1,
    value: chunk?.metadata?.avg_similarity || 0
  }))
  
  const maxBars = 30
  const displaySims = similarities.slice(0, maxBars)
  
  const svg = `
    <svg viewBox="0 0 500 120" class="similarity-bar-chart">
      ${displaySims.map((item, idx) => {
        const barHeight = item.value * 80
        const x = idx * (500 / displaySims.length) + 2
        const y = 100 - barHeight
        const barWidth = (500 / displaySims.length) - 4
        
        // 根据相似度选择颜色
        let color = '#f5222d'  // 低
        if (item.value >= 0.8) {
          color = '#52c41a'  // 高
        } else if (item.value >= 0.5) {
          color = '#faad14'  // 中
        }
        
        return `
          <rect 
            x="${x}" 
            y="${y}" 
            width="${barWidth}" 
            height="${barHeight}"
            fill="${color}"
            rx="2"
          >
            <title>块 ${item.index}: ${(item.value * 100).toFixed(1)}%</title>
          </rect>
        `
      }).join('')}
      <line x1="0" y1="100" x2="500" y2="100" stroke="#e8e8e8" stroke-width="1"/>
    </svg>
  `
  
  similarityChartRef.value.innerHTML = svg
}

// 监听变化
watch(
  () => [props.chunks, props.strategy],
  () => {
    nextTick(() => {
      createSimilarityChart()
    })
  },
  { immediate: true }
)

onMounted(() => {
  createSimilarityChart()
})
</script>

<style scoped>
.linear-visualizer {
  padding: 16px;
}

/* 文档总览 */
.document-overview {
  margin-bottom: 24px;
  padding: 16px;
  background: var(--td-bg-color-container);
  border-radius: 8px;
  border: 1px solid var(--td-component-border);
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.overview-title {
  font-weight: 500;
  color: var(--td-text-color-primary);
}

.overview-info {
  font-size: 13px;
  color: var(--td-text-color-secondary);
}

.overview-bar {
  position: relative;
  height: 32px;
  background: var(--td-bg-color-page);
  border-radius: 6px;
  overflow: hidden;
}

.chunk-segment {
  position: absolute;
  height: 100%;
  cursor: pointer;
  transition: all 0.15s ease;
  min-width: 2px;
}

.chunk-segment:hover,
.chunk-segment.hovered {
  filter: brightness(1.15);
  z-index: 1;
  transform: scaleY(1.1);
}

.chunk-segment.selected {
  box-shadow: 0 0 0 2px var(--td-brand-color);
  z-index: 2;
}

.overlap-indicator {
  position: absolute;
  right: 0;
  top: 0;
  height: 100%;
  background: repeating-linear-gradient(
    45deg,
    rgba(255, 255, 255, 0.3),
    rgba(255, 255, 255, 0.3) 2px,
    transparent 2px,
    transparent 4px
  );
}

.overview-scale {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 12px;
  color: var(--td-text-color-placeholder);
}

/* 悬浮提示 */
.chunk-tooltip {
  position: fixed;
  z-index: 1000;
  width: 240px;
  padding: 12px;
  background: var(--td-bg-color-container);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border: 1px solid var(--td-component-border);
  pointer-events: none;
}

.tooltip-header {
  font-weight: 600;
  color: var(--td-text-color-primary);
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--td-component-border);
}

.tooltip-content {
  margin-bottom: 8px;
}

.tooltip-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 4px;
}

.tooltip-label {
  color: var(--td-text-color-secondary);
}

.tooltip-value {
  color: var(--td-text-color-primary);
  font-weight: 500;
}

.tooltip-preview {
  font-size: 12px;
  color: var(--td-text-color-secondary);
  line-height: 1.5;
  max-height: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 分块列表 */
.chunk-list-container {
  margin-bottom: 24px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-weight: 500;
  color: var(--td-text-color-primary);
}

.list-controls {
  display: flex;
  gap: 8px;
}

.chunk-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 500px;
  overflow-y: auto;
  padding-right: 4px;
}

.chunk-card {
  padding: 12px;
  background: var(--td-bg-color-container);
  border: 1px solid var(--td-component-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.chunk-card:hover {
  border-color: var(--td-brand-color-light);
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.1);
}

.chunk-card.selected {
  border-color: var(--td-brand-color);
  background: var(--td-brand-color-light-hover);
}

/* 类型左边框 */
.chunk-card.type-table {
  border-left: 3px solid #52c41a;
}

.chunk-card.type-code {
  border-left: 3px solid #722ed1;
}

.chunk-card.type-image {
  border-left: 3px solid #faad14;
}

.chunk-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.chunk-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.chunk-index {
  font-weight: 600;
  color: var(--td-text-color-primary);
  font-size: 14px;
}

.chunk-card-content {
  font-size: 13px;
  color: var(--td-text-color-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  margin-bottom: 8px;
}

.chunk-card-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--td-text-color-placeholder);
}

.position-info {
  flex-shrink: 0;
}

.position-bar {
  flex: 1;
  height: 4px;
  background: var(--td-bg-color-page);
  border-radius: 2px;
  overflow: hidden;
}

.position-indicator {
  position: relative;
  height: 100%;
  background: var(--td-brand-color);
  border-radius: 2px;
  min-width: 2px;
}

.load-more {
  text-align: center;
  padding: 12px;
}

.more-data-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  margin-top: 8px;
  background: var(--td-bg-color-page);
  border-radius: 6px;
  font-size: 13px;
  color: var(--td-text-color-secondary);
}

.more-data-hint :deep(.t-icon) {
  color: var(--td-brand-color);
}

/* 语义相似度区域 */
.similarity-section {
  padding: 16px;
  background: var(--td-bg-color-container);
  border-radius: 8px;
  border: 1px solid var(--td-component-border);
}

.similarity-section h4 {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--td-text-color-primary);
}

.similarity-chart {
  width: 100%;
  height: 120px;
  margin-bottom: 12px;
}

.similarity-chart :deep(svg) {
  width: 100%;
  height: 100%;
}

.similarity-legend {
  display: flex;
  gap: 24px;
  justify-content: center;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--td-text-color-secondary);
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.legend-color.low {
  background: #f5222d;
}

.legend-color.medium {
  background: #faad14;
}

.legend-color.high {
  background: #52c41a;
}
</style>
