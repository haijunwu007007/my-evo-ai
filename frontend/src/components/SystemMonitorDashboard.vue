<template>
  <div class="sysmon-dashboard">
    <!-- 概览卡片 -->
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card cpu-card">
          <div class="metric-label">CPU</div>
          <div class="metric-value">{{ cpuPercent }}%</div>
          <el-progress :percentage="cpuPercent" :stroke-width="6" :color="cpuColor" :show-text="false" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card mem-card">
          <div class="metric-label">内存</div>
          <div class="metric-value">{{ memoryPercent }}%</div>
          <el-progress :percentage="memoryPercent" :stroke-width="6" :color="memColor" :show-text="false" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card disk-card">
          <div class="metric-label">磁盘</div>
          <div class="metric-value">{{ diskPercent }}%</div>
          <el-progress :percentage="diskPercent" :stroke-width="6" :color="diskColor" :show-text="false" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card alert-card">
          <div class="metric-label">告警</div>
          <div class="metric-value">{{ criticalAlertCount }}<small style="font-size:14px;color:#999">/{{ activeAlertCount }}</small></div>
          <div class="metric-sub">严重/活跃</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- CPU 趋势图 -->
    <el-card shadow="never" class="section-card">
      <template #header><span><b>CPU 趋势 (最近 10min)</b></span></template>
      <div ref="cpuChartRef" style="height:200px" />
    </el-card>

    <!-- 进程 Top 10 -->
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card shadow="never" class="section-card">
          <template #header><span><b>进程 Top 10 (按 CPU)</b></span></template>
          <el-table :data="processes" size="small" stripe max-height="300">
            <el-table-column prop="pid" label="PID" width="70" />
            <el-table-column prop="name" label="名称" min-width="140" />
            <el-table-column prop="cpu_percent" label="CPU%" width="80" sortable>
              <template #default="{ row }"><span :class="row.cpu_percent > 50 ? 'text-danger' : ''">{{ row.cpu_percent }}%</span></template>
            </el-table-column>
            <el-table-column prop="memory_percent" label="内存%" width="80" sortable />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never" class="section-card">
          <template #header><span><b>活跃告警 ({{ alerts.length }})</b></span></template>
          <div v-if="alerts.length === 0" style="text-align:center;color:#999;padding:20px">暂无告警</div>
          <el-timeline v-else>
            <el-timeline-item
              v-for="a in alerts.slice(0,8)" :key="a.alert_id"
              :timestamp="a.time"
              :type="a.severity === 'critical' ? 'danger' : 'warning'"
            >
              {{ a.message }}
              <el-button text size="small" @click="ack(a.alert_id)" v-if="!a.acked">确认</el-button>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useSystemMonitorStore } from '../stores/systemMonitor'

const store = useSystemMonitorStore()
const cpuChartRef = ref(null)
const processes = ref([])
const alerts = ref([])

const cpuPercent = computed(() => store.cpuPercent)
const memoryPercent = computed(() => store.memoryPercent)
const diskPercent = computed(() => store.diskPercent)
const activeAlertCount = computed(() => store.activeAlertCount)
const criticalAlertCount = computed(() => store.criticalAlertCount)

const cpuColor = computed(() => cpuPercent.value > 90 ? '#f56c6c' : cpuPercent.value > 75 ? '#e6a23c' : '#67c23a')
const memColor = computed(() => memoryPercent.value > 90 ? '#f56c6c' : memoryPercent.value > 80 ? '#e6a23c' : '#409eff')
const diskColor = computed(() => diskPercent.value > 95 ? '#f56c6c' : diskPercent.value > 85 ? '#e6a23c' : '#909399')

async function ack(id) { await store.ackAlert(id); alerts.value = store.alerts }

function renderChart() {
  const el = cpuChartRef.value
  if (!el || !store.cpuHistory.length) return
  import('echarts').then(echarts => {
    if (el._chart) el._chart.dispose()
    const chart = echarts.init(el)
    el._chart = chart
    chart.setOption({
      grid: { left: 50, right: 20, top: 10, bottom: 25 },
      xAxis: { type: 'time', axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', min: 0, max: 100, axisLabel: { fontSize: 10, formatter: '{value}%' } },
      series: [{
        type: 'line', smooth: true, showSymbol: false, areaStyle: { opacity: 0.15 },
        data: store.cpuHistory.map(p => [p.time, p.value]),
        lineStyle: { width: 2 }, itemStyle: { color: '#409eff' },
      }],
      tooltip: { trigger: 'axis' },
    })
    chart.resize()
  })
}

onMounted(() => { store.startPolling(5000); renderChart() })
onUnmounted(() => store.stopPolling())
watch(() => store.cpuHistory.length, () => nextTick(renderChart))
</script>

<style scoped>
.metric-card { text-align: center; cursor: default; }
.metric-label { font-size: 13px; color: #999; }
.metric-value { font-size: 32px; font-weight: 700; margin: 4px 0; }
.metric-sub { font-size: 12px; color: #ccc; }
.section-card { margin-top: 16px; }
.text-danger { color: #f56c6c; font-weight: 700; }
</style>
