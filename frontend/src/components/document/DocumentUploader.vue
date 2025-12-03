<template>
  <div class="document-uploader">
    <div 
      class="upload-area border-2 border-dashed rounded-lg p-8 text-center"
      :class="isDragging ? 'border-primary-500 bg-primary-50' : 'border-gray-300'"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".pdf,.doc,.docx,.txt,.md,.markdown"
        class="hidden"
        @change="handleFileSelect"
      />
      
      <div v-if="!uploading">
        <div class="text-4xl mb-4">📄</div>
        <p class="text-lg font-semibold mb-2">上传文档</p>
        <p class="text-sm text-gray-600 mb-4">
          拖拽文件到这里或点击选择文件
        </p>
        <button 
          class="btn-primary"
          @click="$refs.fileInput.click()"
        >
          选择文件
        </button>
        <p class="text-xs text-gray-500 mt-4">
          支持格式: PDF, DOC, DOCX, TXT, Markdown (最大50MB)
        </p>
      </div>
      
      <div v-else class="upload-progress">
        <div class="spinner mx-auto mb-4"></div>
        <p class="text-lg font-semibold mb-2">上传中...</p>
        <div class="w-full bg-gray-200 rounded-full h-2 mb-2">
          <div 
            class="bg-primary-600 h-2 rounded-full transition-all"
            :style="{ width: progress + '%' }"
          ></div>
        </div>
        <p class="text-sm text-gray-600">{{ progress }}%</p>
      </div>
    </div>
    
    <div v-if="error" class="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
      <p class="text-red-800">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useDocumentStore } from '../../stores/document'

const documentStore = useDocumentStore()

const fileInput = ref(null)
const isDragging = ref(false)
const uploading = ref(false)
const progress = ref(0)
const error = ref(null)

const emit = defineEmits(['upload-complete'])

const MAX_FILE_SIZE = 52428800 // 50MB

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
}

async function uploadFile(file) {
  try {
    validateFile(file)
    
    uploading.value = true
    error.value = null
    progress.value = 0
    
    const document = await documentStore.uploadDocument(file)
    
    emit('upload-complete', document)
    
  } catch (err) {
    error.value = err.message || '上传失败'
  } finally {
    uploading.value = false
    progress.value = 0
    isDragging.value = false
  }
}

function handleFileSelect(event) {
  const file = event.target.files[0]
  if (file) {
    uploadFile(file)
  }
}

function handleDrop(event) {
  const file = event.dataTransfer.files[0]
  if (file) {
    uploadFile(file)
  }
}

// Watch upload progress
documentStore.$subscribe((_mutation, state) => {
  progress.value = state.uploadProgress
})
</script>
