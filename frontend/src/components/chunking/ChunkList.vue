<template>
  <div class="chunk-list">
    <t-card title="分块列表" :bordered="false">
      <template #actions>
        <t-space>
          <!-- Chunk type filter for hybrid chunking results -->
          <t-select
            v-if="hasMultipleTypes"
            v-model="selectedType"
            :options="typeFilterOptions"
            placeholder="筛选类型"
            size="small"
            style="width: 120px"
            clearable
            @change="handleTypeFilter"
          />
          <!-- View mode toggle for parent-child results -->
          <t-radio-group 
            v-if="hasParentChunks" 
            v-model="viewMode" 
            variant="default-filled"
            size="small"
          >
            <t-radio-button value="flat">平铺视图</t-radio-button>
            <t-radio-button value="tree">树形视图</t-radio-button>
          </t-radio-group>
          <span class="total-count">
            共 {{ totalCount }} 个
            <template v-if="hasParentChunks">（{{ parentCount }} 个父块）</template>
          </span>
        </t-space>
      </template>

      <t-loading :loading="loading" size="small">
        <!-- Tree View for Parent-Child -->
        <template v-if="viewMode === 'tree' && hasParentChunks">
          <div class="tree-view">
            <div 
              v-for="parent in parentChunks" 
              :key="parent.id" 
              class="parent-node"
            >
              <!-- Parent chunk header -->
              <div 
                class="parent-header"
                :class="{ 'expanded': expandedParents.has(parent.id) }"
                @click="toggleParent(parent.id)"
              >
                <t-icon 
                  :name="expandedParents.has(parent.id) ? 'chevron-down' : 'chevron-right'" 
                  size="16px"
                />
                <t-tag size="small" theme="warning" variant="light">
                  父块 #{{ parent.sequence_number + 1 }}
                </t-tag>
                <span class="parent-info">
                  {{ parent.child_count }} 个子块 · {{ parent.content?.length || 0 }} 字符
                </span>
              </div>
              
              <!-- Parent content preview -->
              <div v-if="expandedParents.has(parent.id)" class="parent-content">
                <div class="parent-preview" @click="handleSelectParent(parent)">
                  {{ getPreviewText(parent.content, 150) }}
                </div>
                
                <!-- Child chunks -->
                <div class="children-container">
                  <div 
                    v-for="chunk in getChildrenOfParent(parent.id)" 
                    :key="chunk.id"
                    class="child-node"
                    :class="{ 'selected': selectedChunkId === chunk.id }"
                    @click="handleSelect(chunk)"
                  >
                    <t-tag size="small" theme="primary" variant="light">
                      块 #{{ chunk.sequence_number + 1 }}
                    </t-tag>
                    <span class="chunk-size">
                      {{ chunk.token_count || chunk.metadata?.char_count || 0 }} 字符
                    </span>
                    <div class="chunk-preview">
                      {{ getPreviewText(chunk.content, 80) }}
                    </div>
                  </div>
                  
                  <t-loading v-if="loadingChildren.has(parent.id)" size="small" />
                  
                  <t-button 
                    v-if="!loadingChildren.has(parent.id) && getChildrenOfParent(parent.id).length < parent.child_count"
                    theme="default"
                    variant="text"
                    size="small"
                    @click.stop="loadMoreChildren(parent.id)"
                  >
                    加载更多子块...
                  </t-button>
                </div>
              </div>
            </div>
            
            <!-- Load more parents -->
            <t-button 
              v-if="parentChunks.length < parentCount"
              theme="default"
              variant="text"
              block
              @click="$emit('load-more-parents')"
            >
              加载更多父块...
            </t-button>
          </div>
        </template>

        <!-- Flat View (default) -->
        <template v-else>
          <t-list v-if="chunks.length > 0" :split="true">
            <t-list-item
              v-for="chunk in chunks"
              :key="chunk.id"
              :class="{ 'selected': selectedChunkId === chunk.id }"
              @click="handleSelect(chunk)"
              style="cursor: pointer"
            >
              <t-list-item-meta>
                <template #title>
                  <div class="chunk-header">
                    <t-tag size="small" theme="primary" variant="light">
                      块 #{{ chunk.sequence_number + 1 }}
                    </t-tag>
                    <!-- Chunk type icon -->
                    <t-tag 
                      v-if="chunk.chunk_type && chunk.chunk_type !== 'text'" 
                      size="small" 
                      :theme="getTypeTheme(chunk.chunk_type)" 
                      variant="light"
                    >
                      <t-icon :name="getTypeIcon(chunk.chunk_type)" size="12px" />
                      {{ getTypeName(chunk.chunk_type) }}
                    </t-tag>
                    <t-tag 
                      v-if="chunk.parent_id" 
                      size="small" 
                      theme="warning" 
                      variant="outline"
                    >
                      有父块
                    </t-tag>
                    <span class="chunk-size">
                      {{ chunk.token_count || chunk.metadata?.char_count || 0 }} 字符
                    </span>
                  </div>
                </template>
                <template #description>
                  <div class="chunk-preview">
                    {{ getPreviewText(chunk.content) }}
                  </div>
                </template>
              </t-list-item-meta>
              <template #action>
                <t-button
                  theme="primary"
                  variant="text"
                  size="small"
                  @click.stop="handleSelect(chunk)"
                >
                  查看详情
                </t-button>
              </template>
            </t-list-item>
          </t-list>

          <t-empty
            v-else-if="!loading"
            description="暂无分块数据"
          />

          <t-pagination
            v-if="totalCount > pageSize"
            :current="currentPage"
            :page-size="currentPageSize"
            :total="totalCount"
            :page-size-options="[20, 50, 100]"
            show-page-size
            @change="handlePageChange"
            style="margin-top: 16px"
          />
        </template>
      </t-loading>
    </t-card>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  chunks: {
    type: Array,
    default: () => []
  },
  parentChunks: {
    type: Array,
    default: () => []
  },
  totalCount: {
    type: Number,
    default: 0
  },
  parentCount: {
    type: Number,
    default: 0
  },
  page: {
    type: Number,
    default: 1
  },
  pageSize: {
    type: Number,
    default: 50
  },
  selectedChunkId: {
    type: String,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  availableTypes: {
    type: Array,
    default: () => []  // ['text', 'table', 'image', 'code']
  }
})

const emit = defineEmits(['select', 'select-parent', 'page-change', 'load-children', 'load-more-parents', 'type-filter'])

const currentPage = ref(props.page)
const currentPageSize = ref(props.pageSize)
const viewMode = ref('flat')
const expandedParents = ref(new Set())
const loadingChildren = ref(new Set())
const childrenByParent = ref(new Map())
const selectedType = ref(null)

// Chunk type configuration
const typeConfig = {
  text: { name: '文本', theme: 'primary', icon: 'file-text' },
  table: { name: '表格', theme: 'success', icon: 'table' },
  image: { name: '图片', theme: 'warning', icon: 'image' },
  code: { name: '代码', theme: 'danger', icon: 'code' }
}

// Computed
const hasParentChunks = computed(() => props.parentChunks.length > 0 || props.parentCount > 0)

const hasMultipleTypes = computed(() => {
  // Check if chunks have multiple types
  if (props.availableTypes.length > 1) return true
  
  const types = new Set(props.chunks.map(c => c.chunk_type || 'text'))
  return types.size > 1
})

const typeFilterOptions = computed(() => {
  const types = props.availableTypes.length > 0 
    ? props.availableTypes 
    : [...new Set(props.chunks.map(c => c.chunk_type || 'text'))]
  
  return [
    { label: '全部类型', value: null },
    ...types.map(type => ({
      label: typeConfig[type]?.name || type,
      value: type
    }))
  ]
})

// Watch for parent chunks changes
watch(() => props.parentChunks, (newParents) => {
  if (newParents.length > 0) {
    // Auto-expand first parent
    if (expandedParents.value.size === 0) {
      expandedParents.value.add(newParents[0].id)
    }
  }
}, { immediate: true })

// Methods
const handleSelect = (chunk) => {
  emit('select', chunk)
}

const handleSelectParent = (parent) => {
  emit('select-parent', parent)
}

const handlePageChange = ({ current, pageSize }) => {
  emit('page-change', { page: current, pageSize })
}

const handleTypeFilter = (type) => {
  emit('type-filter', type)
}

const getPreviewText = (content, maxLength = 100) => {
  if (!content) return ''
  const preview = content.substring(0, maxLength)
  return preview + (content.length > maxLength ? '...' : '')
}

const toggleParent = (parentId) => {
  if (expandedParents.value.has(parentId)) {
    expandedParents.value.delete(parentId)
  } else {
    expandedParents.value.add(parentId)
    // Load children if not already loaded
    if (!childrenByParent.value.has(parentId)) {
      loadChildren(parentId)
    }
  }
  // Trigger reactivity
  expandedParents.value = new Set(expandedParents.value)
}

const loadChildren = async (parentId) => {
  loadingChildren.value.add(parentId)
  loadingChildren.value = new Set(loadingChildren.value)
  
  emit('load-children', { parentId })
}

const loadMoreChildren = (parentId) => {
  emit('load-children', { parentId, loadMore: true })
}

const getChildrenOfParent = (parentId) => {
  // Filter chunks that belong to this parent
  return props.chunks.filter(chunk => chunk.parent_id === parentId)
}

// Type helpers
const getTypeTheme = (type) => {
  return typeConfig[type]?.theme || 'default'
}

const getTypeIcon = (type) => {
  return typeConfig[type]?.icon || 'file'
}

const getTypeName = (type) => {
  return typeConfig[type]?.name || type
}

// Expose method to update children from parent
const setChildrenForParent = (parentId, children) => {
  childrenByParent.value.set(parentId, children)
  loadingChildren.value.delete(parentId)
  loadingChildren.value = new Set(loadingChildren.value)
}

defineExpose({ setChildrenForParent })
</script>

<style scoped>
.chunk-list {
  height: 100%;
}

.chunk-list :deep(.t-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chunk-list :deep(.t-card__body) {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.chunk-list :deep(.t-list) {
  flex: 1;
  overflow-y: auto;
  max-height: calc(100vh - 400px);
}

.chunk-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chunk-size {
  font-size: 12px;
  color: var(--td-text-color-secondary);
}

.chunk-preview {
  font-size: 12px;
  color: var(--td-text-color-secondary);
  line-height: 1.5;
  margin-top: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.total-count {
  font-size: 12px;
  color: var(--td-text-color-secondary);
}

.selected {
  background-color: var(--td-bg-color-container-select);
  border-left: 3px solid var(--td-brand-color);
}

.chunk-list :deep(.t-list-item) {
  transition: all 0.2s ease;
  border-left: 3px solid transparent;
}

.chunk-list :deep(.t-list-item:hover) {
  background-color: var(--td-bg-color-container-hover);
}

/* Tree View Styles */
.tree-view {
  overflow-y: auto;
  max-height: calc(100vh - 400px);
}

.parent-node {
  margin-bottom: 8px;
  border: 1px solid var(--td-component-border);
  border-radius: 6px;
  overflow: hidden;
}

.parent-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background-color: var(--td-bg-color-container);
  cursor: pointer;
  transition: background-color 0.2s;
}

.parent-header:hover {
  background-color: var(--td-bg-color-container-hover);
}

.parent-header.expanded {
  border-bottom: 1px solid var(--td-component-border);
}

.parent-info {
  font-size: 12px;
  color: var(--td-text-color-secondary);
  margin-left: auto;
}

.parent-content {
  padding: 12px;
}

.parent-preview {
  font-size: 13px;
  color: var(--td-text-color-secondary);
  line-height: 1.6;
  padding: 8px 12px;
  background-color: var(--td-bg-color-page);
  border-radius: 4px;
  margin-bottom: 12px;
  cursor: pointer;
}

.parent-preview:hover {
  background-color: var(--td-bg-color-container-hover);
}

.children-container {
  padding-left: 16px;
  border-left: 2px solid var(--td-brand-color-light);
}

.child-node {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-bottom: 4px;
  background-color: var(--td-bg-color-container);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.child-node:hover {
  background-color: var(--td-bg-color-container-hover);
}

.child-node.selected {
  background-color: var(--td-bg-color-container-select);
  border-left: 3px solid var(--td-brand-color);
}

.child-node .chunk-preview {
  width: 100%;
  margin-top: 4px;
}
</style>
