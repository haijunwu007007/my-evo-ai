<template>
  <div class="coordinator-page">
    <el-card shadow="never" class="page-card">
      <template #header>
        <div class="card-header">
          <span>🧠 AI 编排执行</span>
          <el-tag type="success" v-if="status?.success">运行中</el-tag>
        </div>
      </template>

      <div style="display:flex;gap:8px;align-items:flex-start;margin-bottom:12px">
        <el-input
          v-model="taskDesc"
          type="textarea"
          :rows="3"
          placeholder="用自然语言描述任务…"
          style="flex:1"
        />
        <span class="mic-btn" @click="startVoice('taskDesc')" title="语音输入" style="cursor:pointer;font-size:20px;padding:4px;margin-top:2px">🎤</span>
      </div>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-button type="primary" :loading="loading" @click="execute" style="width:100%">
            {{ loading ? '执行中…' : '🚀 执行' }}
          </el-button>
        </el-col>
        <el-col :span="12">
          <el-select v-model="templateId" placeholder="选择模板" style="width:100%" @change="applyTpl">
            <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-col>
      </el-row>

      <div v-if="result" class="result-box">
        <div class="result-title">执行结果</div>
        <pre>{{ JSON.stringify(result, null, 2) }}</pre>
      </div>
    </el-card>

    <el-card shadow="never" class="page-card" style="margin-top:16px">
      <template #header>
        <div class="card-header">
          <span>🔧 可用能力</span>
        </div>
      </template>
      <div v-if="capabilities" class="cap-grid">
        <div v-for="(items, group) in capabilities" :key="group" class="cap-group">
          <div class="cap-group-title">{{ group }}</div>
          <el-tag v-for="item in items" :key="item" size="small" style="margin:4px">{{ item }}</el-tag>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getCoordinatorStatus, getCoordinatorCapabilities, executeTask, getTemplates, applyTemplate } from '@/api'

const taskDesc = ref('')
const loading = ref(false)
const result = ref<any>(null)
const status = ref<any>(null)
const capabilities = ref<any>(null)
const templates = ref<any[]>([])
const templateId = ref('')

let voiceRec: any = null
function startVoice(field: string) {
  const SR = window.SpeechRecognition || (window as any).webkitSpeechRecognition
  if (!SR) { alert('浏览器不支持语音输入'); return }
  if (voiceRec) { voiceRec.abort(); voiceRec = null; return }
  const r = new SR()
  r.lang = 'zh-CN'; r.continuous = false; r.interimResults = false
  r.onresult = (e: any) => { const t = e.results[0][0].transcript; if (field === 'taskDesc') taskDesc.value = t; voiceRec = null }
  r.onerror = () => { voiceRec = null }; r.onend = () => { voiceRec = null }
  try { r.start(); voiceRec = r } catch {}
}

const execute = async () => {
  if (!taskDesc.value.trim()) return
  loading.value = true; result.value = null
  try { result.value = await executeTask(taskDesc.value) }
  catch (e: any) { result.value = { error: e.message } }
  loading.value = false
}

const applyTpl = async (id: string) => {
  try {
    const res = await applyTemplate(id)
    result.value = { success: true, message: `模板已应用`, task: res.task?.name }
  } catch (e: any) {
    result.value = { error: e.message }
  }
}

onMounted(async () => {
  try {
    const [s, c, t] = await Promise.all([
      getCoordinatorStatus(), getCoordinatorCapabilities(), getTemplates(),
    ])
    status.value = s; templates.value = t.templates || []
    capabilities.value = s.capabilities || c.capabilities || {}
  } catch {}
})
</script>

<style scoped>
.coordinator-page { max-width: 800px; }
.card-header { display:flex; justify-content:space-between; align-items:center; font-weight:600; }
.page-card { background:#1a1a2e; border:1px solid #2d2d44; border-radius:12px; }
.result-box { margin-top:16px; background:#0f0f1a; border-radius:8px; padding:16px; max-height:400px; overflow:auto; }
.result-title { font-size:13px; font-weight:600; color:#e2e8f0; margin-bottom:8px; }
.result-box pre { font-size:12px; color:#a0aec0; white-space:pre-wrap; }
.cap-grid { display:flex; flex-direction:column; gap:12px; }
.cap-group-title { font-size:13px; font-weight:600; color:#6366f1; margin-bottom:4px; text-transform:capitalize; }
</style>
