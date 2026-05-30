<template>
  <div class="notify-page">
    <div v-if="loading" style="display:flex;gap:16px;margin-bottom:16px">
      <el-skeleton-item variant="rect" style="width:25%;height:80px;border-radius:12px" v-for="n in 4" :key="n" />
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
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="never" class="page-card">
          <template #header><div class="card-header"><span>📨 发送历史</span><el-button size="small" @click="load">刷新</el-button></div></template>
          <el-table :data="history" stripe size="small" max-height="360">
            <el-table-column prop="channel" label="渠道" width="90">
              <template #default="{row}"><el-tag size="small">{{ row.channel }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="70" />
            <el-table-column label="状态" width="70">
              <template #default="{row}"><el-tag :type="row.success?'success':'danger'" size="small">{{ row.success?'成功':'失败' }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="message" label="摘要" min-width="120" />
            <el-table-column label="时间" width="140"><template #default="{row}">{{ new Date(row.timestamp).toLocaleString() }}</template></el-table-column>
          </el-table>
          <el-empty v-if="!history.length && !loading" description="暂无发送记录" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="page-card">
          <template #header><div class="card-header"><span>🔔 测试通知</span></div></template>
          <el-form label-width="80px">
            <el-form-item label="渠道">
              <el-select v-model="testChannel" style="width:100%">
                <el-option label="企业微信" value="wecom" />
                <el-option label="钉钉" value="dingtalk" />
                <el-option label="飞书" value="feishu" />
                <el-option label="Server酱" value="serverchan" />
                <el-option label="PushPlus" value="pushplus" />
                <el-option label="邮箱" value="email" />
                <el-option label="Bark" value="bark" />
              </el-select>
            </el-form-item>
            <el-form-item label="内容"><el-input v-model="testMsg" type="textarea" :rows="2" placeholder="测试消息内容" /></el-form-item>
            <el-form-item><el-button type="primary" @click="sendTest" :loading="sending">发送测试</el-button><span v-if="testResult" :style="{color:testResult.success?'#10b981':'#ef4444',marginLeft:12}">{{ testResult.success?'✅ 发送成功':'❌ '+testResult.message }}</span></el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import { notifyStatus, notifyConfig, notifyUpdateConfig, notifySend } from '@/api'
const loading = ref(true); const sending = ref(false); const testResult = ref<any>(null)
const stats = ref([{key:'total',label:'总发送',val:0,color:'#6366f1'},{key:'success',label:'成功',val:0,color:'#10b981'},{key:'fail',label:'失败',val:0,color:'#ef4444'},{key:'channels',label:'渠道数',val:0,color:'#f59e0b'}])
const history = ref([]) as any
const testChannel = ref('wecom'); const testMsg = ref('这是一条来自AUTO-EVO-AI的测试通知')
const config = ref({}) as any
const load = async () => {
  loading.value = true
  try {
    const [st, h] = await Promise.all([
      api.get('/notify/stats'),
      api.get('/notify/history', { params: { limit: 30 } })
    ])
    stats.value[0].val = st.total||0; stats.value[1].val = st.success||0
    stats.value[2].val = st.failed||0; stats.value[3].val = st.channels?.length||0
    history.value = h.history||[]
  } catch {} finally { loading.value = false }
}
const sendTest = async () => {
  sending.value = true; testResult.value = null
  try {
    const r = await notifyTest(testChannel.value, { content: testMsg.value })
    testResult.value = r
  } catch(e:any) { testResult.value = { success: false, message: e.message } }
  finally { sending.value = false }
}
import api from '@/api'
onMounted(load)
</script>
<style scoped>
.notify-page{max-width:1200px;padding-bottom:32px}
.stat-card{background:var(--bg-card);border:1px solid var(--border-subtle);border-radius:12px;text-align:center;padding:16px}
.stat-val{font-size:28px;font-weight:700;line-height:1.2}
.stat-lbl{font-size:12px;color:var(--text-muted);margin-top:4px}
.page-card{background:var(--bg-card);border:1px solid var(--border-subtle);border-radius:12px}
.card-header{display:flex;justify-content:space-between;align-items:center;font-weight:600}
</style>
