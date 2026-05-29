<template>
  <div class="queue-page">
    <el-skeleton :loading="loading" animated>
      <template #default>
        <el-row :gutter="12" style="margin-bottom:16px">
          <el-col :span="4" v-for="s in ['total','pending','running','completed','failed','backlog']" :key="s">
            <el-card shadow="never" class="mini-stat" :body-style="{padding:'12px'}">
              <div class="ms-val" :style="{color:colors[s]||'#e2e8f0'}">{{ loadErr ? '-' : (stats[s]||0) }}</div>
              <div class="ms-lbl">{{ labels[s]||s }}</div>
            </el-card>
          </el-col>
        </el-row>
      </template>
    </el-skeleton>
    <el-card shadow="never" class="page-card">
      <template #header><div class="card-header"><span>📋 队列任务</span><el-button size="small" type="primary" @click="showEnqueue=true" :loading="loading">入队</el-button></div></template>
      <el-skeleton :loading="loading" animated>
        <template #default>
          <el-table :data="tasks" stripe v-if="tasks.length && !loadErr">
            <el-table-column prop="name" label="任务" />
            <el-table-column prop="type" label="类型" width="80" />
            <el-table-column prop="status" label="状态" width="80"><template #default="{row}"><el-tag :type="tagMap[row.status]||'info'" size="small">{{row.status}}</el-tag></template></el-table-column>
            <el-table-column prop="priority" label="优先级" width="70" />
            <el-table-column label="操作" width="140">
              <template #default="{row}">
                <el-button v-if="row.status==='pending'" text size="small" @click="cancel(row.id)">取消</el-button>
                <el-button v-if="row.status==='failed'" text size="small" @click="retry(row.id)">重试</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else-if="loadErr" description="加载失败"><template #extra><el-button size="small" @click="load">重试</el-button></template></el-empty>
          <el-empty v-else description="队列为空" />
        </template>
      </el-skeleton>
    </el-card>
    <el-dialog v-model="showEnqueue" title="入队任务" width="400px">
      <el-form :model="form" label-width="60px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型"><el-select v-model="form.type" style="width:100%"><el-option label="执行" value="execute" /><el-option label="通知" value="notify" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="showEnqueue=false">取消</el-button><el-button type="primary" @click="enqueue">入队</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getQueueStats, getQueueTasks, enqueueTask, cancelTask, retryTask } from '@/api'
const loading = ref(true); const loadErr = ref(false)
const stats = ref({}); const tasks = ref([])
const showEnqueue = ref(false); const form = ref({name:'',type:'execute'})
const colors = {total:'#6366f1',pending:'#f59e0b',running:'#06b6d4',completed:'#10b981',failed:'#ef4444',backlog:'#f59e0b'}
const labels = {total:'总任务',pending:'待处理',running:'运行中',completed:'已完成',failed:'失败',backlog:'积压'}
const tagMap = {pending:'warning',running:'primary',completed:'success',failed:'danger',cancelled:'info'}
const load = async () => {
  loading.value = true; loadErr.value = false
  try { const [qs, qt] = await Promise.all([getQueueStats(), getQueueTasks()]); stats.value = qs; tasks.value = qt.tasks||[] }
  catch { loadErr.value = true }
  finally { loading.value = false }
}
const enqueue = async () => { await enqueueTask(form.value); showEnqueue.value=false; load() }
const cancel = async (id) => { await cancelTask(id); load() }
const retry = async (id) => { await retryTask(id); load() }
onMounted(load)
</script>
<style scoped>
.queue-page{max-width:1000px}
.mini-stat{background:#1a1a2e;border:1px solid #2d2d44;border-radius:8px;text-align:center}
.ms-val{font-size:20px;font-weight:700}
.ms-lbl{font-size:11px;color:#a0aec0}
.page-card{background:#1a1a2e;border:1px solid #2d2d44;border-radius:12px}
.card-header{display:flex;justify-content:space-between;align-items:center;font-weight:600}
</style>
