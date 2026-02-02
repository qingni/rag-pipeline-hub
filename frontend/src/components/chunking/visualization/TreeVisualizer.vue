<template>
  <div class="tree-visualizer">
    <!-- 控制栏 -->
    <div class="visualizer-controls">
      <div class="control-group">
        <span class="control-label">展开层级:</span>
        <t-input-number
          v-model="expandLevel"
          :min="1"
          :max="6"
          size="small"
          style="width: 100px"
          @change="updateExpandLevel"
        />
      </div>
      <div class="control-group">
        <t-checkbox v-model="showStats">显示统计</t-checkbox>
      </div>
      <div class="control-group">
        <t-checkbox v-model="lazyLoadChildren" :disabled="!performanceMode">
          <span class="control-label-with-tip">
            懒加载子节点
            <t-tooltip content="展开时才渲染子节点，提升大数据量下的性能">
              <t-icon name="help-circle" size="14px" />
            </t-tooltip>
          </span>
        </t-checkbox>
      </div>
      <div class="control-group">
        <t-button size="small" variant="outline" @click="expandAll" :disabled="performanceMode && nodeCount > 500">
          全部展开
        </t-button>
        <t-button size="small" variant="outline" @click="collapseAll">全部折叠</t-button>
      </div>
      <!-- 性能指示器 -->
      <div v-if="nodeCount > 100" class="performance-indicator">
        <t-tag 
          :theme="nodeCount > 500 ? 'warning' : 'default'" 
          size="small"
          variant="light"
        >
          <t-icon name="chart-bar" size="14px" />
          {{ nodeCount }} 节点
        </t-tag>
        <t-tooltip v-if="nodeCount > 500" content="节点数量较多，已自动启用性能优化模式">
          <t-icon name="info-circle" size="14px" class="warning-icon" />
        </t-tooltip>
      </div>
    </div>
    
    <!-- 树状图 -->
    <div class="tree-container" ref="treeContainerRef">
      <div class="tree-content">
        <!-- 根节点 -->
        <div class="tree-root">
          <div class="root-node">
            <t-icon name="file-text" size="20px" />
            <span class="root-title">{{ documentName || '文档' }}</span>
            <t-tag size="small" theme="primary" variant="light">
              {{ nodeCount }} 个节点
            </t-tag>
            <t-tag v-if="parentCount" size="small" theme="warning" variant="light">
              {{ parentCount }} 父块
            </t-tag>
          </div>
        </div>
        
        <!-- 树形结构 - 使用虚拟滚动优化 -->
        <div class="tree-nodes">
          <!-- 父块列表 - 支持虚拟滚动 -->
          <template v-if="performanceMode && strategy === 'parent_child'">
            <!-- 虚拟滚动模式：只渲染可视区域附近的父块 -->
            <div 
              class="virtual-scroll-container"
              ref="virtualScrollRef"
              @scroll="handleVirtualScroll"
            >
              <div 
                class="virtual-scroll-spacer" 
                :style="{ height: totalHeight + 'px' }"
              >
                <div 
                  class="virtual-scroll-content"
                  :style="{ transform: `translateY(${offsetY}px)` }"
                >
                  <TreeNodeOptimized
                    v-for="(node, index) in visibleNodes"
                    :key="node.id || index"
                    :node="node"
                    :strategy="strategy"
                    :depth="1"
                    :expand-level="expandLevel"
                    :show-stats="showStats"
                    :selected-id="selectedNodeId"
                    :lazy-load="lazyLoadChildren"
                    :virtual-index="virtualStartIndex + index"
                    @select="handleNodeSelect"
                    @toggle="handleNodeToggle"
                  />
                </div>
              </div>
            </div>
          </template>
          <template v-else>
            <!-- 普通模式：直接渲染所有节点 -->
            <TreeNodeOptimized
              v-for="(node, index) in rootChildren"
              :key="node.id || index"
              :node="node"
              :strategy="strategy"
              :depth="1"
              :expand-level="expandLevel"
              :show-stats="showStats"
              :selected-id="selectedNodeId"
              :lazy-load="lazyLoadChildren"
              @select="handleNodeSelect"
              @toggle="handleNodeToggle"
            />
          </template>
        </div>
      </div>
    </div>
    
    <!-- 图例 -->
    <div class="tree-legend">
      <template v-if="strategy === 'heading'">
        <div class="legend-title">标题层级</div>
        <div class="legend-items">
          <div v-for="level in [1, 2, 3, 4, 5, 6]" :key="level" class="legend-item">
            <span 
              class="legend-dot" 
              :style="{ backgroundColor: getLevelColor(level) }"
            ></span>
            <span>H{{ level }}</span>
          </div>
        </div>
      </template>
      <template v-else-if="strategy === 'parent_child'">
        <div class="legend-title">节点类型</div>
        <div class="legend-items">
          <div class="legend-item">
            <span class="legend-dot parent"></span>
            <span>父块 (完整上下文)</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot child"></span>
            <span>子块 (用于检索)</span>
          </div>
        </div>
        <div v-if="performanceMode" class="legend-perf-tip">
          <t-icon name="lightning" size="14px" />
          <span>性能优化模式已启用</span>
        </div>
      </template>
    </div>
    
    <!-- 选中节点详情 -->
    <div v-if="selectedNode" class="selected-node-detail">
      <div class="detail-header">
        <span class="detail-title">
          {{ getNodeTitle(selectedNode) }}
        </span>
        <t-button 
          size="small" 
          variant="text" 
          @click="selectedNode = null"
        >
          关闭
        </t-button>
      </div>
      <div class="detail-meta">
        <t-tag size="small" theme="primary" variant="light">
          {{ selectedNode.charCount || 0 }} 字符
        </t-tag>
        <t-tag v-if="selectedNode.level" size="small" variant="light">
          H{{ selectedNode.level }}
        </t-tag>
        <t-tag v-if="selectedNode.isParent !== undefined" size="small" :theme="selectedNode.isParent ? 'warning' : 'success'" variant="light">
          {{ selectedNode.isParent ? '父块' : '子块' }}
        </t-tag>
        <t-tag v-if="selectedNode.childCount" size="small" variant="outline">
          {{ selectedNode.childCount }} 个子块
        </t-tag>
      </div>
      <div class="detail-content">
        {{ getNodePreview(selectedNode) }}
      </div>
      <t-button 
        theme="primary" 
        size="small" 
        block
        @click="viewFullDetail"
      >
        查看完整详情
      </t-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, provide, onMounted, onUnmounted } from 'vue'
import TreeNodeOptimized from './TreeNodeOptimized.vue'
import { 
  buildHeadingTree, 
  buildParentChildTree,
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
    default: 'heading'
  },
  documentName: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['node-click'])

// 状态
// 默认展开层级：1表示只显示第一层（父块），用户点击才展开子块
const expandLevel = ref(1)
const showStats = ref(true)
const selectedNode = ref(null)
const selectedNodeId = ref(null)
const expandedNodes = ref(new Set())
const treeContainerRef = ref(null)
const virtualScrollRef = ref(null)

// 性能优化相关状态
const lazyLoadChildren = ref(true)

// 虚拟滚动状态
const scrollTop = ref(0)
const nodeHeight = 44 // 每个父节点的估算高度
const bufferSize = 5 // 缓冲区大小
const virtualStartIndex = ref(0)
const visibleCount = ref(20)
const offsetY = ref(0)

// 构建树数据
const treeData = computed(() => {
  if (props.strategy === 'heading') {
    return buildHeadingTree(props.chunks)
  } else if (props.strategy === 'parent_child') {
    return buildParentChildTree(props.parentChunks, props.chunks)
  }
  return { id: 'root', name: '文档', children: [] }
})

// 根节点的子节点
const rootChildren = computed(() => {
  return treeData.value?.children || []
})

// 父块数量
const parentCount = computed(() => {
  if (props.strategy === 'parent_child') {
    return rootChildren.value.length
  }
  return 0
})

// 节点总数
const nodeCount = computed(() => {
  const countNodes = (node) => {
    let count = 1
    if (node.children) {
      for (const child of node.children) {
        count += countNodes(child)
      }
    }
    return count
  }
  return rootChildren.value.reduce((sum, node) => sum + countNodes(node), 0)
})

// 是否启用性能模式（节点数量 > 100 时自动启用）
const performanceMode = computed(() => {
  return nodeCount.value > 100
})

// 虚拟滚动：总高度
const totalHeight = computed(() => {
  return rootChildren.value.length * nodeHeight
})

// 虚拟滚动：可见节点
const visibleNodes = computed(() => {
  if (!performanceMode.value) {
    return rootChildren.value
  }
  
  const start = Math.max(0, virtualStartIndex.value - bufferSize)
  const end = Math.min(
    rootChildren.value.length, 
    virtualStartIndex.value + visibleCount.value + bufferSize
  )
  
  return rootChildren.value.slice(start, end)
})

// 处理虚拟滚动
const handleVirtualScroll = (e) => {
  if (!performanceMode.value) return
  
  scrollTop.value = e.target.scrollTop
  virtualStartIndex.value = Math.floor(scrollTop.value / nodeHeight)
  offsetY.value = Math.max(0, (virtualStartIndex.value - bufferSize) * nodeHeight)
}

// 更新可见数量
const updateVisibleCount = () => {
  if (virtualScrollRef.value) {
    const containerHeight = virtualScrollRef.value.clientHeight
    visibleCount.value = Math.ceil(containerHeight / nodeHeight) + 2
  }
}

// 获取层级颜色
const getLevelColor = (level) => {
  return getHeadingLevelColor(level)
}

// 获取节点标题
const getNodeTitle = (node) => {
  if (!node) return ''
  return node.name || `节点`
}

// 获取节点预览
const getNodePreview = (node) => {
  if (!node?.originalChunk) return ''
  const content = node.originalChunk.content || ''
  return content.length > 300 ? content.slice(0, 300) + '...' : content
}

// 处理节点选择
const handleNodeSelect = (node) => {
  selectedNode.value = node
  selectedNodeId.value = node.id
}

// 处理节点展开/折叠
const handleNodeToggle = (nodeId, expanded) => {
  if (expanded) {
    expandedNodes.value.add(nodeId)
  } else {
    expandedNodes.value.delete(nodeId)
  }
}

// 更新展开层级
const updateExpandLevel = (level) => {
  expandLevel.value = level
}

// 全部展开
const expandAll = () => {
  // 性能模式下限制全部展开
  if (performanceMode.value && nodeCount.value > 500) {
    return
  }
  expandLevel.value = 10
}

// 全部折叠
const collapseAll = () => {
  expandLevel.value = 1
  expandedNodes.value.clear()
}

// 查看完整详情
const viewFullDetail = () => {
  if (selectedNode.value?.originalChunk) {
    emit('node-click', selectedNode.value.originalChunk)
  }
}

// 生命周期
onMounted(() => {
  updateVisibleCount()
  window.addEventListener('resize', updateVisibleCount)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateVisibleCount)
})

// 监听容器变化
watch(virtualScrollRef, () => {
  updateVisibleCount()
})

// 提供给子组件
provide('expandedNodes', expandedNodes)
provide('getLevelColor', getLevelColor)
provide('performanceMode', performanceMode)
provide('lazyLoadChildren', lazyLoadChildren)
</script>

<style scoped>
.tree-visualizer {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
}

/* 控制栏 */
.visualizer-controls {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: var(--td-bg-color-container);
  border-bottom: 1px solid var(--td-component-border);
  flex-shrink: 0;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-label {
  font-size: 13px;
  color: var(--td-text-color-secondary);
}

.control-label-with-tip {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--td-text-color-secondary);
}

.performance-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.warning-icon {
  color: var(--td-warning-color);
  cursor: help;
}

/* 树容器 */
.tree-container {
  flex: 1;
  overflow: auto;
  padding: 16px;
  background: var(--td-bg-color-page);
}

.tree-content {
  min-width: max-content;
}

/* 根节点 */
.tree-root {
  margin-bottom: 8px;
}

.root-node {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--td-bg-color-container);
  border-radius: 8px;
  border: 1px solid var(--td-component-border);
}

.root-title {
  font-weight: 600;
  color: var(--td-text-color-primary);
}

/* 树节点区域 */
.tree-nodes {
  padding-left: 20px;
  border-left: 2px solid var(--td-component-border);
  margin-left: 20px;
}

/* 虚拟滚动容器 */
.virtual-scroll-container {
  height: calc(100vh - 400px);
  min-height: 300px;
  overflow-y: auto;
  overflow-x: hidden;
}

.virtual-scroll-spacer {
  position: relative;
  width: 100%;
}

.virtual-scroll-content {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
}

/* 图例 */
.tree-legend {
  padding: 12px 16px;
  background: var(--td-bg-color-container);
  border-top: 1px solid var(--td-component-border);
  flex-shrink: 0;
}

.legend-title {
  font-size: 12px;
  color: var(--td-text-color-secondary);
  margin-bottom: 8px;
}

.legend-items {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--td-text-color-primary);
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.legend-dot.parent {
  background: #1890ff;
}

.legend-dot.child {
  background: #52c41a;
}

.legend-perf-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 6px 10px;
  background: var(--td-success-color-light);
  border-radius: 4px;
  font-size: 12px;
  color: var(--td-success-color);
}

/* 选中节点详情 */
.selected-node-detail {
  padding: 16px;
  background: var(--td-bg-color-container);
  border-top: 1px solid var(--td-component-border);
  flex-shrink: 0;
  max-height: 250px;
  overflow-y: auto;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.detail-title {
  font-weight: 600;
  color: var(--td-text-color-primary);
  font-size: 14px;
}

.detail-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.detail-content {
  font-size: 13px;
  color: var(--td-text-color-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 100px;
  overflow-y: auto;
  padding: 12px;
  background: var(--td-bg-color-page);
  border-radius: 6px;
  margin-bottom: 12px;
}
</style>
