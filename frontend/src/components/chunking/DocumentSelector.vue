<template>
  <div class="document-selector">
    <t-card title="选择文档" :bordered="false">
      <template #actions>
        <t-button theme="primary" size="small" @click="loadDocuments">
          <template #icon><t-icon name="refresh" /></template>
          刷新
        </t-button>
      </template>

      <t-loading :loading="loading" size="small">
        <t-radio-group v-model="selectedDocId" @change="handleSelect">
          <t-space direction="vertical" size="medium" style="width: 100%">
            <t-radio
              v-for="doc in documents"
              :key="doc.id"
              :value="doc.id"
              :disabled="false"
            >
              <div class="doc-item">
                <div class="doc-name">{{ doc.filename }}</div>
                <div class="doc-meta">
                  <t-tag size="small" theme="primary">{{ doc.format }}</t-tag>
                  <span class="doc-size">{{ formatSize(doc.size_bytes) }}</span>
                  <span class="doc-time">{{ formatTime(doc.upload_time) }}</span>
                </div>
              </div>
            </t-radio>
          </t-space>
        </t-radio-group>

        <t-empty
          v-if="!loading && documents.length === 0"
          description="暂无已解析的文档"
        />
      </t-loading>
    </t-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useChunkingStore } from '@/stores/chunkingStore'
import { MessagePlugin } from 'tdesign-vue-next'

const chunkingStore = useChunkingStore()

const loading = computed(() => chunkingStore.documentsLoading)
const documents = computed(() => chunkingStore.parsedDocuments)
const selectedDocId = ref(null)

const loadDocuments = async () => {
  try {
    await chunkingStore.loadParsedDocuments()
    console.log('Loaded documents:', chunkingStore.parsedDocuments.length, chunkingStore.parsedDocuments)
  } catch (error) {
    console.error('加载文档列表失败:', error)
    MessagePlugin.error('加载文档列表失败')
  }
}

const handleSelect = (docId) => {
  const doc = chunkingStore.parsedDocuments.find(d => d.id === docId)
  if (doc) {
    chunkingStore.selectDocument(doc)
  }
}

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

onMounted(() => {
  loadDocuments()
})
</script>

<style scoped>
.document-selector {
  margin-bottom: 20px;
}

.document-selector :deep(.t-card__body) {
  padding: 16px 12px;
}

.document-selector :deep(.t-radio) {
  align-items: flex-start;
  padding: 8px 0;
}

.document-selector :deep(.t-radio__label) {
  flex: 1;
  min-width: 0;
}

.doc-item {
  width: 100%;
  line-height: 1.4;
  min-width: 0;
}

.doc-name {
  font-weight: 500;
  margin-bottom: 6px;
  font-size: 13px;
  word-break: break-all;
  overflow-wrap: break-word;
  line-height: 1.5;
}

.doc-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--td-text-color-secondary);
  line-height: 1.5;
}

.doc-size, .doc-time {
  font-size: 11.5px;
  white-space: nowrap;
}
</style>
