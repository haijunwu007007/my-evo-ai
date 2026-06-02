<template>
  <div class="external-tools">
    <el-card shadow="never" class="header-card">
      <h2>🛠️ 外部工具</h2>
      <p class="subtitle">自动检测可用的工具，点击即可使用</p>
      <el-button size="small" @click="refreshHealth" :loading="loading" type="primary" plain>
        刷新状态
      </el-button>
    </el-card>

    <el-empty v-if="!loading && runningTools.length === 0" description="暂无可用工具，请启动 Docker 容器" />

    <div class="tool-grid">
      <div v-for="tool in runningTools" :key="tool.name" class="tool-card">
        <div class="tool-header">
          <span class="tool-icon">{{ tool.icon }}</span>
          <span class="tool-name">{{ tool.name }}</span>
          <el-tag size="small" type="success" effect="dark">✅ 可用</el-tag>
        </div>
        <p class="tool-desc">{{ tool.desc }}</p>
        <a :href="tool.url" target="_blank" class="tool-btn">
          <el-button type="primary" size="small" style="width:100%">
            🔗 打开 {{ tool.name }}
          </el-button>
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '@/api'

const loading = ref(false)
const healthData = ref({})
const runningTools = ref([])

const allTools = [
  { name:'Gitea', icon:'🐱', desc:'代码仓库 — 托管/PR/CI', url:'http://localhost:3000' },
  { name:'Nextcloud', icon:'☁️', desc:'企业网盘 — 文件同步/共享', url:'http://localhost:8090' },
  { name:'Metabase', icon:'📊', desc:'数据分析 — SQL/可视化', url:'http://localhost:3030' },
  { name:'Vaultwarden', icon:'🔐', desc:'密码管理器', url:'http://localhost:8180' },
  { name:'Home Assistant', icon:'🏠', desc:'智能家居控制', url:'http://localhost:8123' },
  { name:'Excalidraw', icon:'✏️', desc:'在线白板/画图', url:'http://localhost:3080' },
  { name:'Miniflux', icon:'📡', desc:'RSS阅读器', url:'http://localhost:3060' },
  { name:'Immich', icon:'📸', desc:'照片管理 (Google Photos替代)', url:'http://localhost:2283' },
  { name:'Jellyfin', icon:'🎬', desc:'私人影音库', url:'http://localhost:3130' },
  { name:'Calibre-Web', icon:'📚', desc:'电子书管理', url:'http://localhost:3140' },
  { name:'Twenty CRM', icon:'🏢', desc:'客户管理 (Salesforce替代)', url:'http://localhost:3100' },
  { name:'Invoice Ninja', icon:'💰', desc:'发票/记账/报价', url:'http://localhost:3110' },
  { name:'Chatwoot', icon:'💬', desc:'客服聊天平台', url:'http://localhost:3120' },
  { name:'osTicket', icon:'🎫', desc:'客服工单系统', url:'http://localhost:3180' },
  { name:'Mattermost', icon:'👥', desc:'团队通讯 (Slack替代)', url:'http://localhost:3150' },
  { name:'Focalboard', icon:'📋', desc:'项目看板 (Notion替代)', url:'http://localhost:3160' },
  { name:'IT-Tools', icon:'🛠', desc:'开发者工具箱', url:'http://localhost:3170' },
  { name:'Hoarder', icon:'🔖', desc:'书签/链接管理', url:'http://localhost:3070' },
  { name:'Docmost', icon:'📝', desc:'协作Wiki/文档', url:'http://localhost:3085' },
  { name:'Documenso', icon:'✍️', desc:'电子签名', url:'http://localhost:3090' },
  { name:'Paperless', icon:'📄', desc:'文档OCR/归档', url:'http://localhost:3190' },
  { name:'Snipe-IT', icon:'💻', desc:'IT资产管理', url:'http://localhost:3200' },
  { name:'Dify', icon:'🤖', desc:'AI应用编排', url:'http://localhost:8002' },
  { name:'Flowise', icon:'🌊', desc:'低代码LLM流程', url:'http://localhost:8001' },
  { name:'n8n', icon:'🔄', desc:'自动化工作流', url:'http://localhost:8000' },
  { name:'Meilisearch', icon:'🔍', desc:'搜索引擎', url:'http://localhost:7700' },
  { name:'Uptime-Kuma', icon:'📈', desc:'服务监控', url:'http://localhost:3001' },
  { name:'MinIO', icon:'📦', desc:'对象存储', url:'http://localhost:9000' },
]

async function refreshHealth() {
  loading.value = true
  try {
    const r = await api.get('/v1/tools/health')
    healthData.value = r.tools || {}
  } catch { healthData.value = {} }
  filterRunning()
  loading.value = false
}

function filterRunning() {
  runningTools.value = allTools.filter(t => {
    const h = healthData.value[t.name]
    return h && h.alive === true
  })
}

onMounted(() => refreshHealth())
</script>

<style scoped>
.external-tools { padding: 16px; max-width: 1200px; margin: 0 auto; }
.header-card { margin-bottom: 16px; }
.subtitle { color: #909399; font-size: 13px; margin: 4px 0 12px 0; }
.tool-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.tool-card {
  background: var(--el-bg-color); border: 1px solid var(--el-border-color-light);
  border-radius: 8px; padding: 16px; transition: all 0.2s;
}
.tool-card:hover { border-color: var(--el-color-primary); transform: translateY(-2px); }
.tool-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.tool-icon { font-size: 24px; }
.tool-name { font-weight: 600; flex: 1; }
.tool-desc { font-size: 13px; color: #909399; margin-bottom: 12px; }
.tool-btn { text-decoration: none; }
</style>
