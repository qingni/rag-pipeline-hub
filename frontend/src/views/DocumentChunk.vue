<template>
  <div class="flex flex-1">
    <ControlPanel title="文档分块" description="将文档分割成块以便进一步处理">
      <div class="card text-center py-12 text-gray-600">
        该功能将在 User Story 2 中实现
      </div>
    </ControlPanel>
    
    <ContentArea title="分块结果">
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
