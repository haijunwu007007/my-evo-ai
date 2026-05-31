<template>
  <div class="settings-page">
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card shadow="never" class="page-card">
          <template #header><div class="card-header"><span>⚙️ 系统配置</span><el-button size="small" @click="reload">重新加载</el-button></div></template>
          <el-table :data="configs" stripe v-if="configs.length" :empty-text="'暂无配置'">
            <el-table-column prop="key" label="Key" min-width="200" />
            <el-table-column prop="value" label="Value" min-width="200">
              <template #default="{row}"><span style="word-break:break-all;font-size:12px;color:#a0aec0">{{ row.value }}</span></template>
            </el-table-column>
            <el-table-column label="操作" width="60">
              <template #default="{row}"><el-popconfirm title="删除？" @confirm="del(row.key)"><template #reference><el-button text type="danger" size="small">删</el-button></template></el-popconfirm></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never" class="page-card">
          <template #header><div class="card-header">📊 统计</div></template>
          <div class="info-row" v-for="(v,k) in statInfo" :key="k"><span class="info-key">{{k}}</span><span class="info-val">{{v}}</span></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getConfigEntries, deleteConfig, reloadConfig, getSystemMetrics, getDiagnosis } from '@/api'
const entries = ref<any[]>([])
const configs = computed(() => entries.value)
const statInfo = ref<Record<string, any>>({})
const load = async () => {
  try {
    const [ce, m, d] = await Promise.all([getConfigEntries(), getSystemMetrics(), getDiagnosis()])
    entries.value = ce.entries||[]
    statInfo.value = { '运行时间': d.uptime_human||'-', '请求数': m.requests||0, '错误数': m.errors||0, '缓存命中': m.cache_hits||0 }
  } catch {}
}
const del = async (key: string) => { await deleteConfig(key); load() }
const reload = async () => { await reloadConfig(); load(); ElMessage.success('配置已重新加载') }
onMounted(load)
</script>
<style scoped>
.settings-page{max-width:1000px}
.page-card{background:#1a1a2e;border:1px solid #2d2d44;border-radius:12px}
.card-header{display:flex;justify-content:space-between;align-items:center;font-weight:600}
.info-row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #2d2d44;font-size:13px}
.info-key{color:#a0aec0};.info-val{color:#e2e8f0;font-weight:500}
</style>
