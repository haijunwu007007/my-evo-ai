import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/dashboard',
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
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
