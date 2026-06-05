import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

// Element Plus
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// Element Plus 暗色模式 CSS 变量
import 'element-plus/theme-chalk/dark/css-vars.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

// 自定义组件全局注册
import StatCard from './components/StatCard.vue'
import PagePanel from './components/PagePanel.vue'
import LoadingBox from './components/LoadingBox.vue'
import VoiceInput from './components/VoiceInput.vue'

const app = createApp(App)
app.component('StatCard', StatCard)
app.component('PagePanel', PagePanel)
app.component('LoadingBox', LoadingBox)
app.component('VoiceInput', VoiceInput)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// ── 全局错误处理 ──
app.config.errorHandler = (err, instance, info) => {
  console.error('[GLOBAL ERROR]', err, info)
  // 展示给用户
  import('element-plus').then(({ ElNotification }) => {
    ElNotification({
      title: '系统异常',
      message: `发生了一个意外错误: ${(err as Error)?.message || '未知错误'}`,
      type: 'error',
      duration: 6000,
    })
  })
}
// 未捕获的 Promise 错误
window.addEventListener('unhandledrejection', (event) => {
  console.error('[UNHANDLED REJECTION]', event.reason)
})

app.mount('#app')
