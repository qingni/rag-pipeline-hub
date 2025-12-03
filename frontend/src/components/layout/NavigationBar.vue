<template>
  <nav class="sidebar w-64 flex flex-col">
    <div class="p-6 border-b border-gray-200">
      <h1 class="text-xl font-bold text-primary-600">文档处理系统</h1>
    </div>
    
    <div class="flex-1 p-4">
      <div class="space-y-2">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="block px-4 py-3 rounded-lg hover:bg-gray-100 transition-colors"
          active-class="bg-primary-100 text-primary-700 font-semibold"
        >
          <div class="flex items-center">
            <span class="mr-3">{{ item.icon }}</span>
            <span>{{ item.label }}</span>
          </div>
        </router-link>
      </div>
    </div>
    
    <div class="p-4 border-t border-gray-200">
      <div class="text-sm text-gray-500">
        版本 v1.0.0
      </div>
    </div>
  </nav>
</template>

<script setup>
const navItems = [
  { path: '/', label: '首页', icon: '🏠' },
  { path: '/documents/load', label: '文档加载', icon: '📄' },
  { path: '/documents/parse', label: '文档解析', icon: '📝' },
  { path: '/documents/chunk', label: '文档分块', icon: '✂️' },
  { path: '/embeddings', label: '向量嵌入', icon: '🔢' },
  { path: '/index', label: '向量索引', icon: '📇' },
  { path: '/search', label: '搜索查询', icon: '🔍' },
  { path: '/generation', label: '文本生成', icon: '✨' }
]
</script>
