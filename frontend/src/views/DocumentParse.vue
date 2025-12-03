<template>
  <div class="flex flex-1">
    <ControlPanel title="文档解析" description="选择解析选项并预览结果">
      <div class="space-y-6">
        <!-- Document selection -->
        <div>
          <label class="block text-sm font-semibold mb-2">选择文档</label>
          <select 
            v-model="selectedDocumentId" 
            class="input-field"
            @change="loadDocumentList"
          >
            <option value="">-- 请选择 --</option>
            <option v-for="doc in documents" :key="doc.id" :value="doc.id">
              {{ doc.filename }}
            </option>
          </select>
        </div>
        
        <!-- Parse options -->
        <div v-if="selectedDocumentId">
          <label class="block text-sm font-semibold mb-2">解析选项</label>
          <select v-model="parseOption" class="input-field mb-4">
            <option value="full_text">全文解析</option>
            <option value="by_page">分页解析</option>
            <option value="by_heading">按标题解析</option>
            <option value="mixed">混合解析</option>
          </select>
          
          <label class="flex items-center">
            <input 
              type="checkbox" 
              v-model="includeTables"
              class="mr-2"
            />
            <span class="text-sm">包含表格</span>
          </label>
        </div>
        
        <!-- Parse button -->
        <div v-if="selectedDocumentId">
          <button
            class="btn-primary w-full"
            :disabled="loading"
            @click="parseDocument"
          >
            <span v-if="!loading">开始解析</span>
            <span v-else class="flex items-center justify-center">
              <span class="spinner mr-2"></span>
              解析中...
            </span>
          </button>
        </div>
        
        <!-- Progress -->
        <ProcessingProgress :status="status" :error="error" />
      </div>
    </ControlPanel>
    
    <ContentArea title="解析结果">
      <div v-if="parseResult">
        <ResultPreview :result="parseResult" />
      </div>
      <div v-else class="card text-center py-12 text-gray-600">
        请选择文档并开始解析
      </div>
    </ContentArea>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useDocumentStore } from '../stores/document'
import { useProcessingStore } from '../stores/processing'
import ControlPanel from '../components/layout/ControlPanel.vue'
import ContentArea from '../components/layout/ContentArea.vue'
import ProcessingProgress from '../components/processing/ProcessingProgress.vue'
import ResultPreview from '../components/processing/ResultPreview.vue'

const documentStore = useDocumentStore()
const processingStore = useProcessingStore()

const documents = computed(() => documentStore.documents)
const selectedDocumentId = ref('')
const parseOption = ref('full_text')
const includeTables = ref(true)
const loading = ref(false)
const status = ref('idle')
const error = ref(null)
const parseResult = ref(null)

onMounted(() => {
  loadDocumentList()
})

async function loadDocumentList() {
  await documentStore.fetchDocuments(1, 'ready')
}

async function parseDocument() {
  if (!selectedDocumentId.value) return
  
  loading.value = true
  status.value = 'processing'
  error.value = null
  
  try {
    const result = await processingStore.parseDocument(
      selectedDocumentId.value,
      parseOption.value,
      includeTables.value
    )
    
    parseResult.value = result
    status.value = 'completed'
  } catch (err) {
    error.value = err.message
    status.value = 'failed'
  } finally {
    loading.value = false
  }
}
</script>
