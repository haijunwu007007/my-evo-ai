<template>
  <div class="scheduler-page">
    <el-card shadow="never" class="page-card">
      <template #header>
        <div class="card-header">
          <span>⏰ 调度器管理</span>
          <div style="display:flex;align-items:center;gap:8px">
            <el-tag v-if="engineLabel" :type="engineLabel.type" size="small">{{ engineLabel.text }}</el-tag>
            <el-button type="primary" size="small" @click="showCreate = true">新建任务</el-button>
            <el-button size="small" @click="refresh">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table :data="tasks" stripe style="width:100%" v-if="tasks.length" :empty-text="'暂无调度任务'">
        <el-table-column prop="name" label="任务名称" min-width="160" />
        <el-table-column prop="target_id" label="目标" min-width="120" />
        <el-table-column prop="cron" label="定时" width="120" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'running' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" @click="toggle(row.id)">{{ row.status === 'running' ? '暂停' : '恢复' }}</el-button>
            <el-button text size="small" @click="trigger(row.id)">触发</el-button>
            <el-popconfirm title="确定删除？" @confirm="remove(row.id)">
              <template #reference><el-button text size="small" type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无调度任务" />
    </el-card>

    <!-- 新建任务对话框 -->
    <el-dialog v-model="showCreate" title="新建调度任务" width="480px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="任务名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="目标类型">
          <el-select v-model="form.target_type" style="width:100%"><el-option label="模块" value="module" /></el-select>
        </el-form-item>
        <el-form-item label="目标ID"><el-input v-model="form.target_id" /></el-form-item>
        <el-form-item label="Cron">
          <el-input v-model="form.cron" placeholder="0 */4 * * *" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="create">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getSchedulerTasks, getSchedulerStatus, createSchedulerTask, toggleSchedulerTask, triggerSchedulerTask, deleteSchedulerTask } from '@/api'

const tasks = ref([])
const showCreate = ref(false)
const form = ref({ name: '', target_type: 'module', target_id: '', cron: '' })

const refresh = async () => {
  try { const r = await getSchedulerTasks(); tasks.value = r.tasks || [] }
  catch {}
}

const toggle = async (id) => { await toggleSchedulerTask(id); refresh() }
const trigger = async (id) => { await triggerSchedulerTask(id); refresh() }
const remove = async (id) => { await deleteSchedulerTask(id); refresh() }

const create = async () => {
  await createSchedulerTask(form.value)
  showCreate.value = false; form.value = { name: '', target_type: 'module', target_id: '', cron: '' }
  refresh()
}

onMounted(refresh)
</script>

<style scoped>
.scheduler-page { max-width: 1000px; }
.card-header { display:flex; justify-content:space-between; align-items:center; font-weight:600; }
.page-card { background:#1a1a2e; border:1px solid #2d2d44; border-radius:12px; }
</style>
