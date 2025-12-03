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
            <option value="pymupdf">PyMuPDF (推荐)</option>
            <option value="pypdf">PyPDF</option>
            <option value="unstructured">Unstructured</option>
          </select>
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
          <DocumentList @select="handleSelectDocument" />
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
import { ref } from 'vue'
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
const loaderType = ref('pymupdf')
const loading = ref(false)
const status = ref('idle')
const error = ref(null)
const loadResult = ref(null)

function handleUploadComplete(document) {
  selectedDocument.value = document
}

function handleSelectDocument(document) {
  selectedDocument.value = document
}

async function loadDocument() {
  if (!selectedDocument.value) return
  
  loading.value = true
  status.value = 'processing'
  error.value = null
  
  try {
    const result = await processingStore.loadDocument(
      selectedDocument.value.id,
      loaderType.value
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
