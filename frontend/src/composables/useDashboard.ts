/**
 * AUTO-EVO-AI V0.1 — Dashboard 数据组合式函数
 * 职责：将 Dashboard.vue 的数据提取、响应式状态和生命周期逻辑分离为可测试的单元
 */
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { getSystemStatus, getSchedulerTasks, getSchedulerStatus, getDiagnosis, getQueueStats, getPipelines, getEventsStats } from '@/api'

export interface StatCard {
  title: string
  value: string | number
  color: string
  icon: string
  trend: number
}

export interface GradeItem {
  name: string
  value: number
  color: string
}

export interface LinePoint {
  times: string[]
  values: number[]
}

export function useDashboard() {
  // ── 基础状态 ──
  const systemStatus = ref<any>(null)
  const tasks = ref<any[]>([])
  const engineStatus = ref<any[]>([])
  const extraStats = ref<any>(null)
  const categories = ref<any[]>([])

  // ── 统计卡片（计算属性） ──
  const statCards = computed<StatCard[]>(() => {
    const s = systemStatus.value
    if (!s) return [
      { title: '模块总数', value: '-', color: '#6366f1', icon: '📦', trend: 0 },
      { title: '已加载', value: '-', color: '#10b981', icon: '⚡', trend: 0 },
      { title: 'API 状态', value: '-', color: '#f59e0b', icon: '🔌', trend: 0 },
      { title: '运行时间', value: '-', color: '#ef4444', icon: '⏱', trend: 0 },
    ]
    const modulesTotal = s.modules_total ?? s.system_info?.modules_total ?? 0
    const loaded = s.modules_loaded ?? 0
    const uptime = s.uptime ?? s.system_info?.uptime ?? 0
    const hours = Math.floor(uptime / 3600)
    const minutes = Math.floor((uptime % 3600) / 60)
    return [
      { title: '模块总数', value: `${modulesTotal}`, color: '#6366f1', icon: '📦', trend: 0 },
      { title: '已加载', value: `${loaded}`, color: '#10b981', icon: '⚡', trend: loaded > 0 ? 5 : 0 },
      { title: 'API 状态', value: '运行中', color: '#f59e0b', icon: '🔌', trend: 0 },
      { title: '运行时间', value: `${hours}h ${minutes}m`, color: '#ef4444', icon: '⏱', trend: 0 },
    ]
  })

  // ── 等级分布 ──
  const gradeData = computed<GradeItem[]>(() => {
    const s = systemStatus.value
    if (!s?.modules) return [
      { name: 'Grade A', value: 0, color: '#10b981' },
      { name: 'Grade B', value: 0, color: '#3b82f6' },
      { name: 'Grade C', value: 0, color: '#f59e0b' },
    ]
    const mods = s.modules
    const grades: Record<string, number> = {}
    for (const m of (Array.isArray(mods) ? mods : [])) {
      const g = m.grade || 'N/A'
      grades[g] = (grades[g] || 0) + 1
    }
    const colors: Record<string, string> = {
      A: '#10b981', B: '#3b82f6', C: '#f59e0b', 'N/A': '#6b7280',
    }
    return Object.entries(grades).map(([name, value]) => ({
      name: `Grade ${name}`,
      value,
      color: colors[name] || '#6b7280',
    }))
  })

  // ── 折线图数据 ──
  const lineData = ref<LinePoint>({ times: [], values: [] })

  // ── 数据加载 ──
  async function fetchMetrics() {
    try {
      const [status, schedTasks, schedStatus, diagnosis, queue, pipelines, eventsStats] = await Promise.allSettled([
        getSystemStatus(), getSchedulerTasks(), getSchedulerStatus(),
        getDiagnosis(), getQueueStats(), getPipelines(), getEventsStats(),
      ])
      if (status.status === 'fulfilled') systemStatus.value = status.value
      if (schedTasks.status === 'fulfilled') tasks.value = schedTasks.value?.tasks ?? schedTasks.value?.data ?? []
      if (diagnosis.status === 'fulfilled') extraStats.value = diagnosis.value
      // 如果后端有 metrics 则更新图表
      if (status.status === 'fulfilled' && status.value?.metrics?.requests?.length) {
        const m = status.value.metrics
        lineData.value.times = m.times ?? []
        lineData.value.values = m.requests ?? []
      }
    } catch (e: any) {
      console.warn('Dashboard fetchMetrics error:', e?.message ?? e)
    }
  }

  // ── 生命周期 ──
  let interval: ReturnType<typeof setInterval> | null = null

  function startPolling() {
    fetchMetrics()
    interval = setInterval(fetchMetrics, 15000)
  }

  function stopPolling() {
    if (interval) { clearInterval(interval); interval = null }
  }

  return {
    systemStatus, tasks, engineStatus, extraStats, categories,
    statCards, gradeData, lineData,
    fetchMetrics, startPolling, stopPolling,
  }
}
