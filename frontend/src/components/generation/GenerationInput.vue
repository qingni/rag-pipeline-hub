<template>
  <div class="generation-input">
    <div class="input-container">
      <t-textarea
        v-model="inputValue"
        placeholder="输入您的问题..."
        :autosize="{ minRows: 3, maxRows: 8 }"
        :disabled="disabled"
        @keydown.ctrl.enter="handleGenerate"
        @keydown.meta.enter="handleGenerate"
      />
      <div class="input-footer">
        <span class="hint-text">Ctrl + Enter 发送</span>
        <div class="action-buttons">
          <t-button
            v-if="loading"
            theme="danger"
            variant="outline"
            @click="handleCancel"
          >
            <template #icon>
              <StopCircle :size="16" />
            </template>
            取消生成
          </t-button>
          <t-button
            v-else
            theme="primary"
            :disabled="!canGenerate"
            @click="handleGenerate"
          >
            <template #icon>
              <Sparkles :size="16" />
            </template>
            生成回答
          </t-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Sparkles, StopCircle } from 'lucide-vue-next'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'generate', 'cancel'])

const inputValue = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const canGenerate = computed(() => {
  return inputValue.value.trim().length > 0 && !props.disabled
})

function handleGenerate() {
  if (canGenerate.value) {
    emit('generate')
  }
}

function handleCancel() {
  emit('cancel')
}
</script>

<style scoped>
.generation-input {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.input-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hint-text {
  font-size: 12px;
  color: #9ca3af;
}

.action-buttons {
  display: flex;
  gap: 8px;
}
</style>
