import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue'
import DashboardView from '../views/DashboardView.vue'
import EnterpriseView from '../views/EnterpriseView.vue'

const routes = [
  { path: '/', name: 'chat', component: ChatView },
  { path: '/dashboard', name: 'dashboard', component: DashboardView },
  { path: '/enterprise', name: 'enterprise', component: EnterpriseView },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

export default createRouter({ history: createWebHistory(), routes })
