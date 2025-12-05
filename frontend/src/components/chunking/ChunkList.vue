<template>
  <div class="chunk-list">
    <t-card title="分块列表" :bordered="false">
      <template #actions>
        <t-space>
          <span class="total-count">共 {{ totalCount }} 个</span>
        </t-space>
      </template>

      <t-loading :loading="loading" size="small">
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
      </t-loading>
    </t-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  chunks: {
    type: Array,
    default: () => []
  },
  totalCount: {
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
  }
})

const emit = defineEmits(['select', 'page-change'])

const currentPage = ref(props.page)
const currentPageSize = ref(props.pageSize)

const handleSelect = (chunk) => {
  emit('select', chunk)
}

const handlePageChange = ({ current, pageSize }) => {
  emit('page-change', { page: current, pageSize })
}

const getPreviewText = (content) => {
  if (!content) return ''
  const preview = content.substring(0, 100)
  return preview + (content.length > 100 ? '...' : '')
}
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
</style>
