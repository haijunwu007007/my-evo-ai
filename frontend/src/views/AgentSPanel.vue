<template>
  <div class="agent-s-panel">
    <el-card shadow="never" class="header-card">
      <div class="header-row">
        <div>
          <h2>Agent-S 桌面自动化</h2>
          <p class="subtitle">Simular Agent-S — GUI Agent 智能操控</p>
        </div>
        <div class="status-tag">
          <el-tag :type="sdkOk ? 'success' : 'danger'" size="small" effect="dark">
            SDK {{ sdkOk ? '就绪' : '未安装' }}
          </el-tag>
          <el-tag v-if="activeTask" type="warning" size="small" effect="dark" style="margin-left:8px">
            任务运行中
          </el-tag>
        </div>
      </div>
    </el-card>

    <div class="grid-2col">
      <!-- 指令执行 -->
      <el-card shadow="never">
        <template #header><span>🎯 执行指令</span></template>
        <el-input v-model="instruction" type="textarea" :rows="3"
          placeholder='例如: "打开记事本并输入 Hello World"' />
        <div class="mt10">
          <el-select v-model="model" size="small" style="width:140px">
            <el-option label="GPT-4o" value="gpt-4o" />
            <el-option label="GPT-4o-mini" value="gpt-4o-mini" />
            <el-option label="Claude-3.5" value="claude-sonnet-4-20250514" />
          </el-select>
          <el-button type="primary" size="small" style="margin-left:8px"
            :loading="running" @click="doExecute" :disabled="!instruction.trim()">
            执行
          </el-button>
          <el-button size="small" @click="clearResult">清除</el-button>
        </div>
        <div v-if="execResult" class="mt10">
          <el-alert :title="execResult.success ? '执行完成' : '执行失败'"
            :type="execResult.success ? 'success' : 'error'" show-icon :closable="false">
            <template #default>
              <p>指令: {{ execResult.instruction }}</p>
              <p v-if="execResult.actions_total !== undefined">
                动作: {{ execResult.actions_success }}/{{ execResult.actions_total }} 成功
                · 耗时: {{ execResult.elapsed_seconds }}s
              </p>
              <pre v-if="execResult.actions" class="result-pre">{{
                JSON.stringify(execResult.actions, null, 2) }}</pre>
            </template>
          </el-alert>
        </div>
      </el-card>

      <!-- 桌面快照 -->
      <el-card shadow="never">
        <template #header><span>📷 桌面快照</span></template>
        <div style="text-align:center">
          <el-button size="small" @click="takeScreenshot" :loading="loadingSS">
            {{ screenshot ? '刷新' : '截取屏幕' }}
          </el-button>
          <el-button size="small" @click="getMousePos">鼠标位置</el-button>
        </div>
        <div v-if="mousePos" class="mt10">
          <el-tag>鼠标: ({{ mousePos.x }}, {{ mousePos.y }})</el-tag>
        </div>
        <div v-if="screenshot" class="mt10 screenshot-box">
          <img :src="'data:image/png;base64,' + screenshot" style="max-width:100%;border-radius:4px" />
        </div>
      </el-card>
    </div>

    <!-- 环境检测 -->
    <el-card shadow="never" class="mt10">
      <template #header><span>🔍 环境检测</span></template>
      <el-button size="small" @click="checkEnv" :loading="checking">检测环境</el-button>
      <div v-if="envChecks" class="mt10">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item v-for="(v,k) in envChecks" :key="k" :label="k">
            <el-tag :type="v ? 'success' : 'danger'" size="small">
              {{ v ? '✓' : '✗' }} {{ String(v) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>

    <!-- 执行历史 -->
    <el-card shadow="never" class="mt10">
      <template #header><span>📜 执行历史</span></template>
      <el-table :data="history" size="small" max-height="300" v-if="history.length">
        <el-table-column prop="instruction" label="指令" min-width="200" show-overflow-tooltip />
        <el-table-column prop="actions_success" label="成功" width="60" />
        <el-table-column prop="actions_total" label="总数" width="60" />
        <el-table-column prop="elapsed_seconds" label="耗时(s)" width="80" />
        <el-table-column prop="timestamp" label="时间" width="160" />
      </el-table>
      <el-empty v-else description="暂无执行记录" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'





const instruction = ref('')
const model = ref('gpt-4o')
const running = ref(false)
const execResult = ref(null)
const screenshot = ref(null)
const loadingSS = ref(false)
const mousePos = ref(null)
const envChecks = ref(null)
const checking = ref(false)
const history = ref([])
const sdkOk = ref(false)
const activeTask = ref(false)

async function doExecute() {
  running.value = true
  execResult.value = null
  try {
    const r = await api.post('/agent-s/execute', { instruction: instruction.value, model: model.value })
    execResult.value = r.data || r
    if (r.data?.success) loadHistory()
  } catch (e) { execResult.value = { success: false, error: String(e) } }
  running.value = false
}

async function takeScreenshot() {
  loadingSS.value = true
  try {
    const r = await api.post('/agent-s/screenshot')
    if (r.data?.success) screenshot.value = r.data.screenshot
  } catch (e) { console.error(e) }
  loadingSS.value = false
}

async function getMousePos() {
  try {
    const r = await api.get('/agent-s/mouse')
    if (r.data?.success) mousePos.value = r.data
  } catch (e) { console.error(e) }
}

async function checkEnv() {
  checking.value = true
  try {
    const r = await api.get('/agent-s/check')
    envChecks.value = r.data?.checks || r.data
  } catch (e) { console.error(e) }
  checking.value = false
}

async function loadHistory() {
  try { const r = await api.get('/agent-s/history?limit=20'); history.value = r.data?.history || [] }
  catch (e) { /* ignore */ }
}

function loadStatus() {
  api.get('/agent-s/status').then(r => {
    // api 拦截器已解包 r.data，r 就是响应 body
    const data = r && r.data ? r.data : r
    sdkOk.value = !!(data.sdk_available ?? data.success)
    activeTask.value = !!(data.active_task ?? data.active)
  }).catch(() => {})
}

function clearResult() { execResult.value = null }

onMounted(() => { loadStatus(); loadHistory() })
</script>

<style scoped>
.agent-s-panel { padding: 16px; max-width: 1100px; margin: 0 auto; }
.header-card { margin-bottom: 16px; }
.header-row { display: flex; justify-content: space-between; align-items: center; }
.subtitle { color: #909399; font-size: 13px; margin: 0; }
.grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.mt10 { margin-top: 10px; }
.result-pre { background: #f5f7fa; padding: 8px; border-radius: 4px; font-size: 12px; max-height: 200px; overflow: auto; white-space: pre-wrap; }
.screenshot-box { text-align: center; }
@media (max-width: 768px) { .grid-2col { grid-template-columns: 1fr; } }
</style>
