import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', public: true },
  },
  {
    path: '/oauth/callback',
    name: 'OAuthCallback',
    component: () => import('@/views/Login.vue'),
    meta: { title: 'OAuth 回调', public: true },
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '监控面板', icon: 'Monitor' },
  },
  {
    path: '/scheduler',
    name: 'Scheduler',
    component: () => import('@/views/Scheduler.vue'),
    meta: { title: '调度器', icon: 'Timer' },
  },
  {
    path: '/events',
    name: 'Events',
    component: () => import('@/views/Events.vue'),
    meta: { title: '事件引擎', icon: 'Bell' },
  },
  {
    path: '/pipeline',
    name: 'Pipeline',
    component: () => import('@/views/Pipeline.vue'),
    meta: { title: '管线引擎', icon: 'Link' },
  },
  {
    path: '/queue',
    name: 'Queue',
    component: () => import('@/views/Queue.vue'),
    meta: { title: '任务队列', icon: 'List' },
  },
  {
    path: '/coordinator',
    name: 'Coordinator',
    component: () => import('@/views/Coordinator.vue'),
    meta: { title: '协调中心', icon: 'Cpu' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue'),
    meta: { title: '系统设置', icon: 'Setting' },
  },
  {
    path: '/modules',
    name: 'Modules',
    component: () => import('@/views/Modules.vue'),
    meta: { title: '模块管理', icon: 'Grid' },
  },
  {
    path: '/security',
    name: 'Security',
    component: () => import('@/views/Security.vue'),
    meta: { title: '安全中心', icon: 'Lock' },
  },
  {
    path: '/sysmon',
    name: 'SysMon',
    component: () => import('@/components/SystemMonitorDashboard.vue'),
    meta: { title: '系统监控', icon: 'TrendCharts' },
  },
  {
    path: '/sso-auth',
    name: 'SsoAuth',
    component: () => import('@/components/SsoAuthPanel.vue'),
    meta: { title: 'SSO 管理', icon: 'User' },
  },
  {
    path: '/data-analysis',
    name: 'DataAnalysis',
    component: () => import('@/components/DataAnalysisPanel.vue'),
    meta: { title: '数据分析', icon: 'DataAnalysis' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// ── 路由守卫 ──
router.beforeEach((to, from, next) => {
  // 公开页面（登录/OAuth回调）直接放行
  if (to.meta.public) return next()

  // 检查登录态
  const token = localStorage.getItem('evo_token')
  if (token) return next()

  // 未登录 → 跳转登录页，带 redirect 参数
  next({ name: 'Login', query: { redirect: to.fullPath } })
})

export default router
