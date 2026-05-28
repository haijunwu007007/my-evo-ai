<template>
  <el-container class="app-container">
    <!-- 侧边栏 -->
    <el-aside :width="collapsed ? '64px' : '220px'" class="app-aside">
      <!-- Logo -->
      <div class="logo" @click="router.push('/dashboard')">
        <div class="logo-icon">
          <el-icon :size="22" color="#6366f1"><Cpu /></el-icon>
        </div>
        <transition name="logo-fade">
          <div v-show="!collapsed" class="logo-texts">
            <span class="logo-text">AUTO-EVO-AI</span>
            <span class="logo-sub">V0.1 · Enterprise</span>
          </div>
        </transition>
      </div>

      <!-- 系统健康指示 -->
      <div v-show="!collapsed" class="sys-pulse">
        <div class="pulse-dot" :class="isOnline ? 'online' : 'offline'"></div>
        <span class="pulse-text">{{ isOnline ? '系统运行中' : '离线模式' }}</span>
        <span class="pulse-count" v-if="moduleCount">{{ moduleCount }}</span>
      </div>

      <!-- 导航菜单 -->
      <el-menu
        :default-active="route.path"
        :collapse="collapsed"
        background-color="transparent"
        text-color="#7b8fa1"
        active-text-color="#6366f1"
        router
        class="nav-menu"
      >
        <el-menu-item-group v-if="!collapsed" title="核心功能">
          <el-menu-item v-for="item in coreMenu" :key="item.path" :index="item.path" class="nav-item">
            <el-icon><component :is="item.icon" /></el-icon>
            <template #title>
              <span>{{ item.title }}</span>
              <el-badge v-if="item.badge" :value="item.badge" type="danger" class="nav-badge" />
            </template>
          </el-menu-item>
        </el-menu-item-group>
        <template v-else>
          <el-menu-item v-for="item in allMenu" :key="item.path" :index="item.path" class="nav-item">
            <el-icon><component :is="item.icon" /></el-icon>
            <template #title>{{ item.title }}</template>
          </el-menu-item>
        </template>

        <el-menu-item-group v-if="!collapsed" title="运维管理">
          <el-menu-item v-for="item in opsMenu" :key="item.path" :index="item.path" class="nav-item">
            <el-icon><component :is="item.icon" /></el-icon>
            <template #title>{{ item.title }}</template>
          </el-menu-item>
        </el-menu-item-group>
      </el-menu>

      <!-- 底部折叠按钮 -->
      <div class="collapse-btn" @click="collapsed = !collapsed">
        <el-icon size="16"><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
        <span v-show="!collapsed" style="font-size:12px;margin-left:6px">收起</span>
      </div>
    </el-aside>

    <!-- 主区域 -->
    <el-container>
      <!-- 顶部 Header -->
      <el-header class="app-header">
        <div class="header-left">
          <div class="breadcrumb-title">{{ currentTitle }}</div>
          <div class="header-tags">
            <el-tag type="success" size="small" effect="dark" v-if="systemStatus?.uptime_human">
              ⏱ {{ systemStatus.uptime_human }}
            </el-tag>
            <el-tag size="small" effect="dark" class="ver-tag">V0.1</el-tag>
            <el-tag type="warning" size="small" effect="dark" v-if="systemStatus?.modules_registered">
              📦 {{ systemStatus.modules_registered }} 模块
            </el-tag>
          </div>
        </div>
        <div class="header-right">
          <el-tooltip content="刷新数据" placement="bottom">
            <el-button text circle @click="refreshAll" :loading="refreshing">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="GitHub" placement="bottom">
            <el-button text circle @click="openGithub">
              <el-icon><Share /></el-icon>
            </el-button>
          </el-tooltip>
          <div class="avatar-btn" @click="$router.push('/settings')">⚙</div>
        </div>
      </el-header>

      <!-- 页面内容 -->
      <el-main class="app-main">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getSystemStatus } from '@/api'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)
const systemStatus = ref(null)
const isOnline = ref(false)
const moduleCount = ref('')
const refreshing = ref(false)
let hTimer = null

const coreMenu = [
  { path: '/dashboard',     title: '监控面板', icon: 'Monitor' },
  { path: '/sysmon',        title: '系统监控', icon: 'TrendCharts' },
  { path: '/coordinator',   title: '协调中心', icon: 'Cpu' },
  { path: '/scheduler',     title: '调度器',   icon: 'Timer' },
  { path: '/modules',       title: '模块管理', icon: 'Grid' },
  { path: '/data-analysis', title: '数据分析', icon: 'DataAnalysis' },
]

const opsMenu = [
  { path: '/events',   title: '事件引擎', icon: 'Bell' },
  { path: '/pipeline', title: '管线引擎', icon: 'Link' },
  { path: '/queue',    title: '任务队列', icon: 'List' },
  { path: '/security', title: '安全中心', icon: 'Lock' },
  { path: '/sso-auth', title: 'SSO 管理', icon: 'User' },
  { path: '/settings', title: '系统设置', icon: 'Setting' },
]

const allMenu = [...coreMenu, ...opsMenu]

const currentTitle = computed(() => {
  const all = [...coreMenu, ...opsMenu]
  return all.find(m => m.path === route.path)?.title || 'AUTO-EVO-AI'
})

const refreshAll = async () => {
  refreshing.value = true
  try {
    const s = await getSystemStatus()
    systemStatus.value = s
    // API 返回 {status: "running"} 而非 {success: true}
    isOnline.value = s?.status === 'running' || !!s?.success
    // API 返回 modules_total 而非 modules_registered
    moduleCount.value = s?.modules_total ? `${s.modules_total}` : (s?.modules_registered ? `${s.modules_registered}` : '')
  } catch {
    isOnline.value = false
  }
  refreshing.value = false
}

const openGithub = () => window.open('https://github.com/haijunwu007007/my-evo-ai', '_blank')

onMounted(() => {
  refreshAll()
  hTimer = setInterval(refreshAll, 30000)
})
onUnmounted(() => clearInterval(hTimer))
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; }

.app-container { height: 100vh; background: #0d0d1a; }

/* ── 侧边栏 ────────────────────────────────────────── */
.app-aside {
  background: #111127;
  border-right: 1px solid #1e1e3a;
  display: flex;
  flex-direction: column;
  transition: width 0.25s cubic-bezier(0.4,0,0.2,1);
  overflow: hidden;
}

.logo {
  height: 58px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  border-bottom: 1px solid #1e1e3a;
  cursor: pointer;
  background: linear-gradient(135deg, rgba(99,102,241,0.08) 0%, transparent 60%);
  flex-shrink: 0;
}
.logo-icon {
  width: 36px;
  height: 36px;
  background: rgba(99,102,241,0.15);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.logo-texts { display: flex; flex-direction: column; }
.logo-text { font-size: 14px; font-weight: 700; color: #e2e8f0; white-space: nowrap; letter-spacing: 0.5px; }
.logo-sub { font-size: 10px; color: #6366f1; margin-top: 1px; }

.sys-pulse {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-bottom: 1px solid #1e1e3a;
  flex-shrink: 0;
}
.pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.pulse-dot.online { background: #10b981; box-shadow: 0 0 0 2px rgba(16,185,129,0.2); animation: pulse 2s infinite; }
.pulse-dot.offline { background: #ef4444; }
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 2px rgba(16,185,129,0.2); }
  50% { box-shadow: 0 0 0 5px rgba(16,185,129,0.05); }
}
.pulse-text { font-size: 11px; color: #7b8fa1; flex: 1; }
.pulse-count { font-size: 10px; background: rgba(99,102,241,0.15); color: #6366f1; padding: 1px 6px; border-radius: 8px; }

.nav-menu { border-right: none !important; flex: 1; overflow-y: auto; overflow-x: hidden; }
.nav-menu :deep(.el-menu-item-group__title) {
  font-size: 10px !important;
  color: #3d3d5c !important;
  padding: 12px 14px 4px !important;
  letter-spacing: 1px;
  text-transform: uppercase;
}
.nav-menu :deep(.el-menu-item) {
  height: 40px;
  line-height: 40px;
  margin: 1px 8px;
  border-radius: 8px;
  color: #7b8fa1;
  font-size: 13px;
}
.nav-menu :deep(.el-menu-item.is-active) {
  background: rgba(99,102,241,0.12) !important;
  color: #6366f1 !important;
  font-weight: 600;
}
.nav-menu :deep(.el-menu-item:hover) { background: rgba(99,102,241,0.06) !important; color: #c0c6d4; }

.collapse-btn {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-top: 1px solid #1e1e3a;
  cursor: pointer;
  color: #4a5568;
  transition: all 0.2s;
  flex-shrink: 0;
  font-size: 13px;
}
.collapse-btn:hover { color: #6366f1; background: rgba(99,102,241,0.06); }

/* ── 顶部 Header ───────────────────────────────────── */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 52px;
  padding: 0 20px;
  background: #111127;
  border-bottom: 1px solid #1e1e3a;
  flex-shrink: 0;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.breadcrumb-title { font-size: 15px; font-weight: 600; color: #e2e8f0; }
.header-tags { display: flex; align-items: center; gap: 6px; }
.ver-tag { background: rgba(99,102,241,0.15) !important; color: #6366f1 !important; border-color: transparent !important; }
.header-right { display: flex; align-items: center; gap: 8px; }
.avatar-btn {
  width: 32px;
  height: 32px;
  background: rgba(99,102,241,0.1);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 16px;
  color: #7b8fa1;
  transition: all 0.2s;
}
.avatar-btn:hover { background: rgba(99,102,241,0.2); color: #6366f1; }

/* ── 主内容 ─────────────────────────────────────────── */
.app-main {
  background: #0d0d1a;
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

/* ── 页面过渡动画 ──────────────────────────────────── */
.page-enter-active, .page-leave-active { transition: opacity 0.15s, transform 0.15s; }
.page-enter-from, .page-leave-to { opacity: 0; transform: translateX(6px); }

/* ── Logo 动画 ─────────────────────────────────────── */
.logo-fade-enter-active, .logo-fade-leave-active { transition: opacity 0.2s; }
.logo-fade-enter-from, .logo-fade-leave-to { opacity: 0; }

/* ── Element Plus 全局覆盖 ────────────────────────── */
.el-card { background: #1a1a2e !important; border-color: #2d2d44 !important; }
.el-table { --el-table-bg-color: #1a1a2e; --el-table-border-color: #2d2d44; --el-table-header-bg-color: #0f0f1a; --el-fill-color-lighter: rgba(99,102,241,0.04); color: #e2e8f0; }
.el-input__wrapper { background: #0f0f1a !important; border-color: #2d2d44 !important; }
.el-input__inner { color: #e2e8f0 !important; }
.el-select .el-input__wrapper { background: #0f0f1a !important; }
.el-drawer { background: #1a1a2e !important; }
.el-drawer__header { border-bottom: 1px solid #2d2d44; color: #e2e8f0; }
.el-skeleton { --el-skeleton-color: #1f1f33; --el-skeleton-to-color: #2d2d44; }
.el-empty__description p { color: #4a5568 !important; }
.el-radio-button__inner { background: #1a1a2e; border-color: #2d2d44; color: #7b8fa1; }
.el-radio-button__original-radio:checked + .el-radio-button__inner { background: #6366f1; border-color: #6366f1; color: #fff; }
.el-descriptions { --el-descriptions-item-bordered-label-background: #0f0f1a; }
.el-descriptions__label { color: #7b8fa1 !important; }
.el-descriptions__content { color: #e2e8f0 !important; }
</style>
