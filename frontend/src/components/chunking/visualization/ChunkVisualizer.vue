<template>
  <div class="chunk-visualizer">
    <!-- 工具栏 -->
    <div class="visualizer-toolbar">
      <div class="toolbar-left">
        <t-radio-group v-model="viewMode" variant="default-filled" size="small">
          <t-radio-button value="linear" :disabled="false">
            <template #icon><t-icon name="view-list" /></template>
            线性视图
          </t-radio-button>
          <t-radio-button value="tree" :disabled="!supportsTreeView">
            <template #icon><t-icon name="tree-list" /></template>
            树状视图
          </t-radio-button>
          <t-radio-button value="stats">
            <template #icon><t-icon name="chart-bar" /></template>
            统计视图
          </t-radio-button>
        </t-radio-group>
        
        <t-divider layout="vertical" />
        
        <span class="strategy-badge">
          <ChunkTypeIcon :type="strategyType" :show-label="true" />
        </span>
      </div>
      
      <div class="toolbar-right">
        <!-- 导出按钮 -->
        <t-dropdown :options="exportOptions" @click="handleExport">
          <t-button variant="outline" size="small">
            <template #icon><t-icon name="download" /></template>
            导出
          </t-button>
        </t-dropdown>
        
        <!-- 刷新按钮 -->
        <t-button 
          variant="outline" 
          size="small"
          @click="$emit('refresh')"
        >
          <template #icon><t-icon name="refresh" /></template>
        </t-button>
      </div>
    </div>

    <!-- 可视化内容区 -->
    <div class="visualizer-content" ref="contentRef">
      <!-- 树状视图 (heading, parent_child) -->
      <TreeVisualizer
        v-if="viewMode === 'tree' && supportsTreeView"
        :chunks="chunks"
        :parent-chunks="parentChunks"
        :strategy="strategyType"
        :document-name="documentName"
        @node-click="handleChunkClick"
      />
      
      <!-- 线性视图 -->
      <LinearVisualizer
        v-else-if="viewMode === 'linear' && strategyType !== 'hybrid'"
        :chunks="chunks"
        :strategy="strategyType"
        :show-overlap="strategyType === 'character'"
        :total-count="statistics?.total_chunks || 0"
        @chunk-click="handleChunkClick"
      />
      
      <!-- 混合视图 (hybrid) -->
      <HybridVisualizer
        v-else-if="viewMode === 'linear' && strategyType === 'hybrid'"
        :chunks="chunks"
        :statistics="statistics"
        @chunk-click="handleChunkClick"
      />
      
      <!-- 统计视图 -->
      <ChunkStatsChart
        v-else-if="viewMode === 'stats'"
        :chunks="chunks"
        :parent-chunks="parentChunks"
        :strategy="strategyType"
        :external-statistics="statistics"
      />
    </div>
    
    <!-- 选中块详情抽屉 -->
    <t-drawer
      v-model:visible="detailDrawerVisible"
      :header="selectedChunkTitle"
      size="500px"
      :footer="false"
    >
      <ChunkDetail 
        v-if="selectedChunk"
        :chunk="selectedChunk" 
        :parent-chunk="selectedParentChunk"
        @load-parent="loadParentChunk"
      />
    </t-drawer>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import TreeVisualizer from './TreeVisualizer.vue'
import LinearVisualizer from './LinearVisualizer.vue'
import HybridVisualizer from './HybridVisualizer.vue'
import ChunkStatsChart from './ChunkStatsChart.vue'
import ChunkDetail from '../ChunkDetail.vue'
import ChunkTypeIcon from '../ChunkTypeIcon.vue'
import { 
  getVisualizationConfig, 
  chunksToMermaid,
  exportToJSON,
  calculateChunkStatistics
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
  strategyType: {
    type: String,
    default: 'character'
  },
  documentName: {
    type: String,
    default: ''
  },
  externalStatistics: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['chunk-click', 'refresh', 'load-parent'])

// 获取可视化配置
const visualConfig = computed(() => {
  return getVisualizationConfig(props.strategyType)
})

// 是否支持树状视图
const supportsTreeView = computed(() => {
  return visualConfig.value.supportsTree
})

// 默认视图模式
const viewMode = ref(visualConfig.value.defaultView === 'tree' ? 'tree' : 'linear')

// 统计信息
const statistics = computed(() => {
  if (props.externalStatistics) {
    return props.externalStatistics
  }
  return calculateChunkStatistics(props.chunks, props.parentChunks)
})

// 选中的块
const selectedChunk = ref(null)
const selectedParentChunk = ref(null)
const detailDrawerVisible = ref(false)
const contentRef = ref(null)

// 选中块标题
const selectedChunkTitle = computed(() => {
  if (!selectedChunk.value) return '块详情'
  const seq = selectedChunk.value.sequence_number
  return `块 #${seq !== undefined ? seq + 1 : '?'} 详情`
})

// 导出选项
const exportOptions = [
  { content: '导出为 Mermaid', value: 'mermaid' },
  { content: '导出为 JSON', value: 'json' },
  { content: '复制统计信息', value: 'stats' }
]

// 处理块点击
const handleChunkClick = (chunk) => {
  selectedChunk.value = chunk
  selectedParentChunk.value = null
  detailDrawerVisible.value = true
  emit('chunk-click', chunk)
}

// 加载父块
const loadParentChunk = (parentId) => {
  emit('load-parent', parentId)
}

// 处理导出
const handleExport = async ({ value }) => {
  try {
    switch (value) {
      case 'mermaid':
        const mermaid = chunksToMermaid(props.chunks, props.strategyType, props.parentChunks)
        await navigator.clipboard.writeText(mermaid)
        MessagePlugin.success('Mermaid 图已复制到剪贴板')
        break
        
      case 'json':
        const data = {
          strategy: props.strategyType,
          total_chunks: props.chunks.length,
          statistics: statistics.value,
          chunks: props.chunks.map(c => ({
            id: c.id || c.metadata?.chunk_id,
            sequence_number: c.sequence_number,
            content: c.content,
            metadata: c.metadata,
            chunk_type: c.chunk_type
          }))
        }
        if (props.parentChunks.length > 0) {
          data.parent_chunks = props.parentChunks.map(p => ({
            id: p.id || p.metadata?.chunk_id,
            content: p.content,
            child_count: p.child_count
          }))
        }
        exportToJSON(data, `chunks_${props.strategyType}_${Date.now()}.json`)
        MessagePlugin.success('JSON 文件已下载')
        break
        
      case 'stats':
        const statsText = `分块统计信息
策略: ${props.strategyType}
总块数: ${statistics.value.total_chunks}
总字符数: ${statistics.value.total_characters}
平均块大小: ${Math.round(statistics.value.avg_chunk_size)}
块大小范围: ${statistics.value.min_chunk_size} - ${statistics.value.max_chunk_size}`
        await navigator.clipboard.writeText(statsText)
        MessagePlugin.success('统计信息已复制到剪贴板')
        break
    }
  } catch (error) {
    console.error('Export failed:', error)
    MessagePlugin.error('导出失败')
  }
}

// 监听策略变化，重置视图模式
watch(() => props.strategyType, (newType) => {
  const config = getVisualizationConfig(newType)
  if (config.supportsTree && viewMode.value !== 'stats') {
    viewMode.value = 'tree'
  } else if (!config.supportsTree && viewMode.value === 'tree') {
    viewMode.value = 'linear'
  }
}, { immediate: true })
</script>

<style scoped>
.chunk-visualizer {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--td-bg-color-page);
  border-radius: 8px;
  overflow: hidden;
}

/* 工具栏 */
.visualizer-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--td-bg-color-container);
  border-bottom: 1px solid var(--td-component-border);
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.strategy-badge {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  background: var(--td-bg-color-page);
  border-radius: 4px;
  font-size: 13px;
}

/* 内容区 */
.visualizer-content {
  flex: 1;
  overflow: auto;
  min-height: 400px;
}

/* 响应式 */
@media (max-width: 768px) {
  .visualizer-toolbar {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }
  
  .toolbar-left,
  .toolbar-right {
    justify-content: center;
  }
}
</style>
