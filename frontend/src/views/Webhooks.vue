<template>
  <div class="webhooks-page">
    <div v-if="loading" style="display:flex;gap:16px;margin-bottom:16px">
      <el-skeleton-item variant="rect" style="width:30%;height:80px;border-radius:12px" />
      <el-skeleton-item variant="rect" style="width:30%;height:80px;border-radius:12px" />
      <el-skeleton-item variant="rect" style="width:30%;height:80px;border-radius:12px" />
    </div>
    <div v-else>
      <el-row :gutter="16" style="margin-bottom:16px">
        <el-col :span="6" v-for="s in stats" :key="s.key">
          <el-card shadow="never" class="stat-card">
            <div class="stat-val" :style="{color:s.color}">{{ s.val }}</div>
            <div class="stat-lbl">{{ s.label }}</div>
          </el-card>
        </el-col>
      </el-row>
    </div>
    <el-card shadow="never" class="page-card">
      <template #header>
        <div class="card-header">
          <span>📡 GitHub Webhook 事件</span>
          <div style="display:flex;gap:8px">
            <el-button size="small" @click="load">刷新</el-button>
            <el-popconfirm title="清除所有事件？" @confirm="clear"><template #reference><el-button size="small" type="danger" plain>清除</el-button></template></el-popconfirm>
          </div>
        </div>
      </template>
      <el-skeleton :loading="loading" animated>
        <template #default>
          <el-table :data="events" stripe size="small" v-if="events.length">
            <el-table-column prop="event_type" label="类型" width="120">
              <template #default="{row}"><el-tag :type="row.event_type === 'push'?'success':row.event_type === 'pull_request'?'warning':'info'" size="small">{{ row.event_type }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="repo" label="仓库" min-width="140" />
            <el-table-column prop="action" label="动作" width="80" />
            <el-table-column prop="sender" label="触发者" width="100" />
            <el-table-column label="时间" width="160"><template #default="{row}">{{ new Date(row.timestamp).toLocaleString() }}</template></el-table-column>
            <el-table-column label="详情" width="60"><template #default="{row}"><el-button text size="small" @click="showDetail(row)">查看</el-button></template></el-table-column>
          </el-table>
          <el-empty v-else-if="!loading && !err" description="暂无 Webhook 事件" />
          <el-empty v-else description="加载失败"><template #extra><el-button size="small" @click="load">重试</el-button></template></el-empty>
        </template>
      </el-skeleton>
    </el-card>
    <el-dialog v-model="detailVisible" title="事件详情" width="700px">
      <pre class="detail-code">{{ detailData }}</pre>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { webhookEvents, webhookStats, clearWebhooks } from '@/api'
const loading = ref(true); const err = ref(false)
const events = ref<any[]>([]); const stats = ref<any[]>([])
const detailVisible = ref(false); const detailData = ref('')
const load = async () => {
  loading.value = true; err.value = false
  try {
    const [es, ss] = await Promise.all([webhookEvents(), webhookStats()])
    events.value = es.events||[]
    stats.value = [
      {key:'total',label:'总事件',val:ss.total_events||0,color:'#6366f1'},
      {key:'push',label:'Push',val:ss.by_type?.push||0,color:'#10b981'},
      {key:'pr',label:'PR',val:ss.by_type?.pull_request||0,color:'#f59e0b'},
      {key:'other',label:'其他',val:(ss.total_events||0)-((ss.by_type?.push||0)+(ss.by_type?.pull_request||0)),color:'#94a3b8'}
    ]
  } catch { err.value = true } finally { loading.value = false }
}
const clear = async () => { await clearWebhooks(); load() }
const showDetail = (row:any) => { detailVisible.value = true; detailData.value = JSON.stringify(row, null, 2) }
onMounted(load)
</script>
<style scoped>
.webhooks-page{max-width:1200px;padding-bottom:32px}
.stat-card{background:var(--bg-card);border:1px solid var(--border-subtle);border-radius:12px;text-align:center;padding:16px}
.stat-val{font-size:28px;font-weight:700;line-height:1.2}
.stat-lbl{font-size:12px;color:var(--text-muted);margin-top:4px}
.page-card{background:var(--bg-card);border:1px solid var(--border-subtle);border-radius:12px}
.card-header{display:flex;justify-content:space-between;align-items:center;font-weight:600}
.detail-code{background:var(--bg-sidebar);border:1px solid var(--border-color);border-radius:8px;padding:12px;font-size:12px;white-space:pre;overflow:auto;max-height:400px;color:var(--text-primary)}
</style>
