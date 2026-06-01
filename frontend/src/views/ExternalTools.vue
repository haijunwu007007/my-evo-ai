<template>
  <el-main class="tools-page" style="padding:20px;background:#f5f7fa;min-height:100vh">
    <h2 style="margin:0 0 8px 0;font-size:22px;font-weight:600;color:#1a1a2e">🔧 外部工具集成</h2>
    <p style="margin:0 0 20px 0;color:#666;font-size:14px">一站式管理所有集成的开源工具平台</p>

    <el-row :gutter="20">
      <el-col :span="8" v-for="t in tools" :key="t.name">
        <el-card :body-style="{ padding: '20px' }" class="tool-card" shadow="hover">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
            <span style="font-size:28px">{{ t.icon }}</span>
            <div>
              <h3 style="margin:0;font-size:16px;font-weight:600">{{ t.name }}</h3>
              <span style="font-size:12px;color:#999">{{ t.status }}</span>
            </div>
          </div>
          <p style="font-size:13px;color:#555;line-height:1.6;margin:0 0 12px 0">{{ t.desc }}</p>
          <el-row :gutter="8">
            <el-col :span="12">
              <el-button size="small" @click="openUrl(t.url)" style="width:100%" v-if="t.url">打开面板</el-button>
            </el-col>
            <el-col :span="12">
              <el-button size="small" :type="t.bridge ? 'primary' : 'info'" @click="checkTool(t)" style="width:100%">{{ t.bridge ? '连接检测' : '查看文档' }}</el-button>
            </el-col>
          </el-row>
          <div v-if="t.checkResult" style="margin-top:10px;padding:8px;border-radius:6px;font-size:12px" :style="{background:t.checkResult.ok?'#e8f5e9':'#fff3e0',color:t.checkResult.ok?'#2e7d32':'#e65100'}">
            {{ t.checkResult.msg }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ChromaDB -->
    <h3 style="margin:24px 0 12px 0;font-size:16px;font-weight:600;color:#1a1a2e">📊 ChromaDB 向量数据库</h3>
    <el-card shadow="hover">
      <div v-if="chromaLoading">加载中...</div>
      <div v-else-if="chromaError" style="color:#999">ChromaDB 未安装或未启动</div>
      <div v-else>
        <p>集合数量: <strong>{{ chromaData.count }}</strong></p>
        <el-table :data="chromaData.collections" stripe size="small" style="width:100%" v-if="chromaData.collections.length">
          <el-table-column prop="name" label="集合名称" />
          <el-table-column prop="count" label="文档数" width="120" />
        </el-table>
      </div>
    </el-card>
  </el-main>
</template>

<script>
import axios from 'axios'
const api = axios.create({baseURL: ''})

export default {
  name: 'ExternalTools',
  data() {
    return {
      tools: [
        { name:'Dify', icon:'🤖', status:'模块已安装', desc:'可视化 LLM 应用构建平台 — RAG 知识库、Agent 工作流、对话机器人', url:'http://localhost:3000', bridge:'/api/tools/dify', checkResult:null },
        { name:'Flowise', icon:'🔀', status:'模块已安装', desc:'低代码 LLM 工作流编排 — 拖拽式构建 AI 管道、知识库检索链', url:'http://localhost:5678', bridge:null, checkResult:null },
        { name:'n8n', icon:'⚡', status:'模块已安装', desc:'高级工作流自动化平台 — 300+ 集成、可视化编排、定时任务触发', url:'http://localhost:5678', bridge:null, checkResult:null },
        { name:'One-API', icon:'🌐', status:'Docker 就绪', desc:'统一 LLM API 网关 — 管理 20+ 模型提供商、密钥配额、用量统计', url:'http://localhost:3001', bridge:null, checkResult:null },
        { name:'LiteLLM', icon:'🧠', status:'模块已安装', desc:'轻量级 AI 网关 — 100+ 模型统一接口、自动故障切换、成本追踪', url:'http://localhost:4000', bridge:'/api/litellm/health', checkResult:null },
        { name:'Agent-S', icon:'🖥️', status:'模块已安装', desc:'GUI 自动化智能体 — AI 控制桌面、执行操作、屏幕理解', url:'/agent-s', bridge:'/api/agent-s/status', checkResult:null },
        { name:'Meilisearch', icon:'🔍', status:'Docker 就绪', desc:'毫秒级全文搜索引擎 — 模块/文档/日志即时搜索，容错拼写', url:'http://localhost:7700', bridge:'/api/tools/meili', checkResult:null },
        { name:'Stirling-PDF', icon:'📄', status:'Docker 就绪', desc:'开源 PDF 工具箱 — 合并/拆分/压缩/OCR/签名 60+ 操作', url:'http://localhost:8081', bridge:'/api/tools/pdf', checkResult:null },
        { name:'Uptime-Kuma', icon:'📡', status:'Docker 就绪', desc:'自托管服务监控 — 实时状态、告警通知、SSL 证书检查', url:'http://localhost:3001', bridge:'/api/tools/uptime', checkResult:null },
        { name:'NextChat', icon:'💬', status:'Docker 就绪', desc:'跨平台 ChatGPT UI — 多模型聊天、Prompt 管理、插件系统', url:'http://localhost:3099', bridge:'/api/tools/nextchat', checkResult:null },
        { name:'Browser-Use', icon:'🌐', status:'SDK已安装 v0.12.6', desc:'AI 浏览器自动化 (93k⭐) — Agent 像人类一样操作网页', url:'', bridge:'/api/tools/browser-use', checkResult:null },
        { name:'FileBrowser', icon:'📁', status:'Docker 就绪', desc:'Web 文件管理器 (55k⭐) — 浏览器中管理服务器文件', url:'http://localhost:8083', bridge:'/api/tools/filebrowser', checkResult:null },
        { name:'OpenClaw', icon:'🦞', status:'Docker 就绪', desc:'AI 个人助手网关 (373k⭐) — 连接 Telegram/Discord/WhatsApp 50+平台', url:'http://localhost:3002', bridge:'/api/tools/openclaw', checkResult:null },
        { name:'Langfuse', icon:'🔍', status:'SDK已安装 v4.7.1', desc:'LLM 可观测性 (14k⭐) — 追踪 AI 调用耗时、Token 成本、质量对比', url:'https://cloud.langfuse.com', bridge:'/api/tools/langfuse/health', checkResult:null },
        { name:'Superset', icon:'📊', status:'Docker 就绪', desc:'数据可视化平台 (65k⭐) — 拖拽式 Dashboard、SQL 查询、实时图表', url:'http://localhost:8088', bridge:'/api/tools/superset/health', checkResult:null },
        { name:'ActivePieces', icon:'🧩', status:'Docker 就绪', desc:'开源工作流引擎 (12k⭐) — TypeScript 原生、200+ 集成、AI 管道', url:'http://localhost:8080', bridge:'/api/tools/activepieces/health', checkResult:null },
        { name:'Hoppscotch', icon:'🔗', status:'Docker 就绪', desc:'开源 API 测试工具 (66k⭐) — Postman 替代品，HTTP/GraphQL/WebSocket', url:'http://localhost:3010', bridge:'/api/tools/hoppscotch/health', checkResult:null },
        { name:'Tabby', icon:'✏️', status:'Docker 就绪', desc:'自托管 AI 代码助手 (30k⭐) — 代码补全、内联建议、多模型', url:'http://localhost:8089', bridge:'/api/tools/tabby/health', checkResult:null },
        { name:'Firecrawl', icon:'🕷️', status:'Docker 就绪', desc:'AI 网页爬虫 (30k⭐) — 为 RAG 知识库抓取网页数据', url:'http://localhost:3002', bridge:'/api/tools/firecrawl/health', checkResult:null },
        { name:'MCP Hub', icon:'🔌', status:'内置就绪', desc:'MCP 协议网关 (内置) — AI Agent 统一调用外部工具', url:'', bridge:'/api/tools/mcp/health', checkResult:null },
        { name:'MinIO', icon:'💾', status:'Docker 就绪', desc:'S3 对象存储 (55k⭐) — 高性能文件存储，备份/上传/模型存储', url:'http://localhost:9001', bridge:'/api/tools/minio/health', checkResult:null },
        { name:'Portainer', icon:'🐳', status:'Docker 就绪', desc:'Docker 管理面板 (32k⭐) — Web UI 管理容器/镜像/网络/卷', url:'https://localhost:9443', bridge:'/api/tools/portainer/health', checkResult:null },
        { name:'Grafana', icon:'📈', status:'Docker 就绪', desc:'开源监控仪表盘 (70k⭐) — Prometheus 数据可视化、告警', url:'http://localhost:3050', bridge:'/api/tools/grafana/health', checkResult:null },
        { name:'Outline', icon:'📝', status:'Docker 就绪', desc:'知识库文档系统 (30k⭐) — 团队文档、项目说明、API 文档', url:'http://localhost:3100', bridge:'/api/tools/outline/health', checkResult:null },
        { name:'Appsmith', icon:'🛠️', status:'Docker 就绪', desc:'低代码内部工具 (35k⭐) — 拖拽构建管理面板、Dashboard', url:'http://localhost:8080', bridge:'/api/tools/appsmith/health', checkResult:null },

        { name:'Code-Server', icon:'💻', status:'Docker 就绪', desc:'Web IDE (70k⭐) — 浏览器里写代码', url:'http://localhost:8443', bridge:'/api/tools/code-server/health', checkResult:null },
        { name:'Dashy', icon:'🏠', status:'Docker 就绪', desc:'统一启动页 (17k⭐) — 30 个工具一站式入口', url:'http://localhost:4000', bridge:'/api/tools/dashy/health', checkResult:null },
        { name:'Ntfy', icon:'🔔', status:'Docker 就绪', desc:'推送通知 (30k⭐) — 手机/桌面推送', url:'http://localhost:8086', bridge:'/api/tools/ntfy/health', checkResult:null },
        { name:'NocoDB', icon:'🗄️', status:'Docker 就绪', desc:'数据库管理 (55k⭐) — SQLite 转电子表格', url:'http://localhost:8088', bridge:'/api/tools/nocodb/health', checkResult:null },
        { name:'Changedetection', icon:'👁️', status:'Docker 就绪', desc:'网页变更监控 (20k⭐) — 监控文档/竞品更新', url:'http://localhost:5000', bridge:'/api/tools/changedetection/health', checkResult:null },
      ],
      chromaData: { count:0, collections:[] },
      chromaLoading: true, chromaError: false
    }
  },
  async mounted() {
    try {
      const r = await api.get('/api/tools/chroma')
      if(r.data.available) {
        const r2 = await api.get('/api/tools/chroma/collections')
        this.chromaData = { count: r.data.count, collections: r2.data.collections || [] }
      } else { this.chromaError = true }
    } catch { this.chromaError = true }
    this.chromaLoading = false
  },
  methods: {
    openUrl(url) { window.open(url, '_blank') },
    async checkTool(t) {
      if(!t.bridge) { this.openDoc(t); return }
      try {
        const r = await api.get(t.bridge, { timeout: 5000 })
        t.checkResult = { ok: true, msg: `✅ 连接正常 — ${JSON.stringify(r.data).slice(0,80)}` }
      } catch(e) {
        t.checkResult = { ok: false, msg: `❌ 连接失败 — ${e.message}` }
      }
    },
    openDoc(t) {
      const docs = { Dify:'https://docs.dify.ai', Flowise:'https://docs.flowiseai.com', 'n8n':'https://docs.n8n.io', 'One-API':'https://github.com/songquanpeng/one-api', Meilisearch:'https://www.meilisearch.com/docs', 'Stirling-PDF':'https://github.com/Stirling-Tools/Stirling-PDF', 'Uptime-Kuma':'https://github.com/louislam/uptime-kuma', NextChat:'https://github.com/ChatGPTNextWeb/NextChat', 'Browser-Use':'https://github.com/browser-use/browser-use', FileBrowser:'https://github.com/filebrowser/filebrowser', OpenClaw:'https://github.com/openclaw/openclaw', Langfuse:'https://langfuse.com/docs', Superset:'https://superset.apache.org/docs', ActivePieces:'https://www.activepieces.com/docs', Hoppscotch:'https://github.com/hoppscotch/hoppscotch', Tabby:'https://tabby.tabbyml.com/docs', Firecrawl:'https://docs.firecrawl.dev', 'MCP Hub':'https://github.com/apappascs/mcp-servers-hub', MinIO:'https://min.io/docs', Portainer:'https://docs.portainer.io', Grafana:'https://grafana.com/docs', Outline:'https://docs.outline.com', Appsmith:'https://docs.appsmith.com' }
      window.open(docs[t.name] || '#', '_blank')
    }
  }
}
</script>

<style scoped>
.tool-card { border-radius: 12px; transition: transform .2s,margin .2s; margin-bottom:16px; }
.tool-card:hover { transform: translateY(-2px); }
</style>
