<template>
  <div class="chunking-view">
    <t-layout>
      <!-- Left Panel: Configuration (Always Visible) -->
      <t-aside width="380px" class="left-panel">
        <div class="panel-content">
          <t-space direction="vertical" size="medium" style="width: 100%">
            <!-- Panel Header -->
            <div class="panel-header">
              <SplitSquareHorizontal :size="22" class="panel-icon" />
              <h2 class="panel-title">文档分块</h2>
            </div>

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
                :disabled="!canStartChunking || isProcessing"
                :loading="isProcessing"
                @click="handleStartChunking"
              >
                {{ isProcessing ? '分块处理中...' : '开始分块' }}
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
                  <div class="result-header-content">
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
                  </div>
                  <!-- 结果文件路径 -->
                  <div v-if="currentResult?.file_path" class="result-file-path">
                    <t-icon name="file" size="14px" />
                    <span class="file-path-label">结果文件:</span>
                    <t-tooltip :content="currentResult.file_path" placement="top">
                      <span class="file-path-text">{{ currentResult.file_path }}</span>
                    </t-tooltip>
                  </div>
                </t-card>

                <!-- 可视化视图 -->
                <div class="visualization-container">
                <ChunkVisualizer
                    :chunks="chunks"
                    :parent-chunks="parentChunks"
                    :strategy-type="currentResult?.strategy_type"
                    :document-name="currentResult?.document_name"
                    :external-statistics="externalStatistics"
                    @chunk-click="handleSelectChunk"
                    @load-parent="handleLoadParentDetail"
                    @refresh="handleRefreshResult"
                  />
                </div>
              </template>

              <!-- Empty State -->
              <template v-else-if="!currentTask">
                <div class="empty-state-container">
                  <t-card :bordered="false" class="empty-state-card">
                    <t-empty description="请在左侧配置并开始分块操作，或在历史记录中查看已完成的分块结果">
                      <template #image>
                        <t-icon name="chart-pie" size="64px" style="color: var(--td-text-color-placeholder)" />
                      </template>
                    </t-empty>
                  </t-card>
                </div>
              </template>
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
import { SplitSquareHorizontal } from 'lucide-vue-next'
import { useChunkingStore } from '@/stores/chunkingStore'
import { MessagePlugin } from 'tdesign-vue-next'
import DocumentSelector from '@/components/chunking/DocumentSelector.vue'
import StrategySelector from '@/components/chunking/StrategySelector.vue'
import ParameterConfig from '@/components/chunking/ParameterConfig.vue'
import ChunkingProgress from '@/components/chunking/ChunkingProgress.vue'
import HistoryList from '@/components/chunking/HistoryList.vue'
import { ChunkVisualizer } from '@/components/chunking/visualization'

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

// 父块相关
const parentChunks = computed(() => chunkingStore.parentChunks)

// 统计数据：使用后端返回的统计信息，避免分页导致的数据不完整问题
const externalStatistics = computed(() => {
  if (!chunkingStore.currentResult) return null
  
  const result = chunkingStore.currentResult
  const stats = result.statistics || {}
  
  // 合并后端统计数据和前端需要的字段
  const baseStats = {
    total_chunks: result.total_chunks || chunkingStore.chunksTotalCount,
    total_characters: stats.total_characters || 0,
    avg_chunk_size: stats.avg_chunk_size || 0,
    min_chunk_size: stats.min_chunk_size || 0,
    max_chunk_size: stats.max_chunk_size || 0,
    size_distribution: stats.size_distribution || []
  }
  
  // 父子块统计：后端保存的是扁平结构，前端组件需要嵌套结构
  if (chunkingStore.isParentChildResult) {
    baseStats.parent_child_stats = {
      parent_count: stats.parent_count || 0,
      child_count: stats.child_count || result.total_chunks || 0,
      avg_parent_size: stats.avg_parent_size || 0,
      avg_children_per_parent: stats.avg_children_per_parent || 0
    }
  }
  
  return baseStats
})

// Helper functions
const getStrategyLabel = (type) => {
  const labels = {
    'CHARACTER': '按字数',
    'PARAGRAPH': '按段落',
    'HEADING': '按标题',
    'SEMANTIC': '按语义',
    'PARENT_CHILD': '父子分块',
    'HYBRID': '混合分块',
    'character': '按字数',
    'paragraph': '按段落',
    'heading': '按标题',
    'semantic': '按语义',
    'parent_child': '父子分块',
    'hybrid': '混合分块'
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
    // 如果是父子分块，加载父块
    if (chunkingStore.isParentChildResult) {
      await chunkingStore.loadParentChunks()
    }
  } catch (error) {
    MessagePlugin.error('加载结果失败')
  }
}

const handleViewHistory = async (resultId) => {
  try {
    await chunkingStore.loadChunkingResult(resultId)
    // 如果是父子分块，加载父块
    if (chunkingStore.isParentChildResult) {
      await chunkingStore.loadParentChunks()
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

const handleLoadParentDetail = async (parentId) => {
  try {
    await chunkingStore.getParentWithChildren(parentId)
  } catch (error) {
    console.error('加载父块详情失败:', error)
  }
}

const handleRefreshResult = async () => {
  if (chunkingStore.currentResult) {
    await handleViewResult(chunkingStore.currentResult.result_id)
  }
}

const handleTabChange = (value) => {
  console.log('Tab changed to:', value)
}

// Watch for task completion to auto-load results
watch(() => chunkingStore.currentTask?.status, async (newStatus, oldStatus) => {
  if (newStatus === 'completed' && oldStatus === 'processing') {
    MessagePlugin.success('分块任务完成！')
    // 如果是父子分块，自动加载父块
    if (chunkingStore.isParentChildResult) {
      await chunkingStore.loadParentChunks()
    }
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

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 4px;
}

.panel-icon {
  color: #8B5CF6;
  flex-shrink: 0;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.left-panel {
  background-color: var(--td-bg-color-container);
  border-right: 1px solid var(--td-component-border);
  overflow-y: auto;
  height: 100vh;
  flex-shrink: 0;
  min-width: 380px;
  max-width: 380px;
}

.panel-content {
  padding: 20px 16px;
  width: 100%;
  box-sizing: border-box;
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
  max-width: 1600px;
  margin: 0 auto;
}

/* 结果头部信息 */
.result-header {
  margin-bottom: 16px;
  padding: 12px 0 0;
}

.result-header :deep(.t-card__body) {
  padding: 0px 24px 0px 24px;
}

.result-header-content {
  display: flex;
  justify-content: flex-start;
  align-items: center;
}

/* 结果文件路径样式 */
.result-file-path {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--td-component-stroke);
  font-size: 13px;
  color: var(--td-text-color-secondary);
}

.result-file-path .file-path-label {
  color: var(--td-text-color-placeholder);
  flex-shrink: 0;
}

.result-file-path .file-path-text {
  color: var(--td-text-color-secondary);
  font-family: 'SF Mono', Monaco, Menlo, Consolas, monospace;
  font-size: 12px;
  max-width: 500px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.result-file-path .file-path-text:hover {
  color: var(--td-brand-color);
}

/* 可视化容器 */
.visualization-container {
  background: var(--td-bg-color-container);
  border-radius: 8px;
  min-height: 600px;
  overflow: hidden;
}

/* 空状态容器 */
.empty-state-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 500px;
}

.empty-state-card {
  width: 100%;
  max-width: 600px;
}

.empty-state-card :deep(.t-card__body) {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 40px;
}
</style>
