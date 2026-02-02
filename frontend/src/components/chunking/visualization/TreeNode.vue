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
          :name="isExpanded ? 'chevron-down' : 'chevron-right'" 
          size="14px" 
        />
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
    
    <!-- 子节点 -->
    <div v-if="hasChildren && isExpanded" class="node-children">
      <TreeNode
        v-for="(child, index) in node.children"
        :key="child.id || index"
        :node="child"
        :strategy="strategy"
        :depth="depth + 1"
        :expand-level="expandLevel"
        :show-stats="showStats"
        :selected-id="selectedId"
        @select="$emit('select', $event)"
        @toggle="$emit('toggle', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, inject } from 'vue'
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
  }
})

const emit = defineEmits(['select', 'toggle'])

// 注入的方法
const getLevelColor = inject('getLevelColor', getHeadingLevelColor)

// 本地展开状态
const localExpanded = ref(props.depth < props.expandLevel)

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
const toggleExpand = () => {
  localExpanded.value = !localExpanded.value
  emit('toggle', props.node.id, localExpanded.value)
}

// 点击节点
const handleClick = () => {
  emit('select', props.node)
}

// 监听展开层级变化
watch(() => props.expandLevel, (newLevel) => {
  localExpanded.value = props.depth < newLevel
}, { immediate: true })
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

/* 不同深度的样式变化 */
.tree-node:nth-child(odd) > .node-content {
  /* background: var(--td-bg-color-container); */
}
</style>
