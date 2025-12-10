<template>
  <div class="parameter-config">
    <t-card title="参数配置" :bordered="false">
      <t-form v-if="hasStrategy" :data="parameters" layout="vertical">
        <!-- Character strategy parameters -->
        <template v-if="strategyType === 'character'">
          <t-form-item label="块大小" name="chunk_size">
            <t-input-number
              v-model="parameters.chunk_size"
              :min="100"
              :max="5000"
              :step="100"
              @change="handleParamChange"
            />
            <template #tips>每个文本块的字符数（100-5000）</template>
          </t-form-item>

          <t-form-item label="重叠度" name="overlap">
            <t-input-number
              v-model="parameters.overlap"
              :min="0"
              :max="Math.floor(parameters.chunk_size * 0.3)"
              :step="10"
              @change="handleParamChange"
            />
            <template #tips>相邻块之间的重叠字符数</template>
          </t-form-item>
        </template>

        <!-- Paragraph strategy parameters -->
        <template v-if="strategyType === 'paragraph'">
          <t-form-item label="最小块大小" name="min_chunk_size">
            <t-input-number
              v-model="parameters.min_chunk_size"
              :min="50"
              :max="2000"
              :step="50"
              @change="handleParamChange"
            />
            <template #tips>段落合并的最小字符数</template>
          </t-form-item>

          <t-form-item label="最大块大小" name="max_chunk_size">
            <t-input-number
              v-model="parameters.max_chunk_size"
              :min="500"
              :max="10000"
              :step="100"
              @change="handleParamChange"
            />
            <template #tips>段落块的最大字符数</template>
          </t-form-item>
        </template>

        <!-- Heading strategy parameters -->
        <template v-if="strategyType === 'heading'">
          <t-form-item label="最小标题层级" name="min_heading_level">
            <t-select
              v-model="parameters.min_heading_level"
              :options="headingLevels"
              @change="handleParamChange"
            />
          </t-form-item>

          <t-form-item label="最大标题层级" name="max_heading_level">
            <t-select
              v-model="parameters.max_heading_level"
              :options="headingLevels"
              @change="handleParamChange"
            />
          </t-form-item>
        </template>

        <!-- Semantic strategy parameters -->
        <template v-if="strategyType === 'semantic'">
          <t-form-item label="相似度阈值" name="similarity_threshold">
            <t-slider
              v-model="parameters.similarity_threshold"
              :min="0.3"
              :max="0.9"
              :step="0.1"
              :label="String(parameters.similarity_threshold)"
              @change="handleParamChange"
            />
            <template #tips>语义相似度阈值（0.3-0.9）</template>
          </t-form-item>

          <t-form-item label="最小块大小" name="min_chunk_size">
            <t-input-number
              v-model="parameters.min_chunk_size"
              :min="100"
              :max="2000"
              :step="100"
              @change="handleParamChange"
            />
          </t-form-item>
        </template>

        <!-- Estimated chunk count -->
        <t-divider />
        <div v-if="estimatedChunks > 0" class="estimate-info">
          <t-tag theme="success" variant="light">
            预计生成约 {{ estimatedChunks }} 个文本块
          </t-tag>
        </div>
      </t-form>

      <t-empty
        v-else
        description="请先选择分块策略"
        size="small"
      />
    </t-card>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useChunkingStore } from '@/stores/chunkingStore'

const chunkingStore = useChunkingStore()

const parameters = ref({})
const estimatedChunks = ref(0)

const hasStrategy = computed(() => !!chunkingStore.selectedStrategy)
const strategyType = computed(() => chunkingStore.selectedStrategy?.type)

const headingLevels = [
  { label: 'H1', value: 1 },
  { label: 'H2', value: 2 },
  { label: 'H3', value: 3 },
  { label: 'H4', value: 4 },
  { label: 'H5', value: 5 },
  { label: 'H6', value: 6 }
]

// Watch for strategy changes
watch(
  () => chunkingStore.selectedStrategy,
  (strategy) => {
    if (strategy) {
      parameters.value = { ...strategy.default_parameters }
      estimateChunkCount()
    }
  },
  { immediate: true }
)

const handleParamChange = () => {
  chunkingStore.updateParameters(parameters.value)
  estimateChunkCount()
}

const estimateChunkCount = () => {
  // Simple estimation based on document size and parameters
  const doc = chunkingStore.selectedDocument
  if (!doc || !strategyType.value) {
    estimatedChunks.value = 0
    return
  }

  // Rough estimation: assume average 2 chars per byte for text
  const estimatedTextLength = doc.size_bytes * 2

  if (strategyType.value === 'character') {
    const chunkSize = parameters.value.chunk_size || 500
    const overlap = parameters.value.overlap || 50
    const effectiveSize = chunkSize - overlap
    estimatedChunks.value = Math.ceil(estimatedTextLength / effectiveSize)
  } else if (strategyType.value === 'paragraph') {
    const avgSize = (parameters.value.min_chunk_size + parameters.value.max_chunk_size) / 2
    estimatedChunks.value = Math.ceil(estimatedTextLength / avgSize)
  } else {
    // For heading and semantic, harder to estimate
    estimatedChunks.value = Math.ceil(estimatedTextLength / 800)
  }
}
</script>

<style scoped>
.parameter-config {
  margin-bottom: 20px;
}

.parameter-config :deep(.t-card__body) {
  padding: 16px 12px;
}

.parameter-config :deep(.t-form-item__label) {
  font-size: 13px;
}

.parameter-config :deep(.t-form__tips) {
  font-size: 12px;
  line-height: 1.4;
}

.estimate-info {
  text-align: center;
  padding: 12px 0;
}
</style>
