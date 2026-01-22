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
          <t-alert theme="info" style="margin-bottom: 16px">
            <template #message>
              语义分块：使用 Embedding 相似度智能识别语义边界
            </template>
          </t-alert>

          <t-form-item>
            <t-checkbox
              v-model="parameters.use_embedding"
              @change="handleParamChange"
            >
              使用 Embedding 模型（更准确，需要 API）
            </t-checkbox>
          </t-form-item>

          <!-- Embedding model selector -->
          <t-form-item 
            v-if="parameters.use_embedding" 
            label="Embedding 模型" 
            name="embedding_model"
          >
            <t-select
              v-model="parameters.embedding_model"
              :options="embeddingModelOptions"
              @change="handleParamChange"
            />
            <template #tips>
              {{ getEmbeddingModelTips(parameters.embedding_model) }}
            </template>
          </t-form-item>

          <t-form-item label="相似度阈值" name="similarity_threshold">
            <t-slider
              v-model="parameters.similarity_threshold"
              :min="0.1"
              :max="0.9"
              :step="0.1"
              :label="String(parameters.similarity_threshold)"
              @change="handleParamChange"
            />
            <template #tips>语义相似度阈值（越低分块越细）</template>
          </t-form-item>

          <t-form-item label="最小块大小" name="min_chunk_size">
            <t-input-number
              v-model="parameters.min_chunk_size"
              :min="100"
              :max="2000"
              :step="100"
              @change="handleParamChange"
            />
            <template #tips>分块最小字符数</template>
          </t-form-item>

          <t-form-item label="最大块大小" name="max_chunk_size">
            <t-input-number
              v-model="parameters.max_chunk_size"
              :min="500"
              :max="5000"
              :step="100"
              @change="handleParamChange"
            />
            <template #tips>分块最大字符数</template>
          </t-form-item>
        </template>

        <!-- Parent-Child strategy parameters -->
        <template v-if="strategyType === 'parent_child'">
          <t-alert theme="info" style="margin-bottom: 16px">
            <template #message>
              父子分块：大块（父块）提供上下文，小块（子块）用于检索
            </template>
          </t-alert>

          <t-form-item label="父块大小" name="parent_chunk_size">
            <t-input-number
              v-model="parameters.parent_chunk_size"
              :min="500"
              :max="10000"
              :step="100"
              @change="handleParamChange"
            />
            <template #tips>父块的字符数（500-10000），用于提供完整上下文</template>
          </t-form-item>

          <t-form-item label="子块大小" name="child_chunk_size">
            <t-input-number
              v-model="parameters.child_chunk_size"
              :min="100"
              :max="2000"
              :step="50"
              @change="handleParamChange"
            />
            <template #tips>子块的字符数（100-2000），用于向量检索</template>
          </t-form-item>

          <t-form-item label="子块重叠度" name="child_overlap">
            <t-input-number
              v-model="parameters.child_overlap"
              :min="0"
              :max="Math.floor(parameters.child_chunk_size * 0.3)"
              :step="10"
              @change="handleParamChange"
            />
            <template #tips>子块之间的重叠字符数</template>
          </t-form-item>

          <t-form-item label="父块重叠度" name="parent_overlap">
            <t-input-number
              v-model="parameters.parent_overlap"
              :min="0"
              :max="Math.floor(parameters.parent_chunk_size * 0.2)"
              :step="50"
              @change="handleParamChange"
            />
            <template #tips>父块之间的重叠字符数</template>
          </t-form-item>

          <!-- Parameter validation warning -->
          <t-alert 
            v-if="parameters.child_chunk_size >= parameters.parent_chunk_size"
            theme="warning"
            style="margin-top: 8px"
          >
            <template #message>
              子块大小必须小于父块大小
            </template>
          </t-alert>
        </template>

        <!-- Multimodal strategy parameters -->
        <template v-if="strategyType === 'multimodal'">
          <t-alert theme="info" style="margin-bottom: 16px">
            <template #message>
              多模态分块：独立提取表格、图片、代码块，分别生成不同类型的分块
            </template>
          </t-alert>

          <!-- Content type toggles -->
          <t-form-item label="内容类型提取">
            <t-space direction="vertical" style="width: 100%">
              <t-checkbox
                v-model="parameters.include_tables"
                @change="handleParamChange"
              >
                提取表格（Markdown格式）
              </t-checkbox>
              <t-checkbox
                v-model="parameters.include_images"
                @change="handleParamChange"
              >
                提取图片（独立分块）
              </t-checkbox>
              <!-- Image base64 sub-option with indent -->
              <div v-if="parameters.include_images" class="sub-option">
                <t-checkbox
                  v-model="parameters.extract_image_base64"
                  @change="handleParamChange"
                >
                  嵌入图片数据
                </t-checkbox>
                <div class="sub-option-tips">
                  勾选后图片以 Base64 编码嵌入分块，可用于多模态向量化；
                  不勾选则仅保留图片路径引用
                </div>
              </div>
              <t-checkbox
                v-model="parameters.include_code"
                @change="handleParamChange"
              >
                提取代码块（保留语言标识）
              </t-checkbox>
            </t-space>
          </t-form-item>

          <t-divider />

          <!-- Text chunking strategy -->
          <t-form-item label="文本分块策略" name="text_strategy">
            <t-select
              v-model="parameters.text_strategy"
              :options="textStrategyOptions"
              @change="handleParamChange"
            />
            <template #tips>非多模态内容的文本分块方式</template>
          </t-form-item>

          <template v-if="parameters.text_strategy !== 'none'">
            <t-form-item label="文本块大小" name="text_chunk_size">
              <t-input-number
                v-model="parameters.text_chunk_size"
                :min="100"
                :max="5000"
                :step="100"
                @change="handleParamChange"
              />
              <template #tips>每个文本块的字符数</template>
            </t-form-item>

            <t-form-item label="文本重叠度" name="text_overlap">
              <t-input-number
                v-model="parameters.text_overlap"
                :min="0"
                :max="Math.floor(parameters.text_chunk_size * 0.3)"
                :step="10"
                @change="handleParamChange"
              />
              <template #tips>相邻文本块的重叠字符数</template>
            </t-form-item>
          </template>

          <t-divider />

          <!-- Extraction thresholds -->
          <t-form-item label="最小表格行数" name="min_table_rows">
            <t-input-number
              v-model="parameters.min_table_rows"
              :min="1"
              :max="10"
              :step="1"
              @change="handleParamChange"
            />
            <template #tips>少于此行数的表格将被忽略</template>
          </t-form-item>

          <t-form-item label="最小代码行数" name="min_code_lines">
            <t-input-number
              v-model="parameters.min_code_lines"
              :min="1"
              :max="20"
              :step="1"
              @change="handleParamChange"
            />
            <template #tips>少于此行数的代码块将被忽略</template>
          </t-form-item>
        </template>

        <!-- Hybrid strategy parameters -->
        <template v-if="strategyType === 'hybrid'">
          <t-alert theme="info" style="margin-bottom: 16px">
            <template #message>
              混合分块：针对不同内容类型（正文、代码、表格）应用最合适的分块策略
            </template>
          </t-alert>

          <!-- Text strategy selection -->
          <t-form-item label="正文分块策略" name="text_strategy">
            <t-select
              v-model="parameters.text_strategy"
              :options="hybridTextStrategyOptions"
              @change="handleParamChange"
            />
            <template #tips>普通文本内容的分块方式</template>
          </t-form-item>

          <t-form-item label="文本块大小" name="text_chunk_size">
            <t-input-number
              v-model="parameters.text_chunk_size"
              :min="100"
              :max="5000"
              :step="100"
              @change="handleParamChange"
            />
            <template #tips>每个文本块的字符数</template>
          </t-form-item>

          <t-form-item label="文本重叠度" name="text_overlap">
            <t-input-number
              v-model="parameters.text_overlap"
              :min="0"
              :max="Math.floor(parameters.text_chunk_size * 0.3)"
              :step="10"
              @change="handleParamChange"
            />
          </t-form-item>

          <!-- Semantic-specific params -->
          <t-form-item v-if="parameters.text_strategy === 'semantic'" label="语义相似度阈值">
            <t-slider
              v-model="parameters.similarity_threshold"
              :min="0.1"
              :max="0.9"
              :step="0.1"
              :label="String(parameters.similarity_threshold)"
              @change="handleParamChange"
            />
          </t-form-item>

          <t-form-item v-if="parameters.text_strategy === 'semantic'">
            <t-checkbox
              v-model="parameters.use_embedding"
              @change="handleParamChange"
            >
              使用 Embedding 模型（更准确，需要 API）
            </t-checkbox>
          </t-form-item>

          <!-- Embedding model selector for hybrid semantic -->
          <t-form-item 
            v-if="parameters.text_strategy === 'semantic' && parameters.use_embedding" 
            label="Embedding 模型"
          >
            <t-select
              v-model="parameters.embedding_model"
              :options="embeddingModelOptions"
              @change="handleParamChange"
            />
            <template #tips>
              {{ getEmbeddingModelTips(parameters.embedding_model) }}
            </template>
          </t-form-item>

          <t-divider />

          <!-- Code strategy selection -->
          <t-form-item label="代码分块策略" name="code_strategy">
            <t-select
              v-model="parameters.code_strategy"
              :options="codeStrategyOptions"
              @change="handleParamChange"
            />
            <template #tips>代码块的分块方式</template>
          </t-form-item>

          <t-form-item v-if="parameters.code_strategy === 'lines'" label="每块行数">
            <t-input-number
              v-model="parameters.code_chunk_lines"
              :min="10"
              :max="200"
              :step="10"
              @change="handleParamChange"
            />
          </t-form-item>

          <t-form-item v-if="parameters.code_strategy === 'lines'" label="代码重叠行数">
            <t-input-number
              v-model="parameters.code_overlap_lines"
              :min="0"
              :max="20"
              :step="1"
              @change="handleParamChange"
            />
          </t-form-item>

          <t-divider />

          <!-- Table strategy selection -->
          <t-form-item label="表格分块策略" name="table_strategy">
            <t-select
              v-model="parameters.table_strategy"
              :options="tableStrategyOptions"
              @change="handleParamChange"
            />
            <template #tips>表格内容的处理方式</template>
          </t-form-item>
        </template>

        <!-- Estimated chunk count -->
        <t-divider />
        <div v-if="estimatedChunks > 0" class="estimate-info">
          <t-tag theme="success" variant="light">
            预计生成约 {{ estimatedChunks }} 个文本块
          </t-tag>
          <t-tag v-if="strategyType === 'parent_child'" theme="primary" variant="light" style="margin-left: 8px">
            约 {{ estimatedParentChunks }} 个父块
          </t-tag>
          <t-space v-if="strategyType === 'multimodal'" style="margin-top: 8px">
            <t-tag v-if="parameters.include_tables" theme="success" variant="outline" size="small">
              + 表格块
            </t-tag>
            <t-tag v-if="parameters.include_images" theme="warning" variant="outline" size="small">
              + 图片块
            </t-tag>
            <t-tag v-if="parameters.include_code" theme="danger" variant="outline" size="small">
              + 代码块
            </t-tag>
          </t-space>
          <t-space v-if="strategyType === 'hybrid'" style="margin-top: 8px">
            <t-tag theme="primary" variant="outline" size="small">
              正文: {{ parameters.text_strategy }}
            </t-tag>
            <t-tag v-if="parameters.code_strategy !== 'none'" theme="warning" variant="outline" size="small">
              代码: {{ parameters.code_strategy }}
            </t-tag>
            <t-tag theme="success" variant="outline" size="small">
              表格: {{ parameters.table_strategy === 'independent' ? '独立' : '合并' }}
            </t-tag>
          </t-space>
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
const estimatedParentChunks = ref(0)

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

const textStrategyOptions = [
  { label: '按字符分块', value: 'character' },
  { label: '按段落分块', value: 'paragraph' },
  { label: '不分块（仅提取多模态）', value: 'none' }
]

const hybridTextStrategyOptions = [
  { label: '语义分块（推荐）', value: 'semantic' },
  { label: '按段落分块', value: 'paragraph' },
  { label: '按字符分块', value: 'character' },
  { label: '按标题分块', value: 'heading' }
]

const codeStrategyOptions = [
  { label: '按行数分块', value: 'lines' },
  { label: '按字符分块', value: 'character' },
  { label: '不分块（保持完整）', value: 'none' }
]

const tableStrategyOptions = [
  { label: '独立分块', value: 'independent' },
  { label: '合并到文本', value: 'merge_with_text' }
]

// Embedding model options (unified with document vectorization)
const embeddingModelOptions = [
  { label: 'BGE-M3（推荐，1024维，8K上下文，快速）', value: 'bge-m3' },
  { label: 'Qwen3-Embedding-8B（4096维，32K上下文，高精度）', value: 'qwen3-embedding-8b' },
  { label: '混元 Embedding（1024维）', value: 'hunyuan-embedding' }
]

// Get embedding model description tips
const getEmbeddingModelTips = (model) => {
  const tips = {
    'bge-m3': '多语言支持，速度快，适合大多数场景',
    'qwen3-embedding-8b': '超长文本支持（32K），高维向量（4096维），适合高精度场景',
    'hunyuan-embedding': '腾讯混元提供的 Embedding 模型'
  }
  return tips[model] || '选择 Embedding 模型'
}

// Default parameters for parent-child strategy
const parentChildDefaults = {
  parent_chunk_size: 2000,
  child_chunk_size: 500,
  child_overlap: 50,
  parent_overlap: 200
}

// Default parameters for multimodal strategy
const multimodalDefaults = {
  include_tables: true,
  include_images: true,
  include_code: true,
  text_strategy: 'character',
  text_chunk_size: 500,
  text_overlap: 50,
  min_table_rows: 2,
  min_code_lines: 3,
  extract_image_base64: false
}

// Default parameters for hybrid strategy
const hybridDefaults = {
  text_strategy: 'semantic',
  code_strategy: 'lines',
  table_strategy: 'independent',
  text_chunk_size: 500,
  text_overlap: 50,
  code_chunk_lines: 50,
  code_overlap_lines: 5,
  similarity_threshold: 0.5,
  use_embedding: true,
  embedding_model: 'bge-m3'  // Default to bge-m3 for speed
}

// Default parameters for semantic strategy
const semanticDefaults = {
  similarity_threshold: 0.3,
  min_chunk_size: 300,
  max_chunk_size: 1200,
  use_embedding: true,
  embedding_model: 'bge-m3'  // Default to bge-m3 for speed
}

// Watch for strategy changes
watch(
  () => chunkingStore.selectedStrategy,
  (strategy) => {
    if (strategy) {
      if (strategy.type === 'parent_child') {
        parameters.value = { ...parentChildDefaults, ...strategy.default_parameters }
      } else if (strategy.type === 'multimodal') {
        parameters.value = { ...multimodalDefaults, ...strategy.default_parameters }
      } else if (strategy.type === 'hybrid') {
        parameters.value = { ...hybridDefaults, ...strategy.default_parameters }
      } else if (strategy.type === 'semantic') {
        parameters.value = { ...semanticDefaults, ...strategy.default_parameters }
      } else {
        parameters.value = { ...strategy.default_parameters }
      }
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
    estimatedParentChunks.value = 0
    return
  }

  // Use actual text length from document features if available, otherwise fallback to file size estimation
  const features = chunkingStore.documentFeatures
  let estimatedTextLength
  
  if (features?.total_char_count && features.total_char_count > 0) {
    // Use actual parsed text length (most accurate)
    estimatedTextLength = features.total_char_count
  } else {
    // Fallback: rough estimation based on file size
    // For JSON/structured files, actual text content is usually much smaller
    // Use a more conservative multiplier
    estimatedTextLength = doc.size_bytes * 0.5
  }

  if (strategyType.value === 'character') {
    const chunkSize = parameters.value.chunk_size || 500
    const overlap = parameters.value.overlap || 50
    const effectiveSize = chunkSize - overlap
    estimatedChunks.value = Math.ceil(estimatedTextLength / effectiveSize)
  } else if (strategyType.value === 'paragraph') {
    const avgSize = (parameters.value.min_chunk_size + parameters.value.max_chunk_size) / 2
    estimatedChunks.value = Math.ceil(estimatedTextLength / avgSize)
  } else if (strategyType.value === 'parent_child') {
    const parentSize = parameters.value.parent_chunk_size || 2000
    const childSize = parameters.value.child_chunk_size || 500
    const parentOverlap = parameters.value.parent_overlap || 200
    const childOverlap = parameters.value.child_overlap || 50
    
    // Estimate parent chunks
    const parentStep = parentSize - parentOverlap
    estimatedParentChunks.value = Math.ceil(estimatedTextLength / parentStep)
    
    // Estimate child chunks per parent
    const childStep = childSize - childOverlap
    const childrenPerParent = Math.ceil(parentSize / childStep)
    estimatedChunks.value = estimatedParentChunks.value * childrenPerParent
  } else if (strategyType.value === 'multimodal') {
    // For multimodal, estimate based on text strategy
    if (parameters.value.text_strategy === 'none') {
      estimatedChunks.value = 0  // Will show multimodal tags instead
    } else {
      const textSize = parameters.value.text_chunk_size || 500
      const textOverlap = parameters.value.text_overlap || 50
      const effectiveSize = textSize - textOverlap
      // Estimate about 70% of content is text (rest is tables/images/code)
      estimatedChunks.value = Math.ceil((estimatedTextLength * 0.7) / effectiveSize)
    }
  } else if (strategyType.value === 'hybrid') {
    // For hybrid, estimate based on text strategy and content types
    const textSize = parameters.value.text_chunk_size || 500
    const textOverlap = parameters.value.text_overlap || 50
    const effectiveSize = textSize - textOverlap
    // Estimate about 60% of content is text, 20% code, 20% tables/images
    estimatedChunks.value = Math.ceil((estimatedTextLength * 0.6) / effectiveSize)
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

.parameter-config :deep(.t-card) {
  background: linear-gradient(135deg, #f9fbff 0%, #f5f8ff 100%);
  border: 1px solid var(--td-component-stroke);
  border-radius: 10px;
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

.sub-option {
  padding-left: 24px;
  margin-top: 4px;
}

.sub-option-tips {
  font-size: 12px;
  color: var(--td-text-color-placeholder);
  line-height: 1.5;
  margin-top: 4px;
  padding-left: 24px;
}
</style>
