<template>
  <el-container class="app-container">
    <!-- 侧边栏 -->
    <el-aside :width="collapsed ? '64px' : '220px'" class="app-aside">
      <div class="logo" @click="router.push('/dashboard')">
        <el-icon :size="28" color="#6366f1"><Cpu /></el-icon>
        <span v-show="!collapsed" class="logo-text">AUTO-EVO-AI</span>
      </div>

      <el-menu
        :default-active="route.path"
        :collapse="collapsed"
        background-color="transparent"
        text-color="#a0aec0"
        active-text-color="#6366f1"
        router
      >
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </el-menu>

      <div class="collapse-btn" @click="collapsed = !collapsed">
        <el-icon><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
      </div>
    </el-aside>

    <!-- 主区域 -->
    <el-container>
      <el-header class="app-header">
        <div class="header-left">
          <el-tag type="success" size="small" effect="dark" v-if="systemStatus">
            {{ systemStatus.uptime_human || '运行中' }}
          </el-tag>
          <el-tag type="info" size="small" effect="plain" style="margin-left:8px">
            V0.1
          </el-tag>
        </div>
        <div class="header-right">
          <el-tooltip content="二维码访问" placement="bottom">
            <el-button text circle @click="openQr">
              <el-icon><Share /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="刷新数据" placement="bottom">
            <el-button text circle @click="refreshAll">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getSystemStatus } from '@/api'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)
const systemStatus = ref(null)

const menuItems = [
  { path: '/dashboard', title: '监控面板', icon: 'Monitor' },
  { path: '/coordinator', title: '协调中心', icon: 'Cpu' },
  { path: '/scheduler', title: '调度器', icon: 'Timer' },
  { path: '/events', title: '事件引擎', icon: 'Bell' },
  { path: '/pipeline', title: '管线引擎', icon: 'Link' },
  { path: '/queue', title: '任务队列', icon: 'List' },
  { path: '/modules', title: '模块管理', icon: 'Grid' },
  { path: '/security', title: '安全中心', icon: 'Lock' },
  { path: '/settings', title: '系统设置', icon: 'Setting' },
]

const refreshAll = async () => {
  try {
    systemStatus.value = await getSystemStatus()
    ElMessage.success('已刷新')
  } catch {
    // server not running
  }
}

const openQr = () => {
  window.open('/api/qr', '_blank')
}

onMounted(refreshAll)
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; }

.app-container { height: 100vh; background: #0f0f1a; }

.app-aside {
  background: #1a1a2e;
  border-right: 1px solid #2d2d44;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  overflow: hidden;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  border-bottom: 1px solid #2d2d44;
  cursor: pointer;
}

.logo-text {
  font-size: 15px;
  font-weight: 700;
  color: #e2e8f0;
  white-space: nowrap;
}

.app-aside .el-menu {
  border-right: none;
  flex: 1;
}

.collapse-btn {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-top: 1px solid #2d2d44;
  cursor: pointer;
  color: #a0aec0;
  transition: color 0.2s;
}

.collapse-btn:hover { color: #6366f1; }

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 20px;
  background: #1a1a2e;
  border-bottom: 1px solid #2d2d44;
}

.header-left, .header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-right .el-button { color: #a0aec0; }
.header-right .el-button:hover { color: #6366f1; }

.app-main {
  background: #0f0f1a;
  padding: 20px;
  overflow-y: auto;
}

/* Element Plus 暗色覆盖 */
.el-menu--dark { --el-menu-bg-color: transparent; }
.el-menu-item { --el-menu-hover-bg-color: rgba(99,102,241,0.08); }
</style>
