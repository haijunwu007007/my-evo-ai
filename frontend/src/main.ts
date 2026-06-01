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

const app = createApp(App)
app.component('StatCard', StatCard)
app.component('PagePanel', PagePanel)
app.component('LoadingBox', LoadingBox)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
