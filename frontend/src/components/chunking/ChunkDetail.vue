<template>
  <div class="chunk-detail">
    <t-card v-if="chunk" title="分块详情" :bordered="false">
      <template #actions>
        <t-button
          theme="default"
          size="small"
          @click="copyContent"
        >
          <template #icon><t-icon name="file-copy" /></template>
          复制内容
        </t-button>
      </template>

      <t-descriptions :column="2" :colon="true">
        <t-descriptions-item label="序号">
          块 #{{ chunk.sequence_number + 1 }}
        </t-descriptions-item>
        <t-descriptions-item label="字符数">
          {{ chunk.token_count || chunk.metadata?.char_count || chunk.content?.length || 0 }}
        </t-descriptions-item>
        <t-descriptions-item label="起始位置">
          {{ chunk.start_position || chunk.metadata?.start_position || 0 }}
        </t-descriptions-item>
        <t-descriptions-item label="结束位置">
          {{ chunk.end_position || chunk.metadata?.end_position || 0 }}
        </t-descriptions-item>
        <t-descriptions-item v-if="chunk.chunk_type" label="类型">
          <t-tag size="small" :theme="getTypeTheme(chunk.chunk_type)">
            <t-icon :name="getTypeIcon(chunk.chunk_type)" size="12px" style="margin-right: 4px" />
            {{ getTypeName(chunk.chunk_type) }}
          </t-tag>
        </t-descriptions-item>
        <t-descriptions-item v-if="chunk.parent_id" label="父块">
          <t-button 
            theme="primary" 
            variant="text" 
            size="small"
            @click="showParentDetail"
          >
            查看父块内容
          </t-button>
        </t-descriptions-item>
      </t-descriptions>

      <!-- Type-specific metadata display -->
      <template v-if="chunk.chunk_type && chunk.chunk_type !== 'text'">
        <t-divider />
        
        <!-- Table metadata -->
        <div v-if="chunk.chunk_type === 'table'" class="type-metadata-section">
          <h4>
            <t-icon name="table" style="margin-right: 8px" />
            表格信息
          </h4>
          <t-descriptions :column="2" :colon="true" size="small">
            <t-descriptions-item label="表格序号">
              {{ chunk.metadata?.table_index + 1 || '-' }}
            </t-descriptions-item>
            <t-descriptions-item label="行数">
              {{ chunk.metadata?.row_count || '-' }}
            </t-descriptions-item>
            <t-descriptions-item label="列数">
              {{ chunk.metadata?.column_count || '-' }}
            </t-descriptions-item>
            <t-descriptions-item label="有表头">
              {{ chunk.metadata?.has_header ? '是' : '否' }}
            </t-descriptions-item>
            <t-descriptions-item v-if="chunk.metadata?.table_title" label="表格标题" :span="2">
              {{ chunk.metadata.table_title }}
            </t-descriptions-item>
            <t-descriptions-item v-if="chunk.metadata?.page_number" label="页码">
              {{ chunk.metadata.page_number }}
            </t-descriptions-item>
          </t-descriptions>
        </div>

        <!-- Image metadata -->
        <div v-if="chunk.chunk_type === 'image'" class="type-metadata-section">
          <h4>
            <t-icon name="image" style="margin-right: 8px" />
            图片信息
          </h4>
          <t-descriptions :column="2" :colon="true" size="small">
            <t-descriptions-item label="图片序号">
              {{ chunk.metadata?.image_index + 1 || '-' }}
            </t-descriptions-item>
            <t-descriptions-item v-if="chunk.metadata?.format" label="格式">
              {{ chunk.metadata.format.toUpperCase() }}
            </t-descriptions-item>
            <t-descriptions-item v-if="chunk.metadata?.width" label="尺寸">
              {{ chunk.metadata.width }} × {{ chunk.metadata.height || '?' }} px
            </t-descriptions-item>
            <t-descriptions-item v-if="chunk.metadata?.page_number" label="页码">
              {{ chunk.metadata.page_number }}
            </t-descriptions-item>
            <t-descriptions-item v-if="chunk.metadata?.alt_text" label="替代文本" :span="2">
              {{ chunk.metadata.alt_text }}
            </t-descriptions-item>
            <t-descriptions-item v-if="chunk.metadata?.caption" label="图片说明" :span="2">
              {{ chunk.metadata.caption }}
            </t-descriptions-item>
            <t-descriptions-item v-if="chunk.metadata?.image_path" label="图片路径" :span="2">
              <code>{{ chunk.metadata.image_path }}</code>
            </t-descriptions-item>
          </t-descriptions>
          
          <!-- Image preview if base64 is available -->
          <div v-if="chunk.metadata?.image_base64" class="image-preview">
            <h5>图片预览</h5>
            <img 
              :src="`data:image/${chunk.metadata.format || 'png'};base64,${chunk.metadata.image_base64}`"
              :alt="chunk.metadata.alt_text || '图片预览'"
              class="preview-image"
            />
          </div>
        </div>

        <!-- Code metadata -->
        <div v-if="chunk.chunk_type === 'code'" class="type-metadata-section">
          <h4>
            <t-icon name="code" style="margin-right: 8px" />
            代码信息
          </h4>
          <t-descriptions :column="2" :colon="true" size="small">
            <t-descriptions-item label="编程语言">
              <t-tag size="small" variant="light">
                {{ chunk.metadata?.language || 'text' }}
              </t-tag>
            </t-descriptions-item>
            <t-descriptions-item label="行数">
              {{ chunk.metadata?.end_line - chunk.metadata?.start_line + 1 || '-' }}
            </t-descriptions-item>
            <t-descriptions-item v-if="chunk.metadata?.function_name" label="函数名">
              <code>{{ chunk.metadata.function_name }}</code>
            </t-descriptions-item>
            <t-descriptions-item v-if="chunk.metadata?.class_name" label="类名">
              <code>{{ chunk.metadata.class_name }}</code>
            </t-descriptions-item>
            <t-descriptions-item v-if="chunk.metadata?.file_reference" label="文件引用" :span="2">
              <code>{{ chunk.metadata.file_reference }}</code>
            </t-descriptions-item>
            <t-descriptions-item label="完整代码块">
              {{ chunk.metadata?.is_complete_block ? '是' : '否' }}
            </t-descriptions-item>
          </t-descriptions>
        </div>
      </template>

      <!-- Parent chunk preview section -->
      <template v-if="chunk.parent_id && (parentChunk || loadingParent)">
        <t-divider />
        <div class="parent-section">
          <div class="section-header">
            <h4>父块内容</h4>
            <t-button
              v-if="parentChunk"
              theme="default"
              variant="text"
              size="small"
              @click="copyParentContent"
            >
              复制父块
            </t-button>
          </div>
          
          <t-loading v-if="loadingParent" size="small" />
          
          <div v-else-if="parentChunk" class="parent-content-box">
            <div class="parent-meta">
              <t-tag size="small" theme="warning" variant="light">
                父块 #{{ parentChunk.sequence_number + 1 }}
              </t-tag>
              <span class="parent-info">
                {{ parentChunk.content?.length || 0 }} 字符 · 
                {{ parentChunk.child_count }} 个子块
              </span>
            </div>
            <div 
              class="parent-text" 
              :class="{ 'expanded': parentExpanded }"
            >
              {{ parentChunk.content }}
            </div>
            <t-button
              v-if="parentChunk.content?.length > 500"
              theme="default"
              variant="text"
              size="small"
              block
              @click="parentExpanded = !parentExpanded"
            >
              {{ parentExpanded ? '收起' : '展开全部' }}
            </t-button>
          </div>
        </div>
      </template>

      <t-divider />

      <div class="content-section">
        <h4>内容</h4>
        <div 
          class="content-box"
          :class="{ 'code-content': chunk.chunk_type === 'code' }"
        >
          <pre v-if="chunk.chunk_type === 'code'"><code>{{ chunk.content }}</code></pre>
          <template v-else>{{ chunk.content }}</template>
        </div>
      </div>

      <t-divider />

      <div class="metadata-section">
        <h4>元数据</h4>
        <t-textarea
          :value="formatMetadata(chunk.chunk_metadata || chunk.metadata)"
          readonly
          :autosize="{ minRows: 3, maxRows: 10 }"
        />
      </div>
    </t-card>

    <!-- Parent chunk detail view -->
    <t-card v-else-if="selectedParentChunk" title="父块详情" :bordered="false">
      <template #actions>
        <t-space>
          <t-button
            theme="default"
            size="small"
            @click="copyParentContent"
          >
            <template #icon><t-icon name="file-copy" /></template>
            复制内容
          </t-button>
          <t-button
            theme="default"
            size="small"
            @click="$emit('close-parent')"
          >
            返回
          </t-button>
        </t-space>
      </template>

      <t-descriptions :column="2" :colon="true">
        <t-descriptions-item label="序号">
          父块 #{{ selectedParentChunk.sequence_number + 1 }}
        </t-descriptions-item>
        <t-descriptions-item label="字符数">
          {{ selectedParentChunk.content?.length || 0 }}
        </t-descriptions-item>
        <t-descriptions-item label="子块数量">
          {{ selectedParentChunk.child_count }}
        </t-descriptions-item>
        <t-descriptions-item label="起始位置">
          {{ selectedParentChunk.start_position || 0 }}
        </t-descriptions-item>
      </t-descriptions>

      <t-divider />

      <div class="content-section">
        <h4>完整内容</h4>
        <div class="content-box parent-full-content">
          {{ selectedParentChunk.content }}
        </div>
      </div>

      <t-divider />

      <div class="children-section">
        <h4>包含的子块 ({{ selectedParentChunk.child_count }} 个)</h4>
        <div v-if="selectedParentChunk.children?.length" class="children-list">
          <div 
            v-for="child in selectedParentChunk.children" 
            :key="child.id"
            class="child-item"
            @click="$emit('select-child', child)"
          >
            <t-tag size="small" theme="primary" variant="light">
              块 #{{ child.sequence_number + 1 }}
            </t-tag>
            <span class="child-preview">{{ child.content_preview }}</span>
          </div>
        </div>
        <t-empty v-else description="子块数据未加载" size="small" />
      </div>
    </t-card>

    <t-empty
      v-else
      description="请选择一个文本块查看详情"
    />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'

const props = defineProps({
  chunk: {
    type: Object,
    default: null
  },
  parentChunk: {
    type: Object,
    default: null
  },
  selectedParentChunk: {
    type: Object,
    default: null
  },
  loadingParent: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['load-parent', 'close-parent', 'select-child'])

const parentExpanded = ref(false)

// Type configuration
const typeConfig = {
  text: { name: '文本', theme: 'primary', icon: 'file-text' },
  table: { name: '表格', theme: 'success', icon: 'table' },
  image: { name: '图片', theme: 'warning', icon: 'image' },
  code: { name: '代码', theme: 'danger', icon: 'code' }
}

// Reset parent expanded state when chunk changes
watch(() => props.chunk, () => {
  parentExpanded.value = false
})

const copyContent = async () => {
  if (!props.chunk?.content) return

  try {
    await navigator.clipboard.writeText(props.chunk.content)
    MessagePlugin.success('内容已复制到剪贴板')
  } catch (error) {
    MessagePlugin.error('复制失败')
  }
}

const copyParentContent = async () => {
  const content = props.parentChunk?.content || props.selectedParentChunk?.content
  if (!content) return

  try {
    await navigator.clipboard.writeText(content)
    MessagePlugin.success('父块内容已复制到剪贴板')
  } catch (error) {
    MessagePlugin.error('复制失败')
  }
}

const showParentDetail = () => {
  if (props.chunk?.parent_id) {
    emit('load-parent', props.chunk.parent_id)
  }
}

const formatMetadata = (metadata) => {
  if (!metadata) return '{}'
  return JSON.stringify(metadata, null, 2)
}

const getTypeTheme = (type) => {
  return typeConfig[type]?.theme || 'default'
}

const getTypeIcon = (type) => {
  return typeConfig[type]?.icon || 'file'
}

const getTypeName = (type) => {
  return typeConfig[type]?.name || type
}
</script>

<style scoped>
.chunk-detail {
  height: 100%;
}

.chunk-detail :deep(.t-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chunk-detail :deep(.t-card__body) {
  flex: 1;
  overflow-y: auto;
}

.content-section,
.metadata-section,
.parent-section,
.children-section,
.type-metadata-section {
  margin-top: 16px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.content-section h4,
.metadata-section h4,
.parent-section h4,
.children-section h4,
.type-metadata-section h4 {
  margin-bottom: 12px;
  font-weight: 500;
  font-size: 14px;
  color: var(--td-text-color-primary);
  display: flex;
  align-items: center;
}

.section-header h4 {
  margin-bottom: 0;
}

.content-box {
  padding: 16px;
  background-color: var(--td-bg-color-container);
  border: 1px solid var(--td-component-border);
  border-radius: 6px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 500px;
  overflow-y: auto;
  font-size: 14px;
}

.content-box.code-content {
  background-color: #1e1e1e;
  color: #d4d4d4;
  font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
  font-size: 13px;
}

.content-box.code-content pre {
  margin: 0;
}

.content-box.code-content code {
  font-family: inherit;
}

.parent-full-content {
  max-height: 600px;
}

.metadata-section :deep(.t-textarea__inner) {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
}

.chunk-detail :deep(.t-empty) {
  padding: 60px 0;
}

/* Parent content styles */
.parent-content-box {
  background-color: var(--td-bg-color-page);
  border: 1px solid var(--td-component-border);
  border-radius: 6px;
  overflow: hidden;
}

.parent-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background-color: var(--td-bg-color-container);
  border-bottom: 1px solid var(--td-component-border);
}

.parent-info {
  font-size: 12px;
  color: var(--td-text-color-secondary);
}

.parent-text {
  padding: 12px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  max-height: 200px;
  overflow: hidden;
  position: relative;
}

.parent-text:not(.expanded)::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: linear-gradient(transparent, var(--td-bg-color-page));
}

.parent-text.expanded {
  max-height: none;
}

.parent-text.expanded::after {
  display: none;
}

/* Children list styles */
.children-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.child-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background-color: var(--td-bg-color-container);
  border: 1px solid var(--td-component-border);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.child-item:hover {
  background-color: var(--td-bg-color-container-hover);
  border-color: var(--td-brand-color);
}

.child-preview {
  font-size: 12px;
  color: var(--td-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

/* Type-specific metadata styles */
.type-metadata-section {
  background-color: var(--td-bg-color-page);
  border-radius: 6px;
  padding: 16px;
}

.type-metadata-section :deep(.t-descriptions) {
  background-color: transparent;
}

/* Image preview styles */
.image-preview {
  margin-top: 16px;
}

.image-preview h5 {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 8px;
  color: var(--td-text-color-secondary);
}

.preview-image {
  max-width: 100%;
  max-height: 300px;
  border: 1px solid var(--td-component-border);
  border-radius: 4px;
  object-fit: contain;
}
</style>
