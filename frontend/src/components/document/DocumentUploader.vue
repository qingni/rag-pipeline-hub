<template>
  <div class="document-uploader">
    <t-upload
      v-model="files"
      :auto-upload="false"
      :draggable="true"
      :accept="acceptedFormats"
      :max="1"
      :size-limit="{ size: MAX_FILE_SIZE, unit: 'B' }"
      :before-upload="handleBeforeUpload"
      :disabled="uploading"
      @change="handleFileChange"
      theme="file"
    >
      <template #drag-content>
        <div class="upload-area">
          <UploadCloudIcon :size="32" class="upload-icon" />
          <p class="upload-text">点击上传 / 拖拽到此区域</p>
        </div>
      </template>
    </t-upload>
    
    <!-- 文件格式提示 -->
    <div class="upload-tips">
      <p class="tips-text">
        支持格式: PDF, DOCX, XLSX, PPTX, HTML, CSV, JSON, XML, TXT, MD 等 20+ 种格式 (最大50MB)
        <br />
        <span class="tips-feature">大文件自动启用断点续传</span>
      </p>
    </div>
    
    <!-- 上传进度 -->
    <div v-if="uploading" class="progress-section">
      <!-- 阶段指示器 -->
      <div class="phase-indicator">
        <div 
          class="phase-item" 
          :class="{ active: uploadPhase === 'hashing', done: phaseOrder > 0 }"
        >
          <HashIcon :size="14" />
          <span>计算哈希</span>
        </div>
        <ChevronRightIcon :size="14" class="phase-arrow" />
        <div 
          class="phase-item" 
          :class="{ active: uploadPhase === 'uploading', done: phaseOrder > 1 }"
        >
          <UploadIcon :size="14" />
          <span>上传文件</span>
        </div>
        <ChevronRightIcon :size="14" class="phase-arrow" />
        <div 
          class="phase-item" 
          :class="{ active: uploadPhase === 'completing', done: phaseOrder > 2 }"
        >
          <CheckCircleIcon :size="14" />
          <span>完成</span>
        </div>
      </div>
      
      <t-progress 
        :percentage="displayProgress" 
        :status="uploadStatus"
        :label="progressLabel"
      />
      
      <!-- 取消按钮 -->
      <div class="upload-actions">
        <t-button 
          v-if="canCancel"
          theme="default" 
          variant="text" 
          size="small"
          @click="cancelUpload"
        >
          <XIcon :size="14" />
          取消上传
        </t-button>
      </div>
    </div>
    
    <!-- 错误提示 -->
    <t-alert 
      v-if="error" 
      theme="error" 
      :message="error"
      class="mt-3"
      close
      @close="error = null"
    />
    
    <!-- 成功提示 -->
    <t-alert 
      v-if="uploadSuccess" 
      theme="success" 
      :message="successMessage"
      class="mt-3"
      close
      @close="uploadSuccess = false"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useDocumentStore } from '../../stores/document'
import { useLoadingQueueStore } from '../../stores/loadingQueueStore'
import chunkedUploadService from '../../services/chunkedUploadService'
import { 
  UploadCloud as UploadCloudIcon,
  Hash as HashIcon,
  Upload as UploadIcon,
  CheckCircle as CheckCircleIcon,
  ChevronRight as ChevronRightIcon,
  X as XIcon
} from 'lucide-vue-next'

const documentStore = useDocumentStore()
const loadingQueueStore = useLoadingQueueStore()

// State
const files = ref([])
const uploading = ref(false)
const uploadPhase = ref('idle') // idle, hashing, uploading, completing
const hashProgress = ref(0)
const uploadProgress = ref(0)
const error = ref(null)
const uploadSuccess = ref(false)
const successMessage = ref('文档上传成功')

// 取消控制器
let abortController = null

const emit = defineEmits(['upload-complete'])

// 常量
const MAX_FILE_SIZE = 52428800 // 50MB
const LARGE_FILE_THRESHOLD = 10 * 1024 * 1024 // 10MB，超过此大小使用分片上传
const acceptedFormats = '.pdf,.doc,.docx,.txt,.md,.markdown,.xlsx,.xls,.pptx,.ppt,.html,.htm,.csv,.json,.xml,.rtf,.odt,.ods,.odp'

// Computed
const phaseOrder = computed(() => {
  const phases = ['idle', 'hashing', 'uploading', 'completing', 'done']
  return phases.indexOf(uploadPhase.value)
})

const displayProgress = computed(() => {
  if (uploadPhase.value === 'hashing') {
    return Math.round(hashProgress.value * 0.1) // 哈希计算占 10%
  } else if (uploadPhase.value === 'uploading') {
    return 10 + Math.round(uploadProgress.value * 0.85) // 上传占 85%
  } else if (uploadPhase.value === 'completing') {
    return 95
  }
  return 0
})

const progressLabel = computed(() => {
  if (uploadPhase.value === 'hashing') {
    return `计算文件哈希... ${hashProgress.value}%`
  } else if (uploadPhase.value === 'uploading') {
    return `上传中... ${uploadProgress.value}%`
  } else if (uploadPhase.value === 'completing') {
    return '正在完成...'
  }
  return ''
})

const uploadStatus = computed(() => {
  if (error.value) return 'error'
  if (uploadSuccess.value) return 'success'
  if (uploading.value) return 'active'
  return 'default'
})

const canCancel = computed(() => {
  return uploading.value && uploadPhase.value !== 'completing'
})

// Methods
function validateFile(file) {
  const allowedExtensions = [
    '.pdf', '.doc', '.docx',
    '.txt', '.md', '.markdown',
    '.xlsx', '.xls',
    '.pptx', '.ppt',
    '.html', '.htm',
    '.csv', '.json', '.xml',
    '.rtf',
    '.odt', '.ods', '.odp'
  ]
  const fileExt = '.' + file.name.split('.').pop().toLowerCase()
  
  if (!allowedExtensions.includes(fileExt)) {
    throw new Error(`不支持的文件格式: ${fileExt}`)
  }
  
  if (file.size > MAX_FILE_SIZE) {
    throw new Error(`文件大小超过限制 (最大50MB)`)
  }
  
  if (file.size === 0) {
    throw new Error('文件为空')
  }
  
  const existingDoc = documentStore.documents.find(
    doc => doc.filename === file.name
  )
  if (existingDoc) {
    throw new Error(`文件"${file.name}"已存在，请勿重复上传`)
  }
  
  return true
}

function handleBeforeUpload(file) {
  try {
    validateFile(file.raw)
    return true
  } catch (err) {
    error.value = err.message
    return false
  }
}

async function handleFileChange(fileList) {
  if (fileList.length === 0) return
  
  const file = fileList[0].raw
  
  // 根据文件大小选择上传方式
  if (file.size > LARGE_FILE_THRESHOLD) {
    await uploadLargeFile(file)
  } else {
    await uploadSmallFile(file)
  }
}

/**
 * 小文件上传（使用原有方式）
 */
async function uploadSmallFile(file) {
  try {
    resetState()
    uploading.value = true
    uploadPhase.value = 'uploading'
    uploadProgress.value = 0
    
    // 暂停轮询，减少并发请求
    loadingQueueStore.pausePolling()
    
    console.log('[DocumentUploader] 开始小文件上传:', file.name, file.size)
    
    const document = await documentStore.uploadDocument(file, (progress) => {
      console.log('[DocumentUploader] 上传进度:', progress)
      uploadProgress.value = progress
    })
    
    // 确保进度显示 100%
    uploadProgress.value = 100
    
    console.log('[DocumentUploader] 上传完成:', document)
    
    uploadSuccess.value = true
    successMessage.value = '文档上传成功'
    emit('upload-complete', document)
    
    clearFiles()
    
  } catch (err) {
    console.error('[DocumentUploader] 上传失败:', err)
    error.value = err.message || '上传失败'
  } finally {
    uploading.value = false
    uploadPhase.value = 'idle'
    // 恢复轮询
    loadingQueueStore.resumePolling()
  }
}

/**
 * 大文件上传（使用分片上传）
 */
async function uploadLargeFile(file) {
  abortController = new AbortController()
  
  try {
    resetState()
    uploading.value = true
    
    // 暂停轮询，减少并发请求
    loadingQueueStore.pausePolling()
    
    const result = await chunkedUploadService.uploadWithResume(file, {
      onHashProgress: (progress) => {
        hashProgress.value = progress
      },
      onUploadProgress: (progress) => {
        uploadProgress.value = progress
      },
      onPhaseChange: (phase) => {
        uploadPhase.value = phase
      },
      signal: abortController.signal
    })
    
    if (result.success) {
      uploadSuccess.value = true
      
      if (result.instant_upload) {
        successMessage.value = '秒传成功！文件已存在'
      } else {
        successMessage.value = '文档上传成功'
      }
      
      // 刷新文档列表
      await documentStore.fetchDocuments(1)
      
      emit('upload-complete', result.document)
      clearFiles()
    }
    
  } catch (err) {
    if (err.message === '上传已取消') {
      // 用户取消，不显示错误
      return
    }
    error.value = err.message || '上传失败'
  } finally {
    uploading.value = false
    uploadPhase.value = 'idle'
    abortController = null
    // 恢复轮询
    loadingQueueStore.resumePolling()
  }
}

function cancelUpload() {
  if (abortController) {
    abortController.abort()
  }
}

function resetState() {
  error.value = null
  uploadSuccess.value = false
  hashProgress.value = 0
  uploadProgress.value = 0
  uploadPhase.value = 'idle'
}

function clearFiles() {
  setTimeout(() => {
    files.value = []
  }, 1000)
}

// Watch upload progress for small files
documentStore.$subscribe((_mutation, state) => {
  if (uploading.value && uploadPhase.value === 'uploading' && !abortController) {
    uploadProgress.value = state.uploadProgress
  }
})
</script>

<style scoped>
.document-uploader {
  width: 100%;
}

.upload-area {
  padding: 24px 16px;
  text-align: center;
  min-height: 100px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.upload-icon {
  margin: 0 auto 12px;
  color: #9ca3af;
  display: block;
}

.upload-text {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin: 0;
  display: block;
}

.upload-tips {
  margin-top: 8px;
  text-align: center;
}

.tips-text {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
  line-height: 1.5;
}

.tips-feature {
  color: #667eea;
  font-weight: 500;
}

/* 进度区域 */
.progress-section {
  margin-top: 12px;
}

/* 阶段指示器 */
.phase-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 12px;
}

.phase-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: #9ca3af;
  background: #f5f5f5;
  transition: all 0.3s;
}

.phase-item.active {
  color: #667eea;
  background: #eef2ff;
  font-weight: 500;
}

.phase-item.done {
  color: #52c41a;
  background: #f6ffed;
}

.phase-arrow {
  color: #d9d9d9;
}

/* 上传操作 */
.upload-actions {
  margin-top: 8px;
  text-align: center;
}

.mt-3 {
  margin-top: 12px;
}
</style>
