<template>
  <div class="search-input-container">
    <div class="search-input-wrapper">
      <div class="textarea-container">
        <search-icon class="search-prefix-icon" />
        <t-textarea
          v-model="localQuery"
          placeholder="输入您的问题或关键词，支持多行输入..."
          :maxlength="2000"
          :autosize="{ minRows: 1, maxRows: 6 }"
          @keydown="handleKeydown"
        />
      </div>
      
      <t-button
        theme="primary"
        size="large"
        :loading="isSearching"
        :disabled="!localQuery.trim()"
        @click="handleSearch"
      >
        <template #icon>
          <search-icon v-if="!isSearching" />
        </template>
        搜索
      </t-button>
    </div>
    
    <div v-if="error" class="search-error">
      <t-alert theme="error" :message="error" close />
    </div>
    
    <div class="search-tips">
      <span class="tip-text">提示：输入自然语言问题，系统将在知识库中检索相关内容</span>
      <span class="char-count">
        {{ localQuery.length }} / 2000
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { SearchIcon } from 'tdesign-icons-vue-next'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  isSearching: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'search', 'clear'])

const localQuery = ref(props.modelValue)

// 双向绑定
watch(() => props.modelValue, (newVal) => {
  localQuery.value = newVal
})

watch(localQuery, (newVal) => {
  emit('update:modelValue', newVal)
})

function handleKeydown(e) {
  // Ctrl+Enter 或 Cmd+Enter 触发搜索
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault()
    handleSearch()
  }
}

function handleSearch() {
  if (localQuery.value.trim()) {
    emit('search', localQuery.value.trim())
  }
}

function handleClear() {
  localQuery.value = ''
  emit('clear')
}
</script>

<style scoped>
.search-input-container {
  margin-bottom: 1rem;
}

.search-input-wrapper {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
}

.textarea-container {
  flex: 1;
  position: relative;
  display: flex;
  align-items: flex-start;
  border: 1px solid #dcdcdc;
  border-radius: 6px;
  padding: 8px 12px;
  background: #fff;
  transition: border-color 0.2s;
}

.textarea-container:hover {
  border-color: #0052d9;
}

.textarea-container:focus-within {
  border-color: #0052d9;
  box-shadow: 0 0 0 2px rgba(0, 82, 217, 0.1);
}

.search-prefix-icon {
  flex-shrink: 0;
  margin-right: 8px;
  margin-top: 4px;
  color: #999;
  font-size: 18px;
}

.textarea-container :deep(.t-textarea__inner) {
  border: none !important;
  padding: 0 !important;
  min-height: 24px !important;
  line-height: 1.6;
  resize: none;
  font-size: 14px;
}

.textarea-container :deep(.t-textarea__inner:focus) {
  box-shadow: none !important;
}

.textarea-container :deep(.t-textarea) {
  flex: 1;
}

.search-input-wrapper .t-button {
  height: 40px;
  flex-shrink: 0;
}

.search-error {
  margin-top: 0.5rem;
}

.search-tips {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #999;
}

.tip-text {
  color: #666;
}

.char-count {
  color: #999;
}
</style>
