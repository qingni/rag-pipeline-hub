<template>
  <div class="content-area bg-gray-50">
    <div v-if="title" class="mb-6">
      <h1 class="content-title-row">
        <slot name="icon" />
        <span class="text-2xl font-bold text-gray-900">{{ title }}</span>
      </h1>
      <p v-if="subtitle" class="text-gray-600 mt-1">{{ subtitle }}</p>
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
  subtitle: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.content-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}
</style>
