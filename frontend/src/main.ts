import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import naive from 'naive-ui'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(naive)

// Naive UI 消息组件注入
app.config.globalProperties.$message = (window as any).$message || undefined
app.mount('#app')
