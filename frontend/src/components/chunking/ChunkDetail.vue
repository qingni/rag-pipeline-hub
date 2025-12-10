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
      </t-descriptions>

      <t-divider />

      <div class="content-section">
        <h4>内容</h4>
        <div class="content-box">
          {{ chunk.content }}
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

    <t-empty
      v-else
      description="请选择一个文本块查看详情"
    />
  </div>
</template>

<script setup>
import { MessagePlugin } from 'tdesign-vue-next'

const props = defineProps({
  chunk: {
    type: Object,
    default: null
  }
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

const formatMetadata = (metadata) => {
  if (!metadata) return '{}'
  return JSON.stringify(metadata, null, 2)
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
.metadata-section {
  margin-top: 16px;
}

.content-section h4,
.metadata-section h4 {
  margin-bottom: 12px;
  font-weight: 500;
  font-size: 14px;
  color: var(--td-text-color-primary);
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

.metadata-section :deep(.t-textarea__inner) {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
}

.chunk-detail :deep(.t-empty) {
  padding: 60px 0;
}
</style>
