<template>
  <div class="flex flex-1">
    <ControlPanel title="文本生成" description="基于文档内容生成文本">
      <div class="card text-center py-12 text-gray-600">
        该功能将在 User Story 4 中实现
      </div>
    </ControlPanel>
    
    <ContentArea title="生成结果">
      <div class="card text-center py-12 text-gray-600">
        敬请期待
      </div>
    </ContentArea>
  </div>
</template>

<script setup>
import ControlPanel from '../components/layout/ControlPanel.vue'
import ContentArea from '../components/layout/ContentArea.vue'
</script>
