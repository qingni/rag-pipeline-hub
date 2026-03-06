<template>
  <aside class="sidebar">
    <!-- 标题区域 -->
    <div class="sidebar-header">
      <h1 class="sidebar-title">
        <span class="title-rag">RAG</span>
        <span class="title-rest">Pipeline Hub</span>
      </h1>
    </div>
    
    <!-- 导航菜单 -->
    <t-menu 
      :value="currentPath"
      theme="light"
      class="sidebar-menu"
    >
      <t-menu-item
        v-for="item in navItems"
        :key="item.path"
        :value="item.path"
        @click="handleNavigate(item.path)"
      >
        <template #icon>
          <component :is="item.iconComponent" :size="18" />
        </template>
        {{ item.label }}
      </t-menu-item>
    </t-menu>
    
    <!-- 底部信息 -->
    <div class="sidebar-footer">
      <t-divider />
      <div class="version-info">
        <Info :size="14" class="inline-block mr-1" />
        版本 v1.0.0
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { 
  Home, FileUp, SplitSquareHorizontal, Binary, 
  Server, SearchCheck, BotMessageSquare, Info 
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()

const currentPath = computed(() => route.path)

const navItems = [
  { path: '/', label: '首页', iconComponent: Home },
  { path: '/documents/load', label: '文档加载', iconComponent: FileUp },
  { path: '/documents/chunk', label: '文档分块', iconComponent: SplitSquareHorizontal },
  { path: '/documents/embed', label: '文档向量化', iconComponent: Binary },
  { path: '/index', label: '向量索引', iconComponent: Server },
  { path: '/search', label: '搜索查询', iconComponent: SearchCheck },
  { path: '/generation', label: '文本生成', iconComponent: BotMessageSquare }
]

function handleNavigate(path) {
  router.push(path)
}
</script>

<style scoped>
.sidebar {
  width: 240px;
  display: flex;
  flex-direction: column;
  height: 100vh;
  border-right: 1px solid #e5e7eb;
  background-color: #ffffff;
}

.sidebar-header {
  padding: 24px 20px;
  border-bottom: 1px solid #e5e7eb;
}

.sidebar-title {
  display: flex;
  align-items: baseline;
  gap: 7px;
  margin: 0;
  line-height: 1;
}

.title-rag {
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.5px;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.title-rest {
  font-size: 15px;
  font-weight: 500;
  color: #6B7280;
  letter-spacing: 0.2px;
}

.sidebar-menu {
  flex: 1;
  padding: 12px 8px;
  overflow-y: auto;
}

.sidebar-menu :deep(.t-menu__item) {
  gap: 8px;
}

.sidebar-footer {
  margin-top: auto;
}

.version-info {
  font-size: 12px;
  color: #6b7280;
  padding: 8px 24px;
}
</style>
