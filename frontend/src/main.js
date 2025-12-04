import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

// TDesign 样式和组件
import TDesign from 'tdesign-vue-next'
import 'tdesign-vue-next/es/style/index.css'

// TailwindCSS 样式
import './assets/styles/main.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(TDesign)

app.mount('#app')
