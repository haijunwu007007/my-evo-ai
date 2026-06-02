<template>
  <div class="plugins-page">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2 style="margin:0">🧩 插件管理</h2>
      <div style="display:flex;gap:8px">
        <el-button size="small" @click="scan" :loading="scanning">扫描新插件</el-button>
        <el-button size="small" @click="loadMarket" type="primary">插件市场</el-button>
      </div>
    </div>

    <el-tabs v-model="tab">
      <el-tab-pane label="已安装" name="installed">
        <el-table :data="plugins" stripe size="small" v-if="plugins.length">
          <el-table-column prop="name" label="名称" min-width="140" />
          <el-table-column prop="version" label="版本" width="80" />
          <el-table-column label="状态" width="100">
            <template #default="{row}">
              <el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '已启用' : '已停用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="hooks" label="Hook 数" width="80">
            <template #default="{row}">{{ row.hooks?.length || 0 }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="{row}">
              <el-button size="small" :type="row.enabled ? 'warning' : 'success'" @click="toggle(row)">{{ row.enabled ? '停用' : '启用' }}</el-button>
              <el-button size="small" type="danger" plain @click="uninstall(row)">卸载</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无已安装插件" />
      </el-tab-pane>

      <el-tab-pane label="插件市场" name="market">
        <el-table :data="marketItems" stripe size="small" v-if="marketItems.length">
          <el-table-column prop="name" label="名称" min-width="140" />
          <el-table-column prop="desc" label="说明" min-width="200" />
          <el-table-column prop="version" label="版本" width="80" />
          <el-table-column prop="author" label="作者" width="100" />
          <el-table-column label="操作" width="120">
            <template #default="{row}">
              <el-button size="small" type="primary" @click="install(row)" :loading="installing === row.id">安装</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无可用插件" />
      </el-tab-pane>

      <el-tab-pane label="Hook 列表" name="hooks">
        <el-table :data="hooksList" stripe size="small" v-if="hooksList.length">
          <el-table-column prop="name" label="Hook" width="160" />
          <el-table-column prop="description" label="说明" min-width="200" />
          <el-table-column prop="priority" label="优先级" width="80" />
          <el-table-column label="已注册" min-width="200">
            <template #default="{row}">
              <el-tag v-for="p in row.plugins" :key="p.id" size="small" style="margin:2px">{{ p.name }}</el-tag>
              <span v-if="!row.plugins?.length" style="color:#999">无</span>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无 Hook 数据" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const tab = ref('installed')
const plugins = ref<any[]>([])
const marketItems = ref<any[]>([])
const hooksList = ref<any[]>([])
const scanning = ref(false)
const installing = ref('')

async function load() {
  try {
    const r = await api.get('/plugins')
    plugins.value = r.plugins || []
  } catch {}
}
async function loadMarket() {
  try {
    const r = await api.get('/plugins/market/available')
    marketItems.value = r.plugins || []
    tab.value = 'market'
  } catch { ElMessage.error('加载市场失败') }
}
async function scan() {
  scanning.value = true
  try {
    const r = await api.post('/plugins/scan')
    ElMessage.success(`发现 ${r.discovered} 个新插件，共 ${r.total} 个`)
    await load()
  } catch { ElMessage.error('扫描失败') }
  scanning.value = false
}
async function toggle(row: any) {
  try {
    const act = row.enabled ? 'disable' : 'enable'
    await api.post(`/plugins/${row.id}/${act}`)
    row.enabled = !row.enabled
    ElMessage.success(row.enabled ? '已启用' : '已停用')
  } catch { ElMessage.error('操作失败') }
}
async function uninstall(row: any) {
  try {
    await ElMessageBox.confirm(`确定卸载插件「${row.name}」？`)
    await api.post(`/plugins/${row.id}/uninstall`)
    plugins.value = plugins.value.filter((p: any) => p.id !== row.id)
    ElMessage.success('已卸载')
  } catch {}
}
async function install(row: any) {
  installing.value = row.id
  try {
    await api.post('/plugins/install', { plugin_id: row.id })
    ElMessage.success('安装成功')
    await load()
  } catch { ElMessage.error('安装失败') }
  installing.value = ''
}
async function loadHooks() {
  try {
    const r = await api.get('/plugins/hooks')
    hooksList.value = Object.entries(r.hooks || {}).map(([k, v]: any) => ({ name: k, ...v }))
  } catch {}
}
onMounted(() => { load(); loadHooks() })
</script>
<style scoped>
.plugins-page { padding-bottom: 32px; }
</style>
