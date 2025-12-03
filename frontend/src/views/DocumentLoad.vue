<template>
  <div class="flex flex-1">
    <ControlPanel title="文档加载" description="上传文档并选择加载方式">
      <div class="space-y-6">
        <!-- Upload section -->
        <div>
          <DocumentUploader @upload-complete="handleUploadComplete" />
        </div>
        
        <!-- Loader selection -->
        <div v-if="selectedDocument">
          <label class="block text-sm font-semibold mb-2">加载方式</label>
          <select v-model="loaderType" class="input-field">
            <option value="">自动选择 (推荐)</option>
            <optgroup label="PDF 加载器">
              <option value="pymupdf">PyMuPDF</option>
              <option value="pypdf">PyPDF</option>
              <option value="unstructured">Unstructured</option>
            </optgroup>
            <optgroup label="Office 文档加载器">
              <option value="docx">DOCX</option>
              <option value="doc">DOC</option>
            </optgroup>
            <optgroup label="文本加载器">
              <option value="text">Text/Markdown</option>
            </optgroup>
          </select>
          <p class="text-xs text-gray-500 mt-1">
            <span v-if="loaderType === ''">系统会根据文件格式自动选择最佳加载器</span>
            <span v-else-if="loaderType === 'pymupdf'">适用于 PDF,提供最佳性能</span>
            <span v-else-if="loaderType === 'pypdf'">适用于 PDF,轻量级方案</span>
            <span v-else-if="loaderType === 'unstructured'">适用于复杂文档结构</span>
            <span v-else-if="loaderType === 'docx'">适用于 DOCX 文档</span>
            <span v-else-if="loaderType === 'doc'">适用于旧版 DOC 文档</span>
            <span v-else-if="loaderType === 'text'">适用于 TXT 和 Markdown 文件</span>
          </p>
        </div>
        
        <!-- Load button -->
        <div v-if="selectedDocument">
          <button
            class="btn-primary w-full"
            :disabled="loading"
            @click="loadDocument"
          >
            <span v-if="!loading">开始加载</span>
            <span v-else class="flex items-center justify-center">
              <span class="spinner mr-2"></span>
              加载中...
            </span>
          </button>
        </div>
        
        <!-- Progress -->
        <ProcessingProgress :status="status" :error="error" />
      </div>
    </ControlPanel>
    
    <div class="flex-1 flex flex-col">
      <ContentArea title="文档管理">
        <!-- Document list -->
        <div class="mb-6">
          <DocumentList 
            @select="handleSelectDocument"
            @delete="handleDeleteDocument"
          />
        </div>
        
        <!-- Preview -->
        <div v-if="selectedDocument">
          <h3 class="text-lg font-semibold mb-4">文档预览</h3>
          <DocumentPreview :document-id="selectedDocument.id" />
        </div>
        
        <!-- Result -->
        <div v-if="loadResult" class="mt-6">
          <h3 class="text-lg font-semibold mb-4">加载结果</h3>
          <ResultPreview :result="loadResult" />
        </div>
      </ContentArea>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useProcessingStore } from '../stores/processing'
import ControlPanel from '../components/layout/ControlPanel.vue'
import ContentArea from '../components/layout/ContentArea.vue'
import DocumentUploader from '../components/document/DocumentUploader.vue'
import DocumentList from '../components/document/DocumentList.vue'
import DocumentPreview from '../components/document/DocumentPreview.vue'
import ProcessingProgress from '../components/processing/ProcessingProgress.vue'
import ResultPreview from '../components/processing/ResultPreview.vue'

const processingStore = useProcessingStore()

const selectedDocument = ref(null)
const loaderType = ref('') // Empty string for auto-selection
const loading = ref(false)
const status = ref('idle')
const error = ref(null)
const loadResult = ref(null)

// 格式到默认加载器的映射
const formatLoaderMap = {
  'pdf': 'pymupdf',
  'docx': 'docx',
  'doc': 'doc',
  'txt': 'text',
  'md': 'text',
  'markdown': 'text'
}

// 监听选中的文档变化，自动切换加载器
watch(selectedDocument, (newDoc) => {
  if (newDoc && newDoc.format) {
    const format = newDoc.format.toLowerCase()
    const defaultLoader = formatLoaderMap[format]
    
    // 自动切换到对应的加载器（如果存在映射）
    if (defaultLoader) {
      loaderType.value = defaultLoader
      console.log(`自动选择加载器: ${defaultLoader} (文件格式: ${format})`)
    } else {
      // 未知格式，使用自动选择
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
  // 重置状态
  status.value = 'idle'
  error.value = null
  loadResult.value = null
}

async function handleDeleteDocument(documentId) {
  // 如果删除的是当前选中的文档，清空选择
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
      loaderType.value || undefined // Pass undefined for auto-selection
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
</script>
