<template>
  <div class="document-load-container">
    <!-- 左侧控制面板 -->
    <div class="left-panel">
      <div class="left-panel-content">
        <!-- 标题 -->
        <div class="panel-header">
          <h2 class="panel-title">
            <FileTextIcon :size="20" class="title-icon" />
            文档加载
          </h2>
          <p class="panel-subtitle">上传文档并选择加载方式</p>
        </div>

        <t-divider style="margin: 16px 0" />
        
        <!-- 上传区域 -->
        <div class="section">
          <h3 class="section-title">上传文档</h3>
          <DocumentUploader @upload-complete="handleUploadComplete" />
        </div>
        
        <!-- 加载器选择 -->
        <div v-if="selectedDocument" class="section">
          <t-divider style="margin: 16px 0" />
          
          <h3 class="section-title">加载方式</h3>
          
          <!-- Docling 状态提示 -->
          <t-alert 
            v-if="doclingStatus && doclingStatus !== 'ready'"
            :theme="doclingStatus === 'initializing' ? 'warning' : 'info'"
            style="margin-bottom: 12px"
          >
            <template #message>
              <div class="flex items-center">
                <div v-if="doclingStatus === 'initializing'" class="spinner-small mr-2"></div>
                <span>
                  {{ doclingStatusText }}
                </span>
              </div>
            </template>
          </t-alert>
          
          <t-select 
            v-model="loaderType" 
            placeholder="请选择加载方式"
            style="width: 100%"
          >
            <t-option value="" label="自动选择 (推荐)">
              <div class="flex items-center justify-between">
                <span>自动选择</span>
                <t-tag size="small" theme="success" variant="light">推荐</t-tag>
              </div>
            </t-option>
            <t-option-group label="高质量解析">
              <t-option 
                value="docling" 
                :label="doclingOptionLabel"
                :disabled="doclingStatus === 'unavailable'"
              />
            </t-option-group>
            <t-option-group label="PDF 加载器">
              <t-option value="pymupdf" label="PyMuPDF (快速)" />
              <t-option value="pypdf" label="PyPDF (轻量)" />
            </t-option-group>
            <t-option-group label="Office 文档">
              <t-option value="docx" label="DOCX" />
              <t-option value="xlsx" label="XLSX/XLS" />
              <t-option value="pptx" label="PPTX" />
            </t-option-group>
            <t-option-group label="数据格式">
              <t-option value="html" label="HTML" />
              <t-option value="csv" label="CSV" />
              <t-option value="json" label="JSON" />
              <t-option value="xml" label="XML" />
            </t-option-group>
            <t-option-group label="其他格式">
              <t-option value="text" label="Text/Markdown" />
            </t-option-group>
            <t-option-group label="通用解析器">
              <t-option value="unstructured" label="Unstructured (通用)" />
            </t-option-group>
          </t-select>
          
          <!-- 加载器提示 -->
          <t-alert 
            v-if="loaderHint"
            theme="info" 
            :message="loaderHint"
            style="margin-top: 12px"
          />
          
          <!-- 大文件警告 -->
          <t-alert 
            v-if="isLargeFile"
            theme="warning" 
            style="margin-top: 12px"
          >
            <template #message>
              <div>
                <strong>大文件提示：</strong>文件大小为 {{ formatFileSize(selectedDocument.size) }}
                <br />
                <span style="font-size: 12px; color: #666;">
                  复杂文档使用 Docling 解析可能需要 1-5 分钟，如需快速处理可选择 PyMuPDF
                </span>
              </div>
            </template>
          </t-alert>
        </div>
        
        <!-- 开始加载按钮 -->
        <div v-if="selectedDocument" class="section">
          <t-divider style="margin: 16px 0" />
          
          <!-- 异步模式提示 -->
          <t-alert 
            v-if="shouldUseAsync && !taskQueued"
            theme="info" 
            style="margin-bottom: 12px"
          >
            <template #message>
              <div style="font-size: 12px;">
                <strong>异步模式：</strong>{{ asyncModeHint }}
              </div>
            </template>
          </t-alert>
          
          <!-- 任务已加入队列提示 -->
          <div v-if="taskQueued" class="queue-success-section">
            <div class="queue-success-header">
              <CheckCircleIcon :size="20" class="queue-success-icon" />
              <span class="queue-success-title">已加入处理队列</span>
            </div>
            <p class="queue-success-hint">
              任务正在后台处理中，您可以继续上传其他文档。
              <br />
              点击右下角的队列按钮查看处理进度。
            </p>
            <div class="queue-success-actions">
              <t-button
                variant="outline"
                size="small"
                @click="resetForNewTask"
              >
                <template #icon>
                  <PlusIcon :size="16" />
                </template>
                继续上传
              </t-button>
              <t-button
                variant="text"
                theme="danger"
                size="small"
                @click="cancelQueuedTask"
              >
                <template #icon>
                  <XCircleIcon :size="16" />
                </template>
                取消任务
              </t-button>
            </div>
          </div>
          
          <!-- 加载按钮 -->
          <t-button
            v-if="!taskQueued"
            theme="primary"
            block
            size="large"
            :loading="loading"
            @click="loadDocument"
          >
            <template #icon>
              <PlayIcon :size="18" />
            </template>
            {{ loading ? '提交中...' : '开始加载' }}
          </t-button>
        </div>
        
        <!-- 处理进度 - 仅在非队列模式时显示 -->
        <ProcessingProgress v-if="!taskQueued" :status="status" :error="error" />
      </div>
    </div>
    
    <!-- 右侧内容区域 -->
    <div class="right-panel">
      <div class="right-panel-content">
        <!-- 文档列表 -->
        <t-card title="文档管理" :bordered="false" class="content-card">
          <DocumentList 
            @select="handleSelectDocument"
            @delete="handleDeleteDocument"
          />
        </t-card>
        
        <!-- 文档预览和加载结果 - Tab 切换 -->
        <t-card v-if="selectedDocument" :bordered="false" class="content-card preview-card">
          <t-tabs v-model="activeTab" size="medium" class="preview-tabs">
            <t-tab-panel value="preview">
              <template #label>
                <div class="tab-label">
                  <FileTextIcon :size="16" />
                  <span>文档预览</span>
                </div>
              </template>
              <div class="tab-content">
                <DocumentPreview :document-id="selectedDocument.id" />
              </div>
            </t-tab-panel>
            <t-tab-panel 
              value="result" 
              :disabled="!loadResult"
            >
              <template #label>
                <div class="tab-label">
                  <component :is="loadResult ? CheckCircleIcon : CircleIcon" :size="16" />
                  <span>{{ loadResult ? '加载结果' : '加载结果（无）' }}</span>
                </div>
              </template>
              <div v-if="loadResult" class="tab-content">
                <!-- 降级通知 -->
                <FallbackNotice 
                  :load-result="loadResult"
                  :visible="showFallbackNotice"
                  @close="showFallbackNotice = false"
                />
                <ResultPreview :result="loadResult">
                  <template #actions>
                    <t-button 
                      variant="outline" 
                      size="small"
                      @click="downloadResult"
                    >
                      <template #icon>
                        <DownloadIcon :size="16" />
                      </template>
                      下载结果
                    </t-button>
                  </template>
                </ResultPreview>
              </div>
            </t-tab-panel>
          </t-tabs>
        </t-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useProcessingStore } from '../stores/processing'
import { useDocumentStore } from '../stores/document'
import healthService from '../services/healthService'
import { 
  FileText as FileTextIcon,
  Play as PlayIcon,
  Download as DownloadIcon,
  CheckCircle as CheckCircleIcon,
  Circle as CircleIcon,
  XCircle as XCircleIcon,
  Plus as PlusIcon
} from 'lucide-vue-next'
import { useLoadingQueueStore } from '../stores/loadingQueueStore'
import DocumentUploader from '../components/document/DocumentUploader.vue'
import DocumentList from '../components/document/DocumentList.vue'
import DocumentPreview from '../components/document/DocumentPreview.vue'
import FallbackNotice from '../components/document/FallbackNotice.vue'
import ProcessingProgress from '../components/processing/ProcessingProgress.vue'
import ResultPreview from '../components/processing/ResultPreview.vue'

const processingStore = useProcessingStore()
const documentStore = useDocumentStore()
const loadingQueueStore = useLoadingQueueStore()

const selectedDocument = ref(null)
const loaderType = ref('')
const loading = ref(false)
const status = ref('idle')
const error = ref(null)
const loadResult = ref(null)
const activeTab = ref('preview') // Tab 切换状态
const showFallbackNotice = ref(true) // 降级通知显示状态

// 任务队列状态
const taskQueued = ref(false)
const queuedTaskId = ref(null)

// Docling 状态
const doclingStatus = ref(null)
let healthCheckInterval = null

// 检查系统健康状态
async function checkHealth() {
  try {
    const health = await healthService.getHealth()
    if (health.success && health.components?.docling) {
      doclingStatus.value = health.components.docling.status
    }
  } catch (err) {
    console.warn('Health check failed:', err)
  }
}

onMounted(() => {
  // 立即检查一次
  checkHealth()
  
  // 每 5 秒检查一次健康状态
  healthCheckInterval = setInterval(checkHealth, 5000)
  
  // 监听任务完成事件，刷新文档列表
  window.addEventListener('loading-task-complete', handleTaskComplete)
})

onUnmounted(() => {
  if (healthCheckInterval) {
    clearInterval(healthCheckInterval)
  }
  window.removeEventListener('loading-task-complete', handleTaskComplete)
})

// 处理任务完成事件
function handleTaskComplete(event) {
  console.log('[DocumentLoad] 任务完成事件:', event.detail)
  // 刷新文档列表
  documentStore.fetchDocuments()
}

const doclingStatusText = computed(() => {
  switch (doclingStatus.value) {
    case 'initializing':
      return 'Docling 正在初始化中，请稍候...'
    case 'available':
      return 'Docling 可用，但尚未初始化'
    case 'unavailable':
      return 'Docling 不可用'
    case 'ready':
      return 'Docling 已就绪'
    default:
      return ''
  }
})

const doclingOptionLabel = computed(() => {
  switch (doclingStatus.value) {
    case 'initializing':
      return 'Docling (初始化中...)'
    case 'unavailable':
      return 'Docling (不可用)'
    case 'ready':
      return 'Docling (高精度，较慢)'
    default:
      return 'Docling (高精度，较慢)'
  }
})

// 判断是否应该使用异步模式
const shouldUseAsync = computed(() => {
  if (!selectedDocument.value) return false
  
  const loader = loaderType.value || 'auto'
  const format = selectedDocument.value.format?.toLowerCase()
  
  // Docling 始终使用异步
  if (loader === 'docling' || loader === 'docling_serve') {
    return true
  }
  
  // 自动模式下，复杂格式始终使用异步（因为后端会使用 Docling Serve）
  // 这些格式的主要解析器是 docling_serve，处理时间较长
  if (loader === 'auto' || loader === '') {
    const complexFormats = ['pdf', 'docx', 'doc', 'pptx', 'ppt']
    if (complexFormats.includes(format)) {
      return true
    }
  }
  
  return false
})

// 异步模式提示
const asyncModeHint = computed(() => {
  if (!shouldUseAsync.value) return ''
  
  const format = selectedDocument.value?.format?.toLowerCase()
  const complexFormats = ['pdf', 'docx', 'doc', 'pptx', 'ppt']
  
  if (complexFormats.includes(format)) {
    return '复杂文档将使用 Docling 高精度解析，任务将加入队列在后台处理'
  }
  
  return '将使用异步模式加载，您可以在加载过程中进行其他操作'
})

const formatLoaderMap = {
  'pdf': 'docling',
  'docx': 'docling',
  'doc': 'docx',
  'xlsx': 'xlsx',
  'xls': 'xlsx',
  'pptx': 'pptx',
  'html': 'html',
  'htm': 'html',
  'csv': 'csv',
  'json': 'json',
  'xml': 'xml',
  'msg': 'msg',
  'vtt': 'vtt',
  'txt': 'text',
  'md': 'text',
  'markdown': 'text'
}

const loaderHint = computed(() => {
  if (!loaderType.value) {
    return '复杂文档 (PDF/DOCX/XLSX/PPTX) 优先使用 Docling 解析，其他格式使用专用加载器'
  }
  
  const hints = {
    'docling': 'Docling 提供高精度表格和结构化内容提取，适合复杂文档，但处理较慢',
    'pymupdf': '适用于 PDF，提供最佳性能和文本提取质量，推荐用于大文件',
    'pypdf': '适用于 PDF，轻量级纯 Python 实现',
    'docx': '适用于 Microsoft Word DOCX 文档',
    'xlsx': '适用于 Microsoft Excel XLSX/XLS 文档',
    'pptx': '适用于 Microsoft PowerPoint PPTX 文档',
    'html': '适用于 HTML 网页文档',
    'csv': '适用于 CSV 表格数据',
    'json': '适用于 JSON 数据文件',
    'xml': '适用于 XML 数据文件',
    'text': '适用于纯文本和 Markdown 文件',
    'unstructured': '通用解析器，支持多种格式，作为其他解析器的降级备选'
  }
  
  return hints[loaderType.value] || ''
})

// 大文件阈值 (2MB)
const LARGE_FILE_THRESHOLD = 2 * 1024 * 1024

const isLargeFile = computed(() => {
  if (!selectedDocument.value) return false
  return selectedDocument.value.size > LARGE_FILE_THRESHOLD
})

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024
    i++
  }
  return `${bytes.toFixed(2)} ${units[i]}`
}

watch(selectedDocument, (newDoc) => {
  if (newDoc && newDoc.format) {
    // 保持自动选择模式，不自动设置具体加载器
    // 用户可以手动选择特定加载器
    loaderType.value = ''
    console.log(`文档已选择: ${newDoc.filename} (格式: ${newDoc.format})，使用自动选择模式`)
  }
})

function handleUploadComplete(document) {
  selectedDocument.value = document
  console.log('上传完成，已选中文档:', document.filename)
}

async function handleSelectDocument(document) {
  selectedDocument.value = document
  console.log('选中文档:', document.filename, '状态:', document.status)
  status.value = 'idle'
  error.value = null
  loadResult.value = null
  activeTab.value = 'preview' // 切换到文档预览 tab
  taskQueued.value = false
  queuedTaskId.value = null
  
  // 如果文档状态为就绪，自动加载最新的加载结果
  if (document.status === 'ready') {
    try {
      const results = await processingStore.fetchResults(document.id, 'load')
      // 获取最新的加载结果
      if (results && results.length > 0) {
        const latestResult = results[0]
        // 通过结果ID获取完整的结果数据（包含result_data）
        const fullResult = await processingStore.fetchResultById(latestResult.id)
        if (fullResult) {
          // fullResult 包含 processing_result 的所有字段 + result_data
          loadResult.value = fullResult
          status.value = 'completed'
          console.log('已加载处理结果:', fullResult)
        }
      }
    } catch (err) {
      console.error('加载处理结果失败:', err)
      // 不显示错误，只是不显示结果
    }
  }
}

function handleDeleteDocument(documentId) {
  if (selectedDocument.value?.id === documentId) {
    selectedDocument.value = null
    loaderType.value = ''
    status.value = 'idle'
    error.value = null
    loadResult.value = null
    taskQueued.value = false
    queuedTaskId.value = null
  }
}

async function loadDocument() {
  if (!selectedDocument.value) return
  
  loading.value = true
  status.value = 'processing'
  error.value = null
  
  // 判断是否使用异步模式（加入队列）
  if (shouldUseAsync.value) {
    await loadDocumentAsync()
  } else {
    await loadDocumentSync()
  }
}

// 同步加载
async function loadDocumentSync() {
  try {
    const result = await processingStore.loadDocument(
      selectedDocument.value.id,
      loaderType.value || undefined
    )
    
    loadResult.value = result
    status.value = 'completed'
    
    // 刷新文档列表以更新状态
    await documentStore.fetchDocuments(documentStore.currentPage)
    
    // 更新选中的文档信息
    const updatedDoc = documentStore.documents.find(d => d.id === selectedDocument.value.id)
    if (updatedDoc) {
      selectedDocument.value = updatedDoc
    }
    
    // 自动切换到加载结果 tab
    activeTab.value = 'result'
  } catch (err) {
    error.value = err.message
    status.value = 'failed'
  } finally {
    loading.value = false
  }
}

// 异步加载 - 加入队列
async function loadDocumentAsync() {
  try {
    console.log('[DocumentLoad] 开始提交异步任务...')
    
    // 1. 提交异步任务
    const taskData = await processingStore.loadDocumentAsync(
      selectedDocument.value.id,
      loaderType.value || 'docling_serve'
    )
    
    console.log('[DocumentLoad] 异步任务提交成功:', taskData)
    
    if (!taskData || !taskData.task_id) {
      throw new Error('服务器返回的任务数据无效')
    }
    
    queuedTaskId.value = taskData.task_id
    taskQueued.value = true
    status.value = 'idle' // 重置状态，允许继续操作
    loading.value = false
    
    // 2. 将任务添加到队列 Store 进行统一管理
    // 重要：必须传递 external_task_id，用于区分异步任务并正确轮询状态
    loadingQueueStore.addTask({
      task_id: taskData.task_id,
      external_task_id: taskData.external_task_id,  // Docling Serve 返回的外部任务 ID
      document_id: selectedDocument.value.id,
      document_name: selectedDocument.value.filename,
      loader_type: loaderType.value || 'docling_serve',
      status: 'pending',
      progress: 0,
      created_at: new Date().toISOString()
    })
    
    // 3. 开始队列轮询（如果尚未开始）
    loadingQueueStore.startPolling()
    
    console.log('[DocumentLoad] 任务已加入队列:', taskData.task_id, 'external:', taskData.external_task_id)
    
  } catch (err) {
    error.value = err.message
    status.value = 'failed'
    loading.value = false
    taskQueued.value = false
  }
}

// 重置以便继续上传新任务
function resetForNewTask() {
  selectedDocument.value = null
  loaderType.value = ''
  status.value = 'idle'
  error.value = null
  loadResult.value = null
  taskQueued.value = false
  queuedTaskId.value = null
}

// 取消已加入队列的任务
async function cancelQueuedTask() {
  if (!queuedTaskId.value) return
  
  try {
    await processingStore.cancelTask(queuedTaskId.value)
    loadingQueueStore.removeTask(queuedTaskId.value)
    
    taskQueued.value = false
    queuedTaskId.value = null
    status.value = 'idle'
  } catch (err) {
    console.error('取消任务失败:', err)
  }
}

function downloadResult() {
  if (!loadResult.value) return
  
  const dataStr = JSON.stringify(loadResult.value, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${selectedDocument.value.filename}_load_result.json`
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.document-load-container {
  display: flex;
  height: 100%;
  width: 100%;
  overflow: hidden;
}

.left-panel {
  width: 360px;
  min-width: 360px;
  max-width: 360px;
  height: 100%;
  border-right: 1px solid #e5e7eb;
  background-color: #ffffff;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.left-panel-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 20px;
}

.panel-header {
  margin-bottom: 0;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  display: flex;
  align-items: center;
  margin-bottom: 4px;
}

.title-icon {
  margin-right: 8px;
  color: #3b82f6;
}

.panel-subtitle {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
}

.section {
  margin-top: 0;
}

.section-title {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 12px;
}

.right-panel {
  flex: 1;
  height: 100%;
  background-color: #f9fafb;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.right-panel-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 20px;
}

.content-card {
  margin-bottom: 20px;
}

.content-card:last-child {
  margin-bottom: 0;
}

/* Tab 样式优化 */
.preview-card {
  overflow: hidden;
}

.preview-tabs {
  margin: -24px -24px 0 -24px;
}

.preview-tabs :deep(.t-tabs__nav-container) {
  padding: 0 24px;
  background-color: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.preview-tabs :deep(.t-tabs__nav) {
  background-color: transparent;
  justify-content: flex-start;
}

.preview-tabs :deep(.t-tabs__nav-item) {
  padding: 12px 20px;
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  transition: all 0.2s ease;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  flex-shrink: 0;
}

.preview-tabs :deep(.t-tabs__nav-item:first-child) {
  margin-left: 0;
}

.preview-tabs :deep(.t-tabs__nav-item:hover) {
  color: #374151;
  background-color: rgba(59, 130, 246, 0.05);
}

.preview-tabs :deep(.t-tabs__nav-item.t-is-active) {
  color: #3b82f6;
  font-weight: 600;
  border-bottom-color: #3b82f6;
}

.preview-tabs :deep(.t-tabs__nav-item.t-is-disabled) {
  color: #d1d5db;
  cursor: not-allowed;
  opacity: 0.6;
}

/* 移除 TDesign 默认的激活指示器 */
.preview-tabs :deep(.t-tabs__nav-item-wrapper) {
  border: none !important;
}

.preview-tabs :deep(.t-tabs__bar) {
  display: none !important;
}

.preview-tabs :deep(.t-tabs__content) {
  padding: 0;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab-content {
  padding: 0px 24px 24px;
}

.content-card:last-child {
  margin-bottom: 0;
}

/* 优化滚动条样式 */
.left-panel-content::-webkit-scrollbar,
.right-panel-content::-webkit-scrollbar {
  width: 6px;
}

.left-panel-content::-webkit-scrollbar-track,
.right-panel-content::-webkit-scrollbar-track {
  background: transparent;
}

.left-panel-content::-webkit-scrollbar-thumb,
.right-panel-content::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.left-panel-content::-webkit-scrollbar-thumb:hover,
.right-panel-content::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

/* 小型加载动画 */
.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 异步加载进度样式 */
.async-progress-section {
  background-color: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-label {
  font-size: 14px;
  font-weight: 500;
  color: #0369a1;
}

.progress-value {
  font-size: 14px;
  font-weight: 600;
  color: #0284c7;
}

.progress-hint {
  font-size: 12px;
  color: #6b7280;
  margin-top: 8px;
  margin-bottom: 0;
}

/* 任务已加入队列成功提示样式 */
.queue-success-section {
  background-color: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
}

.queue-success-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.queue-success-icon {
  color: #16a34a;
}

.queue-success-title {
  font-size: 14px;
  font-weight: 600;
  color: #15803d;
}

.queue-success-hint {
  font-size: 12px;
  color: #6b7280;
  margin: 0 0 12px 0;
  line-height: 1.5;
}

.queue-success-actions {
  display: flex;
  gap: 8px;
}
</style>
