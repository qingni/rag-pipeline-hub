<template>
  <span class="chunk-type-icon" :title="getTooltip(type)">
    <t-icon :name="getIcon(type)" :style="{ color: getColor(type) }" />
    <span v-if="showLabel" class="icon-label">{{ getLabel(type) }}</span>
  </span>
</template>

<script setup>
const props = defineProps({
  type: {
    type: String,
    required: true
  },
  showLabel: {
    type: Boolean,
    default: false
  }
})

const iconConfig = {
  text: {
    icon: 'file-text',
    color: '#1890ff',
    label: '文本',
    tooltip: '文本块'
  },
  table: {
    icon: 'table',
    color: '#52c41a',
    label: '表格',
    tooltip: '表格块'
  },
  image: {
    icon: 'image',
    color: '#722ed1',
    label: '图片',
    tooltip: '图片块'
  },
  code: {
    icon: 'code',
    color: '#fa8c16',
    label: '代码',
    tooltip: '代码块'
  },
  // Strategy icons
  character: {
    icon: 'textformat-wrap',
    color: '#8c8c8c',
    label: '字数',
    tooltip: '按字数分块'
  },
  paragraph: {
    icon: 'article',
    color: '#1890ff',
    label: '段落',
    tooltip: '按段落分块'
  },
  heading: {
    icon: 'format-horizontal-align-top',
    color: '#52c41a',
    label: '标题',
    tooltip: '按标题分块'
  },
  semantic: {
    icon: 'lightbulb',
    color: '#722ed1',
    label: '语义',
    tooltip: '语义分块'
  },
  parent_child: {
    icon: 'tree-list',
    color: '#eb2f96',
    label: '父子',
    tooltip: '父子文档分块'
  },
  hybrid: {
    icon: 'component-layout',
    color: '#fa541c',
    label: '混合',
    tooltip: '混合分块策略（支持多内容类型提取）'
  }
}

const getIcon = (type) => {
  return iconConfig[type]?.icon || 'file'
}

const getColor = (type) => {
  return iconConfig[type]?.color || '#8c8c8c'
}

const getLabel = (type) => {
  return iconConfig[type]?.label || type
}

const getTooltip = (type) => {
  return iconConfig[type]?.tooltip || type
}
</script>

<style scoped>
.chunk-type-icon {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.icon-label {
  font-size: 12px;
  color: var(--td-text-color-secondary);
}
</style>
