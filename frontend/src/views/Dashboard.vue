<template>
  <div class="dashboard">
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="6" v-for="card in statCards" :key="card.title">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" :style="{ color: card.color }">{{ card.value }}</div>
          <div class="stat-label">{{ card.title }}</div>
          <div class="stat-sub">{{ card.sub }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="14">
        <el-card shadow="never" class="section-card">
          <template #header>
            <div class="card-header">
              <span>🧠 协调中心</span>
              <el-button text type="primary" @click="$router.push('/coordinator')">进入</el-button>
            </div>
          </template>
          <div class="coordinator-box">
            <el-input
              v-model="taskInput"
              type="textarea"
              :rows="2"
              placeholder="输入任务描述… 例如: 扫描 GitHub 热门 Python 项目"
              style="margin-bottom:12px"
            />
            <el-button type="primary" :loading="taskLoading" @click="submitTask" style="width:100%">
              {{ taskLoading ? '执行中…' : '🚀 执行任务' }}
            </el-button>
            <div v-if="taskResult" class="task-result">
              <pre>{{ JSON.stringify(taskResult, null, 2) }}</pre>
            </div>
          </div>
        </el-card>

        <el-card shadow="never" class="section-card" style="margin-top:16px">
          <template #header>
            <div class="card-header">
              <span>⚙️ 引擎状态</span>
              <el-button text type="primary" @click="loadEngineStatus">刷新</el-button>
            </div>
          </template>
          <div v-if="engineStatus.length" class="engine-grid">
            <div class="engine-item" v-for="eng in engineStatus" :key="eng.name">
              <div class="engine-name">{{ eng.name }}</div>
              <el-tag :type="eng.active ? 'success' : 'warning'" size="small">
                {{ eng.engine }}
              </el-tag>
              <div class="engine-detail">{{ eng.detail }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card shadow="never" class="section-card">
          <template #header>
            <div class="card-header">
              <span>⚡ 系统状态</span>
              <el-button text type="primary" @click="refresh">刷新</el-button>
            </div>
          </template>
          <div v-if="systemStatus" class="status-list">
            <div class="status-item" v-for="(v, k) in filteredStatus" :key="k">
              <span class="status-key">{{ k }}</span>
              <span class="status-val">{{ v }}</span>
            </div>
          </div>
          <el-empty v-else description="系统未连接" />
        </el-card>

        <el-card shadow="never" class="section-card" style="margin-top:16px">
          <template #header>
            <div class="card-header">
              <span>📋 活跃任务</span>
              <el-button text type="primary" @click="$router.push('/scheduler')">管理</el-button>
            </div>
          </template>
          <div v-if="tasks.length" class="task-list-mini">
            <div class="task-mini-item" v-for="t in tasks.slice(0,5)" :key="t.id">
              <span>{{ t.name }}</span>
              <el-tag :type="t.status === 'running' ? 'success' : 'info'" size="small">
                {{ t.status }}
              </el-tag>
            </div>
          </div>
          <el-empty v-else description="无调度任务" />
        </el-card>

        <el-card shadow="never" class="section-card" style="margin-top:16px">
          <template #header>
            <div class="card-header">
              <span>📊 队列/管线/事件</span>
            </div>
          </template>
          <div v-if="extraStats" class="status-list">
            <div class="status-item"><span class="status-key">队列待处理</span><span class="status-val">{{ extraStats.queue_pending || 0 }}</span></div>
            <div class="status-item"><span class="status-key">队列失败</span><span class="status-val">{{ extraStats.queue_failed || 0 }}</span></div>
            <div class="status-item"><span class="status-key">管线活跃</span><span class="status-val">{{ extraStats.pipeline_active || 0 }}</span></div>
            <div class="status-item"><span class="status-key">事件总数</span><span class="status-val">{{ extraStats.events_total || 0 }}</span></div>
          </div>
          <el-empty v-else description="暂无数据" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getSystemStatus, getSchedulerTasks, getSchedulerStatus, executeTask, getDiagnosis, getQueueStats, getPipelines, getEventsStats, getMonitorRealtime } from '@/api'

const taskInput = ref('')
const taskLoading = ref(false)
const taskResult = ref(null)
const systemStatus = ref(null)
const tasks = ref([])
const engineStatus = ref([])
const extraStats = ref(null)

const statCards = ref([
  { title: '模块总数', value: '-', color: '#6366f1', sub: 'registered' },
  { title: '调度任务', value: '-', color: '#10b981', sub: 'scheduler' },
  { title: '队列积压', value: '-', color: '#f59e0b', sub: 'pending' },
  { title: '运行时间', value: '-', color: '#06b6d4', sub: 'uptime' },
])

const filteredStatus = computed(() => {
  if (!systemStatus.value) return {}
  const s = systemStatus.value
  return {
    'API 版本': s.api_version || s.version || '-',
    '运行时间': s.uptime_human || `${s.uptime_seconds || 0}s`,
    '模块数': s.modules_registered || s.modules_total || s.count || '-',
    '状态': s.success ? '✅ 正常' : '❌ 异常',
  }
})

const submitTask = async () => {
  const desc = taskInput.value.trim()
  if (!desc) return
  taskLoading.value = true
  taskResult.value = null
  try {
    const res = await executeTask(desc)
    taskResult.value = res
  } catch (e) {
    taskResult.value = { error: e.message }
  }
  taskLoading.value = false
}

const loadEngineStatus = async () => {
  try {
    const sch = await getSchedulerStatus()
    const queue = await getQueueStats()
    const events = await getEventsStats()
    const pip = await getPipelines()
    
    extraStats.value = {
      queue_pending: queue.pending || 0,
      queue_failed: queue.failed || 0,
      pipeline_active: pip.active || pip.active_count || 0,
      events_total: events.total_events || 0,
    }
    
    engineStatus.value = [
      { name: '调度器', active: sch.running, engine: sch.engine || 'dict', detail: `${sch.active_tasks || 0}/${sch.total_tasks || 0} 任务` },
      { name: '事件引擎', active: events.success, engine: events.engine || 'dict', detail: `${events.total_events || 0} 事件` },
      { name: '管线', active: pip.success !== false, engine: 'api', detail: `${pip.count || 0} 管线` },
      { name: '任务队列', active: queue.success, engine: queue.engine || 'dict', detail: `${queue.pending || 0} 待处理` },
    ]
  } catch {}
}

const refresh = async () => {
  try {
    const [status, diag, sch] = await Promise.all([
      getSystemStatus(),
      getDiagnosis(),
      getSchedulerTasks(),
      loadEngineStatus(),
    ])
    systemStatus.value = { ...status, ...diag }
    tasks.value = sch.tasks || []
    statCards.value[0].value = diag.count || status.modules_registered || '-'
    statCards.value[1].value = sch.count || '-'
    statCards.value[3].value = diag.uptime_human || '-'
  } catch {}
}

onMounted(refresh)
</script>

<style scoped>
.dashboard { max-width: 1200px; }
.stat-card { background: #1a1a2e; border: 1px solid #2d2d44; border-radius: 12px; }
.stat-value { font-size: 32px; font-weight: 700; line-height: 1; }
.stat-label { font-size: 13px; color: #a0aec0; margin-top: 4px; }
.stat-sub { font-size: 11px; color: #4a5568; margin-top: 2px; }
.section-card { background: #1a1a2e; border: 1px solid #2d2d44; border-radius: 12px; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-size: 14px; font-weight: 600; }
.coordinator-box { display: flex; flex-direction: column; }
.task-result { margin-top: 12px; background: #0f0f1a; border-radius: 8px; padding: 12px; max-height: 200px; overflow: auto; }
.task-result pre { font-size: 12px; color: #a0aec0; white-space: pre-wrap; word-break: break-all; }
.status-list { display: flex; flex-direction: column; gap: 8px; }
.status-item { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #2d2d44; font-size: 13px; }
.status-key { color: #a0aec0; }
.status-val { color: #e2e8f0; font-weight: 500; }
.task-list-mini { display: flex; flex-direction: column; gap: 8px; }
.task-mini-item { display: flex; justify-content: space-between; align-items: center; font-size: 13px; padding: 6px 0; border-bottom: 1px solid #2d2d44; }
.engine-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.engine-item { background: #0f0f1a; border-radius: 8px; padding: 12px; }
.engine-name { font-size: 13px; color: #e2e8f0; font-weight: 600; margin-bottom: 4px; }
.engine-detail { font-size: 11px; color: #4a5568; margin-top: 4px; }
</style>
