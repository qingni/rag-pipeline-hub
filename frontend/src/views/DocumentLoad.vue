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
            <t-option-group label="PDF 加载器">
              <t-option value="pymupdf" label="PyMuPDF" />
              <t-option value="pypdf" label="PyPDF" />
              <t-option value="unstructured" label="Unstructured" />
            </t-option-group>
            <t-option-group label="Office 文档">
              <t-option value="docx" label="DOCX" />
              <t-option value="doc" label="DOC" />
            </t-option-group>
            <t-option-group label="文本文档">
              <t-option value="text" label="Text/Markdown" />
            </t-option-group>
          </t-select>
          
          <!-- 加载器提示 -->
          <t-alert 
            v-if="loaderHint"
            theme="info" 
            :message="loaderHint"
            style="margin-top: 12px"
          />
        </div>
        
        <!-- 开始加载按钮 -->
        <div v-if="selectedDocument" class="section">
          <t-divider style="margin: 16px 0" />
          
          <t-button
            theme="primary"
            block
            size="large"
            :loading="loading"
            @click="loadDocument"
          >
            <template #icon>
              <PlayIcon :size="18" />
            </template>
            {{ loading ? '加载中...' : '开始加载' }}
          </t-button>
        </div>
        
        <!-- 处理进度 -->
        <ProcessingProgress :status="status" :error="error" />
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
        
        <!-- 文档预览 -->
        <t-card v-if="selectedDocument" title="文档预览" :bordered="false" class="content-card">
          <DocumentPreview :document-id="selectedDocument.id" />
        </t-card>
        
        <!-- 加载结果 -->
        <t-card v-if="loadResult" title="加载结果" :bordered="false" class="content-card">
          <template #actions>
            <t-button 
              variant="text" 
              size="small"
              @click="downloadResult"
            >
              <template #icon>
                <DownloadIcon :size="16" />
              </template>
              下载结果
            </t-button>
          </template>
          <ResultPreview :result="loadResult" />
        </t-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useProcessingStore } from '../stores/processing'
import { 
  FileText as FileTextIcon,
  Play as PlayIcon,
  Download as DownloadIcon
} from 'lucide-vue-next'
import DocumentUploader from '../components/document/DocumentUploader.vue'
import DocumentList from '../components/document/DocumentList.vue'
import DocumentPreview from '../components/document/DocumentPreview.vue'
import ProcessingProgress from '../components/processing/ProcessingProgress.vue'
import ResultPreview from '../components/processing/ResultPreview.vue'

const processingStore = useProcessingStore()

const selectedDocument = ref(null)
const loaderType = ref('')
const loading = ref(false)
const status = ref('idle')
const error = ref(null)
const loadResult = ref(null)

const formatLoaderMap = {
  'pdf': 'pymupdf',
  'docx': 'docx',
  'doc': 'doc',
  'txt': 'text',
  'md': 'text',
  'markdown': 'text'
}

const loaderHint = computed(() => {
  if (!loaderType.value) {
    return '系统会根据文件格式自动选择最佳加载器'
  }
  
  const hints = {
    'pymupdf': '适用于 PDF，提供最佳性能和文本提取质量',
    'pypdf': '适用于 PDF，轻量级纯 Python 实现',
    'unstructured': '适用于复杂文档结构，支持表格和布局识别',
    'docx': '适用于 Microsoft Word DOCX 文档',
    'doc': '适用于旧版 Microsoft Word DOC 文档',
    'text': '适用于纯文本和 Markdown 文件'
  }
  
  return hints[loaderType.value] || ''
})

watch(selectedDocument, (newDoc) => {
  if (newDoc && newDoc.format) {
    const format = newDoc.format.toLowerCase()
    const defaultLoader = formatLoaderMap[format]
    
    if (defaultLoader) {
      loaderType.value = defaultLoader
      console.log(`自动选择加载器: ${defaultLoader} (文件格式: ${format})`)
    } else {
      loaderType.value = ''
    }
  }
})

function handleUploadComplete(document) {
  selectedDocument.value = document
  console.log('上传完成，已选中文档:', document.filename)
}

function handleSelectDocument(document) {
  selectedDocument.value = document
  console.log('选中文档:', document.filename)
  status.value = 'idle'
  error.value = null
  loadResult.value = null
}

function handleDeleteDocument(documentId) {
  if (selectedDocument.value?.id === documentId) {
    selectedDocument.value = null
    loaderType.value = ''
    status.value = 'idle'
    error.value = null
    loadResult.value = null
  }
}

async function loadDocument() {
  if (!selectedDocument.value) return
  
  loading.value = true
  status.value = 'processing'
  error.value = null
  
  try {
    const result = await processingStore.loadDocument(
      selectedDocument.value.id,
      loaderType.value || undefined
    )
    
    loadResult.value = result
    status.value = 'completed'
  } catch (err) {
    error.value = err.message
    status.value = 'failed'
  } finally {
    loading.value = false
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
</style>
