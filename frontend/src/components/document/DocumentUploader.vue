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
      <p class="tips-text">支持格式: PDF, DOC, DOCX, TXT, Markdown (最大50MB)</p>
    </div>
    
    <!-- 上传进度 -->
    <div v-if="uploading" class="mt-3">
      <t-progress 
        :percentage="progress" 
        :status="uploadStatus"
      />
      <p class="text-xs text-gray-500 mt-1 text-center">{{ uploadLabel }}</p>
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
      message="文档上传成功"
      class="mt-3"
      close
      @close="uploadSuccess = false"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useDocumentStore } from '../../stores/document'
import { UploadCloud as UploadCloudIcon } from 'lucide-vue-next'

const documentStore = useDocumentStore()

const files = ref([])
const uploading = ref(false)
const progress = ref(0)
const error = ref(null)
const uploadSuccess = ref(false)

const emit = defineEmits(['upload-complete'])

const MAX_FILE_SIZE = 52428800 // 50MB
const acceptedFormats = '.pdf,.doc,.docx,.txt,.md,.markdown'

const uploadStatus = computed(() => {
  if (error.value) return 'error'
  if (uploadSuccess.value) return 'success'
  if (uploading.value) return 'active'
  return 'default'
})

const uploadLabel = computed(() => {
  if (uploading.value) {
    return `上传中... ${progress.value}%`
  }
  return null
})

function validateFile(file) {
  const allowedExtensions = ['.pdf', '.doc', '.docx', '.txt', '.md', '.markdown']
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
  
  // Check for duplicate filename
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
  
  try {
    error.value = null
    uploadSuccess.value = false
    uploading.value = true
    progress.value = 0
    
    const document = await documentStore.uploadDocument(file)
    
    uploadSuccess.value = true
    emit('upload-complete', document)
    
    // 清空文件列表
    setTimeout(() => {
      files.value = []
    }, 1000)
    
  } catch (err) {
    error.value = err.message || '上传失败'
  } finally {
    uploading.value = false
  }
}

// Watch upload progress
documentStore.$subscribe((_mutation, state) => {
  if (uploading.value) {
    progress.value = state.uploadProgress
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

.upload-hint {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.6;
  margin: 0;
  display: block;
  white-space: pre-line;
}
</style>
