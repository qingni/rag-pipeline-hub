<template>
  <div class="w-80 bg-white shadow-md p-6 overflow-y-auto">
    <div v-if="title" class="mb-6">
      <h2 class="panel-title-row">
        <slot name="icon" />
        <span class="text-lg font-semibold text-gray-800">{{ title }}</span>
      </h2>
      <p v-if="description" class="text-sm text-gray-600 mt-1">{{ description }}</p>
    </div>
    
    <slot></slot>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: ''
  },
  description: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.panel-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}
</style>
