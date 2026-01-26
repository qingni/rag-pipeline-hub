<template>
  <div id="app" class="app-container">
    <div class="app-layout">
      <NavigationBar />
      <div class="main-content">
        <router-view />
      </div>
    </div>
    <!-- 全局加载队列面板 -->
    <LoadingQueuePanel />
  </div>
</template>

<script setup>
import NavigationBar from './components/layout/NavigationBar.vue'
import LoadingQueuePanel from './components/loading/LoadingQueuePanel.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.app-container {
  height: 100%;
  width: 100%;
}

.app-layout {
  display: flex;
  height: 100%;
  width: 100%;
}

.main-content {
  flex: 1;
  height: 100%;
  overflow: auto;
  display: flex;
  flex-direction: column;
}
</style>
