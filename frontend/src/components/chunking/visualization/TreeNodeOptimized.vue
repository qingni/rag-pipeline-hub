<template>
  <div class="tree-node" :class="{ expanded: isExpanded }">
    <!-- 节点连接线 -->
    <div class="node-connector">
      <div class="connector-line"></div>
    </div>
    
    <!-- 节点内容 -->
    <div 
      class="node-content"
      :class="{ 
        selected: isSelected,
        'has-children': hasChildren,
        parent: node.isParent,
        child: node.isParent === false
      }"
      @click="handleClick"
    >
      <!-- 展开/折叠按钮 -->
      <div 
        v-if="hasChildren" 
        class="expand-btn"
        @click.stop="toggleExpand"
      >
        <t-icon 
          v-if="!isLoading"
          :name="isExpanded ? 'chevron-down' : 'chevron-right'" 
          size="14px" 
        />
        <t-loading v-else size="14px" />
      </div>
      <div v-else class="expand-placeholder"></div>
      
      <!-- 节点图标 -->
      <div 
        class="node-icon"
        :style="{ backgroundColor: nodeColor }"
      >
        <t-icon :name="nodeIcon" size="14px" />
      </div>
      
      <!-- 节点标签 -->
      <div class="node-label">
        <span class="node-name">{{ nodeName }}</span>
        <span v-if="showStats" class="node-stats">
          {{ node.charCount || 0 }} 字符
        </span>
      </div>
      
      <!-- 节点标签 -->
      <div class="node-tags">
        <!-- 层级标签 (heading) -->
        <t-tag 
          v-if="node.level && strategy === 'heading'" 
          size="small" 
          variant="light"
          :style="{ 
            backgroundColor: nodeColor + '20',
            color: nodeColor,
            borderColor: nodeColor
          }"
        >
          H{{ node.level }}
        </t-tag>
        
        <!-- 类型标签 (parent_child) -->
        <t-tag 
          v-if="node.isParent !== undefined" 
          size="small" 
          :theme="node.isParent ? 'warning' : 'success'"
          variant="light"
        >
          {{ node.isParent ? '父块' : '子块' }}
        </t-tag>
        
        <!-- 子节点数量 -->
        <t-tag 
          v-if="hasChildren" 
          size="small" 
          variant="outline"
          theme="default"
        >
          {{ node.children.length }} 个子节点
        </t-tag>
      </div>
    </div>
    
    <!-- 子节点 - 支持懒加载和分批渲染 -->
    <div 
      v-if="hasChildren && isExpanded" 
      class="node-children"
    >
      <template v-if="shouldRenderChildren">
        <!-- 可见的子节点 -->
        <TreeNodeOptimized
          v-for="(child, index) in visibleChildren"
          :key="child.id || index"
          :node="child"
          :strategy="strategy"
          :depth="depth + 1"
          :expand-level="expandLevel"
          :show-stats="showStats"
          :selected-id="selectedId"
          :lazy-load="lazyLoad"
          @select="$emit('select', $event)"
          @toggle="$emit('toggle', $event)"
        />
        
        <!-- 未加载的子节点提示 -->
        <div 
          v-if="hasMoreChildren" 
          class="load-more-hint"
          @click="loadMoreChildren"
        >
          <t-icon name="chevron-down" size="14px" />
          <span>还有 {{ remainingChildrenCount }} 个子节点，点击加载更多</span>
        </div>
      </template>
      
      <!-- 加载中状态 -->
      <div v-else class="children-loading">
        <t-loading size="small" />
        <span>加载子节点中...</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, inject, nextTick } from 'vue'
import { getHeadingLevelColor } from './utils/visualizerUtils'

const props = defineProps({
  node: {
    type: Object,
    required: true
  },
  strategy: {
    type: String,
    default: 'heading'
  },
  depth: {
    type: Number,
    default: 0
  },
  expandLevel: {
    type: Number,
    default: 2
  },
  showStats: {
    type: Boolean,
    default: true
  },
  selectedId: {
    type: String,
    default: null
  },
  lazyLoad: {
    type: Boolean,
    default: true
  },
  virtualIndex: {
    type: Number,
    default: -1
  }
})

const emit = defineEmits(['select', 'toggle'])

// 注入的方法和状态
const getLevelColor = inject('getLevelColor', getHeadingLevelColor)
const performanceMode = inject('performanceMode', ref(false))

// 本地展开状态
// 默认不展开，让用户主动点击展开
// 这样避免初始状态下所有父块都展开但子节点在loading的问题
const localExpanded = ref(false)

// 懒加载相关状态
const isLoading = ref(false)
// 懒加载模式下，只有用户手动展开时才渲染子节点
const shouldRenderChildren = ref(!props.lazyLoad)
const loadedChildrenCount = ref(10) // 初始加载的子节点数量
const batchSize = 20 // 每次加载的批量大小

// 是否展开
const isExpanded = computed(() => {
  return localExpanded.value
})

// 是否选中
const isSelected = computed(() => {
  return props.selectedId === props.node.id
})

// 是否有子节点
const hasChildren = computed(() => {
  return props.node.children && props.node.children.length > 0
})

// 子节点总数
const totalChildrenCount = computed(() => {
  return props.node.children?.length || 0
})

// 可见的子节点（用于分批渲染）
const visibleChildren = computed(() => {
  if (!hasChildren.value) return []
  
  // 性能模式下限制初始渲染数量
  if (performanceMode.value && totalChildrenCount.value > 10) {
    return props.node.children.slice(0, loadedChildrenCount.value)
  }
  
  return props.node.children
})

// 是否还有更多子节点
const hasMoreChildren = computed(() => {
  return performanceMode.value && 
         totalChildrenCount.value > loadedChildrenCount.value
})

// 剩余子节点数量
const remainingChildrenCount = computed(() => {
  return Math.max(0, totalChildrenCount.value - loadedChildrenCount.value)
})

// 节点名称
const nodeName = computed(() => {
  const name = props.node.name || ''
  return name.length > 40 ? name.slice(0, 40) + '...' : name
})

// 节点颜色
const nodeColor = computed(() => {
  if (props.strategy === 'heading') {
    return getLevelColor(props.node.level || 1)
  } else if (props.strategy === 'parent_child') {
    return props.node.isParent ? '#1890ff' : '#52c41a'
  }
  return '#1890ff'
})

// 节点图标
const nodeIcon = computed(() => {
  if (props.strategy === 'heading') {
    return 'format-horizontal-align-top'
  } else if (props.strategy === 'parent_child') {
    return props.node.isParent ? 'folder' : 'file'
  }
  return 'file'
})

// 切换展开状态
const toggleExpand = async () => {
  if (!hasChildren.value) return
  
  const newState = !localExpanded.value
  
  // 懒加载模式：首次展开时延迟渲染子节点
  if (newState && props.lazyLoad && !shouldRenderChildren.value) {
    isLoading.value = true
    localExpanded.value = true
    emit('toggle', props.node.id, true)
    
    // 使用 requestIdleCallback 或 setTimeout 延迟渲染
    // 这样不会阻塞UI
    await nextTick()
    
    if ('requestIdleCallback' in window) {
      requestIdleCallback(() => {
        shouldRenderChildren.value = true
        isLoading.value = false
      }, { timeout: 100 })
    } else {
      setTimeout(() => {
        shouldRenderChildren.value = true
        isLoading.value = false
      }, 50)
    }
  } else {
    localExpanded.value = newState
    emit('toggle', props.node.id, newState)
  }
}

// 加载更多子节点
const loadMoreChildren = () => {
  loadedChildrenCount.value = Math.min(
    loadedChildrenCount.value + batchSize,
    totalChildrenCount.value
  )
}

// 点击节点
const handleClick = () => {
  emit('select', props.node)
}

// 监听展开层级变化
watch(() => props.expandLevel, (newLevel, oldLevel) => {
  const shouldExpand = props.depth < newLevel
  
  // 性能优化：如果是折叠操作，同时重置懒加载状态
  if (!shouldExpand && localExpanded.value) {
    localExpanded.value = false
    
    // 可选：折叠时重置懒加载状态，释放内存
    if (props.lazyLoad && performanceMode.value) {
      shouldRenderChildren.value = false
      loadedChildrenCount.value = 10
    }
  } else if (shouldExpand && !localExpanded.value) {
    // 展开操作：需要同时处理懒加载
    if (props.lazyLoad && hasChildren.value && !shouldRenderChildren.value) {
      // 懒加载模式下，展开时需要触发子节点渲染
      isLoading.value = true
      localExpanded.value = true
      
      // 使用 nextTick 后延迟渲染子节点
      nextTick().then(() => {
        if ('requestIdleCallback' in window) {
          requestIdleCallback(() => {
            shouldRenderChildren.value = true
            isLoading.value = false
          }, { timeout: 100 })
        } else {
          setTimeout(() => {
            shouldRenderChildren.value = true
            isLoading.value = false
          }, 50)
        }
      })
    } else {
      localExpanded.value = shouldExpand
    }
  }
}, { immediate: false }) // 注意：immediate 改为 false，避免初始化时自动展开

// 监听 lazyLoad 属性变化
watch(() => props.lazyLoad, (newVal) => {
  if (!newVal) {
    shouldRenderChildren.value = true
  }
})
</script>

<style scoped>
.tree-node {
  position: relative;
  margin: 4px 0;
}

/* 连接线 */
.node-connector {
  position: absolute;
  left: -20px;
  top: 0;
  width: 20px;
  height: 20px;
}

.connector-line {
  position: absolute;
  left: 0;
  top: 10px;
  width: 20px;
  height: 0;
  border-top: 1px dashed var(--td-component-border);
}

/* 节点内容 */
.node-content {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--td-bg-color-container);
  border: 1px solid var(--td-component-border);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  max-width: 100%;
}

.node-content:hover {
  border-color: var(--td-brand-color-light);
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.1);
}

.node-content.selected {
  border-color: var(--td-brand-color);
  background: var(--td-brand-color-light-hover);
}

.node-content.parent {
  border-left: 3px solid #1890ff;
}

.node-content.child {
  border-left: 3px solid #52c41a;
}

/* 展开按钮 */
.expand-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 4px;
  cursor: pointer;
  color: var(--td-text-color-secondary);
  transition: all 0.2s;
  flex-shrink: 0;
}

.expand-btn:hover {
  background: var(--td-bg-color-container-hover);
  color: var(--td-brand-color);
}

.expand-placeholder {
  width: 20px;
  flex-shrink: 0;
}

/* 节点图标 */
.node-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  color: white;
  flex-shrink: 0;
}

/* 节点标签 */
.node-label {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.node-name {
  font-size: 13px;
  color: var(--td-text-color-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-stats {
  font-size: 11px;
  color: var(--td-text-color-placeholder);
}

/* 节点标签 */
.node-tags {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

/* 子节点容器 */
.node-children {
  padding-left: 32px;
  margin-left: 12px;
  border-left: 2px solid var(--td-component-border);
  margin-top: 4px;
}

/* 子节点加载中 */
.children-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 0;
  font-size: 12px;
  color: var(--td-text-color-secondary);
}

/* 加载更多提示 */
.load-more-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--td-brand-color);
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}

.load-more-hint:hover {
  background: var(--td-brand-color-light-hover);
}

/* 不同深度的样式变化 */
.tree-node:nth-child(odd) > .node-content {
  /* background: var(--td-bg-color-container); */
}
</style>
