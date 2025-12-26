<template>
  <div class="search-input-container">
    <div class="search-input-wrapper">
      <t-input
        v-model="localQuery"
        placeholder="输入您的问题或关键词..."
        size="large"
        clearable
        :maxlength="2000"
        @keyup.enter="handleSearch"
        @clear="handleClear"
      >
        <template #prefix-icon>
          <search-icon />
        </template>
      </t-input>
      
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
      <span v-if="localQuery.length > 0" class="char-count">
        {{ localQuery.length }} / 2000
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
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
  align-items: center;
}

.search-input-wrapper .t-input {
  flex: 1;
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
