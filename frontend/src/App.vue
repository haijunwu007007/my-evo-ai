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
          <el-tooltip :content="darkMode ? '切换亮色' : '切换暗色'" placement="bottom">
            <el-button text circle @click="toggleTheme" class="theme-btn">
              <span>{{ darkMode ? '🌓' : '☀️' }}</span>
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
const darkMode = ref(true)
let hTimer = null

// ── 亮暗主题切换 ────────────────────────────────────
const toggleTheme = () => {
  darkMode.value = !darkMode.value
  document.documentElement.setAttribute('data-theme', darkMode.value ? 'dark' : 'light')
  localStorage.setItem('evo_theme', darkMode.value ? 'dark' : 'light')
}

onMounted(() => {
  const saved = localStorage.getItem('evo_theme')
  if (saved === 'light') { darkMode.value = false; document.documentElement.setAttribute('data-theme', 'light') }
  else { document.documentElement.setAttribute('data-theme', 'dark') }
})

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
/* ── CSS 变量主题系统 ────────────────────────────── */
:root, [data-theme="dark"] {
  --bg-body: #0d0d1a;
  --bg-sidebar: #111127;
  --bg-header: #111127;
  --bg-main: #0d0d1a;
  --bg-card: #1a1a2e;
  --border-color: #1e1e3a;
  --border-subtle: #2d2d44;
  --text-primary: #e2e8f0;
  --text-muted: #7b8fa1;
  --text-dim: #4a5568;
}
[data-theme="light"] {
  --bg-body: #f1f5f9;
  --bg-sidebar: #ffffff;
  --bg-header: #ffffff;
  --bg-main: #f1f5f9;
  --bg-card: #ffffff;
  --border-color: #e2e8f0;
  --border-subtle: #cbd5e1;
  --text-primary: #1e293b;
  --text-muted: #64748b;
  --text-dim: #94a3b8;
}
[data-theme="light"] .el-card { --el-card-bg-color: #ffffff; }
[data-theme="light"] .el-table { --el-table-bg-color: #ffffff; --el-table-border-color: #e2e8f0; --el-table-header-bg-color: #f8fafc; color: #1e293b; }

* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; }

.app-container { height: 100vh; background: var(--bg-body); }

/* ── 侧边栏 ────────────────────────────────────────── */
.app-aside {
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-color);
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
  border-bottom: 1px solid var(--border-color);
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
.logo-text { font-size: 14px; font-weight: 700; color: var(--text-primary); white-space: nowrap; letter-spacing: 0.5px; }
.logo-sub { font-size: 10px; color: #6366f1; margin-top: 1px; }

.sys-pulse {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-bottom: 1px solid var(--border-color);
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
.pulse-text { font-size: 11px; color: var(--text-muted); flex: 1; }
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
  color: var(--text-muted);
  font-size: 13px;
}
.nav-menu :deep(.el-menu-item.is-active) {
  background: rgba(99,102,241,0.12) !important;
  color: #6366f1 !important;
  font-weight: 600;
}
.nav-menu :deep(.el-menu-item:hover) { background: rgba(99,102,241,0.06) !important; color: var(--text-primary); }

.collapse-btn {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-top: 1px solid var(--border-color);
  cursor: pointer;
  color: var(--text-dim);
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
  background: var(--bg-header);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.breadcrumb-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.header-tags { display: flex; align-items: center; gap: 6px; }
.ver-tag { background: rgba(99,102,241,0.15) !important; color: #6366f1 !important; border-color: transparent !important; }
.header-right { display: flex; align-items: center; gap: 8px; }
.theme-btn { font-size: 16px; line-height: 1; }
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
  color: var(--text-muted);
  transition: all 0.2s;
}
.avatar-btn:hover { background: rgba(99,102,241,0.2); color: #6366f1; }

/* ── 主内容 ─────────────────────────────────────────── */
.app-main {
  background: var(--bg-main);
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
.el-card { background: var(--bg-card) !important; border-color: var(--border-subtle) !important; }
.el-table { --el-table-bg-color: var(--bg-card); --el-table-border-color: var(--border-subtle); --el-table-header-bg-color: var(--bg-sidebar); --el-fill-color-lighter: rgba(99,102,241,0.04); color: var(--text-primary); }
.el-input__wrapper { background: var(--bg-sidebar) !important; border-color: var(--border-subtle) !important; }
.el-input__inner { color: var(--text-primary) !important; }
.el-select .el-input__wrapper { background: var(--bg-sidebar) !important; }
.el-drawer { background: var(--bg-card) !important; }
.el-drawer__header { border-bottom: 1px solid var(--border-subtle); color: var(--text-primary); }
.el-skeleton { --el-skeleton-color: var(--border-subtle); --el-skeleton-to-color: var(--border-color); }
.el-empty__description p { color: var(--text-dim) !important; }
.el-radio-button__inner { background: var(--bg-card); border-color: var(--border-subtle); color: var(--text-muted); }
.el-radio-button__original-radio:checked + .el-radio-button__inner { background: #6366f1; border-color: #6366f1; color: #fff; }
.el-descriptions { --el-descriptions-item-bordered-label-background: var(--bg-sidebar); }
.el-descriptions__label { color: var(--text-muted) !important; }
.el-descriptions__content { color: var(--text-primary) !important; }
</style>
