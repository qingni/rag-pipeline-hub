<template>
  <div class="generation-page">
    <div class="page-header">
      <h2 class="page-title">
        <BotMessageSquare class="title-icon" :size="24" />
        文本生成
      </h2>
      <p class="page-description">基于 RAG 检索结果和大语言模型生成智能回答</p>
    </div>
    
    <!-- Tab 切换 -->
    <div class="tab-container">
      <t-tabs v-model="activeTab">
        <t-tab-panel value="generate" label="生成">
          <template #label>
            <div class="tab-label">
              <Sparkles :size="16" />
              <span>生成</span>
            </div>
          </template>
        </t-tab-panel>
        <t-tab-panel value="history" label="历史">
          <template #label>
            <div class="tab-label">
              <History :size="16" />
              <span>历史记录</span>
            </div>
          </template>
        </t-tab-panel>
      </t-tabs>
    </div>
    
    <!-- 生成页面 -->
    <div v-show="activeTab === 'generate'" class="generation-layout">
      <!-- 左侧配置面板 -->
      <div class="config-panel">
        <GenerationConfig 
          v-model:model="selectedModel"
          v-model:temperature="temperature"
          v-model:maxTokens="maxTokens"
          v-model:collectionIds="selectedCollectionIds"
          v-model:topK="topK"
          :models="availableModels"
          :available-collections="availableCollections"
          :is-loading-collections="isLoadingCollections"
          :disabled="isGenerating || isRetrieving"
        />
        
        <!-- 检索状态 -->
        <div class="context-section" v-if="isRetrieving">
          <h4 class="section-title">正在检索...</h4>
          <div class="context-count">
            <t-loading size="small" />
            <span>从知识库检索相关文档</span>
          </div>
        </div>
        
        <!-- 上下文信息 -->
        <div class="context-section" v-else-if="hasContext">
          <h4 class="section-title">检索上下文</h4>
          <div class="context-count">
            <FileText :size="16" />
            <span>{{ context.length }} 个文档片段</span>
          </div>
          <t-button 
            variant="text" 
            size="small" 
            @click="clearContext"
            :disabled="isGenerating"
          >
            清除上下文
          </t-button>
        </div>
      </div>
      
      <!-- 右侧主内容区 -->
      <div class="main-content">
        <!-- 输入区域 -->
        <GenerationInput
          v-model="question"
          :loading="isGenerating || isRetrieving"
          :disabled="isGenerating || isRetrieving"
          @generate="handleGenerate"
          @cancel="handleCancel"
        />
        
        <!-- 结果展示区 -->
        <GenerationResult
          :content="generatedContent"
          :loading="isGenerating"
          :error="generationError"
          :tokenUsage="tokenUsage"
          :processingTime="processingTime"
          @retry="handleRetry"
        />
        
        <!-- 来源引用 -->
        <SourceReference
          v-if="sources.length > 0"
          :sources="sources"
        />
      </div>
    </div>
    
    <!-- 历史记录页面 -->
    <div v-show="activeTab === 'history'" class="history-layout">
      <GenerationHistory
        :items="historyList"
        :total="historyTotal"
        :page="historyPage"
        :page-size="historyPageSize"
        :loading="historyLoading"
        @refresh="handleHistoryRefresh"
        @delete="handleHistoryDelete"
        @clear="handleHistoryClear"
        @page-change="handleHistoryPageChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { BotMessageSquare, FileText, History } from 'lucide-vue-next'
import { MessagePlugin } from 'tdesign-vue-next'
import { useGenerationStore } from '../stores/generationStore'
import { storeToRefs } from 'pinia'
import GenerationInput from '../components/Generation/GenerationInput.vue'
import GenerationConfig from '../components/Generation/GenerationConfig.vue'
import GenerationResult from '../components/Generation/GenerationResult.vue'
import SourceReference from '../components/Generation/SourceReference.vue'
import GenerationHistory from '../components/Generation/GenerationHistory.vue'

const store = useGenerationStore()

// Store state
const {
  isGenerating,
  isRetrieving,
  generatedContent,
  generationError,
  tokenUsage,
  processingTime,
  availableModels,
  selectedModel,
  temperature,
  maxTokens,
  context,
  sources,
  hasContext,
  historyList,
  historyTotal,
  historyPage,
  historyPageSize,
  historyLoading,
  availableCollections,
  isLoadingCollections,
  selectedCollectionIds,
  topK,
} = storeToRefs(store)

// Local state
const question = ref('')
const activeTab = ref('generate')

// Load models on mount
onMounted(() => {
  store.loadModels()
  store.loadAvailableCollections()
})

// Load history when switching to history tab
watch(activeTab, (newTab) => {
  if (newTab === 'history') {
    store.loadHistory()
  }
})

// Handlers
async function handleGenerate() {
  if (!question.value.trim()) return
  await store.generateStream(question.value)
}

function handleCancel() {
  store.cancelGeneration()
}

async function handleRetry() {
  if (!question.value.trim()) return
  await store.generateStream(question.value)
}

function clearContext() {
  store.clearContext()
}

// History handlers
async function handleHistoryRefresh() {
  try {
    await store.loadHistory()
    MessagePlugin.success('刷新成功')
  } catch (error) {
    MessagePlugin.error('刷新失败')
  }
}

async function handleHistoryDelete(id) {
  try {
    await store.deleteHistoryItem(id)
    MessagePlugin.success('删除成功')
  } catch (error) {
    MessagePlugin.error('删除失败')
  }
}

async function handleHistoryClear() {
  try {
    await store.clearAllHistory()
    MessagePlugin.success('已清空所有历史记录')
  } catch (error) {
    MessagePlugin.error('清空失败')
  }
}

function handleHistoryPageChange(page) {
  store.loadHistory({ page })
}
</script>

<style scoped>
.generation-page {
  padding: 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page-header {
  margin-bottom: 16px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 8px 0;
}

.title-icon {
  color: #6366f1;
}

.page-description {
  color: #6b7280;
  margin: 0;
}

.tab-container {
  margin-bottom: 16px;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.generation-layout {
  display: flex;
  gap: 24px;
  flex: 1;
  overflow: hidden;
}

.config-panel {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  max-height: 100%;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

.context-section {
  background: #f9fafb;
  border-radius: 8px;
  padding: 16px;
}

.section-title {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin: 0 0 12px 0;
}

.context-count {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6b7280;
  font-size: 14px;
  margin-bottom: 8px;
}

.history-layout {
  flex: 1;
  overflow: hidden;
}
</style>
