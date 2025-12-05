<template>
  <div class="chunking-view">
    <t-layout>
      <!-- Left Panel: Configuration (Always Visible) -->
      <t-aside width="420px" class="left-panel">
        <div class="panel-content">
          <t-space direction="vertical" size="medium" style="width: 100%">
            <!-- Document Selection -->
            <DocumentSelector />

            <!-- Strategy Selection -->
            <StrategySelector />

            <!-- Parameter Configuration -->
            <ParameterConfig />

            <!-- Action Button -->
            <t-card :bordered="false">
              <t-button
                block
                theme="primary"
                size="large"
                :disabled="!canStartChunking"
                :loading="isProcessing"
                @click="handleStartChunking"
              >
                {{ isProcessing ? '处理中...' : '开始分块' }}
              </t-button>
            </t-card>
          </t-space>
        </div>
      </t-aside>

      <!-- Main Content: Tabs for Current Task and History -->
      <t-content class="main-content">
        <t-tabs v-model="activeTab" @change="handleTabChange" class="full-height-tabs">
          <!-- Tab 1: Current Task / Results View -->
          <t-tab-panel value="current" label="分块结果" class="tab-panel-content">
            <div class="current-task-container">
              <!-- Progress Display -->
              <ChunkingProgress
                v-if="currentTask"
                :task="currentTask"
                @view-result="handleViewResult"
                @retry="handleRetry"
              />

              <!-- Results Display -->
              <template v-if="hasResult">
                <!-- Result Header Info -->
                <t-card :bordered="false" class="result-header">
                  <t-space>
                    <t-tag theme="primary" variant="light">
                      文档: {{ currentResult?.document_name || '未知' }}
                    </t-tag>
                    <t-tag theme="success" variant="light">
                      策略: {{ getStrategyLabel(currentResult?.strategy_type) }}
                    </t-tag>
                    <t-tag theme="warning" variant="light">
                      共 {{ chunksTotalCount }} 个分块
                    </t-tag>
                  </t-space>
                </t-card>

                <t-row :gutter="16" class="results-row">
                  <!-- Chunk List -->
                  <t-col :span="12">
                    <ChunkList
                      :chunks="chunks"
                      :total-count="chunksTotalCount"
                      :page="chunksPage"
                      :page-size="chunksPageSize"
                      :selected-chunk-id="selectedChunk?.id"
                      :loading="resultLoading"
                      @select="handleSelectChunk"
                      @page-change="handleChunkPageChange"
                    />
                  </t-col>

                  <!-- Chunk Detail -->
                  <t-col :span="12">
                    <ChunkDetail :chunk="selectedChunk" />
                  </t-col>
                </t-row>
              </template>

              <!-- Empty State -->
              <t-card v-else-if="!currentTask" :bordered="false" class="empty-state-card">
                <t-empty description="请在左侧配置并开始分块操作，或在历史记录中查看已完成的分块结果" />
              </t-card>
            </div>
          </t-tab-panel>

          <!-- Tab 2: History -->
          <t-tab-panel value="history" label="历史记录" class="tab-panel-content">
            <HistoryList
              @view="handleViewHistory"
            />
          </t-tab-panel>
        </t-tabs>
      </t-content>
    </t-layout>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { useChunkingStore } from '@/stores/chunkingStore'
import { MessagePlugin } from 'tdesign-vue-next'
import DocumentSelector from '@/components/chunking/DocumentSelector.vue'
import StrategySelector from '@/components/chunking/StrategySelector.vue'
import ParameterConfig from '@/components/chunking/ParameterConfig.vue'
import ChunkingProgress from '@/components/chunking/ChunkingProgress.vue'
import ChunkList from '@/components/chunking/ChunkList.vue'
import ChunkDetail from '@/components/chunking/ChunkDetail.vue'
import HistoryList from '@/components/chunking/HistoryList.vue'

const chunkingStore = useChunkingStore()

// Tab state
const activeTab = ref('current')

// Computed states
const canStartChunking = computed(() => {
  return chunkingStore.hasSelectedDocument && chunkingStore.hasSelectedStrategy
})

const isProcessing = computed(() => chunkingStore.isChunking)

const currentTask = computed(() => chunkingStore.currentTask)

const currentResult = computed(() => chunkingStore.currentResult)

const hasResult = computed(() => {
  return chunkingStore.currentResult && chunkingStore.chunks.length > 0
})

const chunks = computed(() => chunkingStore.chunks)
const chunksTotalCount = computed(() => chunkingStore.chunksTotalCount)
const chunksPage = computed(() => chunkingStore.chunksPage)
const chunksPageSize = computed(() => chunkingStore.chunksPageSize)
const selectedChunk = computed(() => chunkingStore.selectedChunk)
const resultLoading = computed(() => chunkingStore.resultLoading)

// Helper functions
const getStrategyLabel = (type) => {
  const labels = {
    'CHARACTER': '按字数',
    'PARAGRAPH': '按段落',
    'HEADING': '按标题',
    'SEMANTIC': '按语义',
    'character': '按字数',
    'paragraph': '按段落',
    'heading': '按标题',
    'semantic': '按语义'
  }
  return labels[type] || type
}

// Actions
const handleStartChunking = async () => {
  try {
    await chunkingStore.createChunkingTask()
    MessagePlugin.success('分块任务已创建，正在处理中...')
    // Switch to current tab to show progress
    activeTab.value = 'current'
  } catch (error) {
    MessagePlugin.error(error.message || '创建任务失败')
  }
}

const handleViewResult = async (resultId) => {
  try {
    await chunkingStore.loadChunkingResult(resultId)
    // Auto-select first chunk for preview
    if (chunkingStore.chunks.length > 0) {
      chunkingStore.selectChunk(chunkingStore.chunks[0])
    }
  } catch (error) {
    MessagePlugin.error('加载结果失败')
  }
}

const handleViewHistory = async (resultId) => {
  try {
    await chunkingStore.loadChunkingResult(resultId)
    // Auto-select first chunk for preview
    if (chunkingStore.chunks.length > 0) {
      chunkingStore.selectChunk(chunkingStore.chunks[0])
    }
    // Switch to current tab to show results
    activeTab.value = 'current'
    MessagePlugin.success('历史记录加载成功')
  } catch (error) {
    MessagePlugin.error('加载历史记录失败')
  }
}

const handleRetry = () => {
  handleStartChunking()
}

const handleSelectChunk = (chunk) => {
  chunkingStore.selectChunk(chunk)
}

const handleChunkPageChange = async ({ page }) => {
  if (chunkingStore.currentResult) {
    await chunkingStore.loadChunkingResult(
      chunkingStore.currentResult.result_id,
      page
    )
  }
}

const handleTabChange = (value) => {
  console.log('Tab changed to:', value)
}

// Watch for task completion to auto-load results
watch(() => chunkingStore.currentTask?.status, (newStatus, oldStatus) => {
  if (newStatus === 'completed' && oldStatus === 'processing') {
    MessagePlugin.success('分块任务完成！')
  } else if (newStatus === 'failed' && oldStatus === 'processing') {
    MessagePlugin.error('分块任务失败，请检查错误信息')
  }
})

// Cleanup on unmount
onUnmounted(() => {
  chunkingStore.stopTaskPolling()
})
</script>

<style scoped>
.chunking-view {
  height: 100vh;
  background-color: var(--td-bg-color-page);
}

.left-panel {
  background-color: var(--td-bg-color-container);
  border-right: 1px solid var(--td-component-border);
  overflow-y: auto;
  height: 100vh;
}

.panel-content {
  padding: 20px 16px;
}

.main-content {
  padding: 0;
  overflow-y: auto;
  height: 100vh;
}

/* 标签页全高度布局 */
.full-height-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.full-height-tabs :deep(.t-tabs__nav-container) {
  padding: 16px 24px 0;
  background-color: var(--td-bg-color-container);
}

.full-height-tabs :deep(.t-tabs__content) {
  flex: 1;
  overflow: hidden;
}

.tab-panel-content {
  height: 100%;
  overflow-y: auto;
  padding: 0px 24px 24px;
}

/* 当前任务容器 */
.current-task-container {
  max-width: 1400px;
  margin: 0 auto;
}

/* 结果头部信息 */
.result-header {
  margin-bottom: 16px;
  padding: 12px 0 0;
}

.result-header :deep(.t-card__body) {
  padding: 16px 24px 0px 24px;
}

/* 结果行样式 */
.results-row {
  margin-top: 0;
}

/* 空状态卡片 */
.empty-state-card {
  min-height: 400px;
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
