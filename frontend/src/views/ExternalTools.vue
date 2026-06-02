<template>
  <div class="tools-page">
    <h2 style="margin:0 0 8px 0;font-size:22px;font-weight:600">🔧 外部工具集成</h2>
    <p style="margin:0 0 20px 0;color:var(--text-muted);font-size:14px">一站式管理所有集成的开源工具平台</p>

    <el-row :gutter="20">
      <el-col :xs="24" :sm="12" :md="8" v-for="t in tools" :key="t.name">
        <el-card :body-style="{ padding: '20px' }" class="tool-card" shadow="hover">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
            <span style="font-size:28px">{{ t.icon }}</span>
            <div>
              <h3 style="margin:0;font-size:16px;font-weight:600">{{ t.name }}</h3>
              <span style="font-size:12px;color:var(--text-dim)">{{ t.status }}</span>
            </div>
          </div>
          <p style="font-size:13px;color:var(--text-muted);line-height:1.6;margin:0 0 12px 0">{{ t.desc }}</p>
          <el-row :gutter="8">
            <el-col :span="12">
              <el-button size="small" @click="openUrl(t.url)" style="width:100%" v-if="t.url" :disabled="t.status==='独立部署'">{{ t.status==='独立部署' ? '需单独部署' : '打开面板' }}</el-button>
            </el-col>
            <el-col :span="12">
              <el-button size="small" @click="checkTool(t)" style="width:100%" :type="t.bridge ? 'primary' : 'info'">{{ t.bridge ? '连接检测' : '查看文档' }}</el-button>
            </el-col>
          </el-row>
          <div v-if="t.checkResult" style="margin-top:10px;padding:8px;border-radius:6px;font-size:12px" :style="{background:t.checkResult.ok?'rgba(16,185,129,0.12)':'rgba(245,158,11,0.12)',color:t.checkResult.ok?'#10b981':'#f59e0b'}">
            {{ t.checkResult.msg }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ChromaDB -->
    <h3 style="margin:24px 0 12px 0;font-size:16px;font-weight:600">📊 ChromaDB 向量数据库</h3>
    <el-card shadow="hover">
      <div v-if="chromaLoading">加载中...</div>
      <div v-else-if="chromaError" style="color:var(--text-dim)">ChromaDB 未安装或未启动</div>
      <div v-else>
        <p>集合数量: <strong>{{ chromaData.count }}</strong></p>
        <el-table :data="chromaData.collections" stripe size="small" style="width:100%" v-if="chromaData.collections.length">
          <el-table-column prop="name" label="集合名称" />
          <el-table-column prop="count" label="文档数" width="120" />
        </el-table>
      </div>
    </el-card>
  </div>
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
        { name:'Gitea', icon:'🐱', status:'Docker 就绪', desc:'自托管 Git 服务 (50k⭐) — 代码托管、PR审查、CI/CD', url:'http://localhost:3000', bridge:'/api/tools/gitea/health', checkResult:null },
        { name:'Nextcloud', icon:'☁️', status:'Docker 就绪', desc:'企业网盘 (30k⭐) — 文件同步/共享/协作', url:'http://localhost:8090', bridge:'/api/tools/nextcloud/health', checkResult:null },
        { name:'Metabase', icon:'📊', status:'Docker 就绪', desc:'BI 分析工具 (45k⭐) — SQL查询/可视化/Dashboard', url:'http://localhost:3030', bridge:'/api/tools/metabase/health', checkResult:null },
        { name:'Plane', icon:'📋', status:'Docker 就绪', desc:'项目管理 (30k⭐) — Issue/Kanban/Sprint (Jira替代)', url:'http://localhost:3780', bridge:'/api/tools/plane/health', checkResult:null },
        { name:'Vaultwarden', icon:'🔐', status:'Docker 就绪', desc:'密码管理器 (40k⭐) — Bitwarden兼容/自托管凭证库', url:'http://localhost:8180', bridge:'/api/tools/vaultwarden/health', checkResult:null },
        { name:'Home Assistant', icon:'🏠', status:'Docker 就绪', desc:'智能家居平台 (80k⭐) — IoT控制/自动化场景/传感器', url:'http://localhost:8123', bridge:'/api/tools/homeassistant/health', checkResult:null },
        { name:'Immich', icon:'📸', status:'Docker 就绪', desc:'照片管理 (55k⭐) — Google Photos替代/AI人脸识别', url:'http://localhost:2283', bridge:'/api/tools/immich/health', checkResult:null },
        { name:'Excalidraw', icon:'✏️', status:'Docker 就绪', desc:'在线白板 (90k⭐) — 架构图/流程图/手绘风格', url:'http://localhost:3080', bridge:'/api/tools/excalidraw/health', checkResult:null },
        { name:'Miniflux', icon:'📡', status:'Docker 就绪', desc:'RSS阅读器 (7k⭐) — 技术博客订阅/内容聚合', url:'http://localhost:3060', bridge:'/api/tools/miniflux/health', checkResult:null },
        { name:'Hoarder', icon:'🔖', status:'Docker 就绪', desc:'书签管理 (3k⭐) — 链接收藏/标签/搜索', url:'http://localhost:3070', bridge:'/api/tools/hoarder/health', checkResult:null },
        { name:'Docmost', icon:'📝', status:'Docker 就绪', desc:'协作Wiki (5k⭐) — 团队文档/知识库', url:'http://localhost:3085', bridge:'/api/tools/docmost/health', checkResult:null },
        { name:'Documenso', icon:'✍️', status:'Docker 就绪', desc:'电子签名 (8k⭐) — DocuSign替代/合同签署', url:'http://localhost:3090', bridge:'/api/tools/documenso/health', checkResult:null },
        { name:'Paperless', icon:'📄', status:'Docker 就绪', desc:'文档管理 (25k⭐) — OCR/分类/归档/搜索', url:'http://localhost:3190', bridge:'/api/tools/paperless/health', checkResult:null },
        { name:'Snipe-IT', icon:'💻', status:'Docker 就绪', desc:'IT资产管理 (10k⭐) — 设备/软件/保修跟踪', url:'http://localhost:3200', bridge:'/api/tools/snipeit/health', checkResult:null },
        { name:'Medusa', icon:'🛒', status:'Docker 就绪', desc:'电商平台 (27k⭐) — Shopify替代/商品/订单/支付', url:'http://localhost:3210', bridge:'/api/tools/medusa/health', checkResult:null },
        { name:'OpenEMR', icon:'🏥', status:'Docker 就绪', desc:'医疗系统 (3k⭐) — 电子病历/预约/处方/账单', url:'http://localhost:3220', bridge:'/api/tools/openemr/health', checkResult:null },
        { name:'ERPNext', icon:'🏭', status:'独立部署', desc:'全业务ERP (25k⭐) — 进销存/财务/制造/CRM, 需单独部署', url:'#', bridge:'', checkResult:null },
        { name:'Frappe HR', icon:'👥', status:'独立部署', desc:'人力资源 (15k⭐) — 员工/考勤/工资/招聘, 需单独部署', url:'#', bridge:'', checkResult:null },
        { name:'Open edX', icon:'🎓', status:'独立部署', desc:'在线学习 (12k⭐) — LMS平台, 需独立部署', url:'#', bridge:'', checkResult:null },
        { name:'Twenty CRM', icon:'🤝', status:'Docker 就绪', desc:'客户管理 (42k⭐) — Salesforce开源替代', url:'http://localhost:3100', bridge:'/api/tools/twenty/health', checkResult:null },
        { name:'Invoice Ninja', icon:'💰', status:'Docker 就绪', desc:'发票/记账 (8k⭐) — 报价/支付/对账', url:'http://localhost:3110', bridge:'/api/tools/invoiceninja/health', checkResult:null },
        { name:'Chatwoot', icon:'💬', status:'Docker 就绪', desc:'客服平台 (22k⭐) — 多渠道客户聊天', url:'http://localhost:3120', bridge:'/api/tools/chatwoot/health', checkResult:null },
        { name:'Jellyfin', icon:'🎬', status:'Docker 就绪', desc:'私人影音 (38k⭐) — Netflix替代/媒体库', url:'http://localhost:3130', bridge:'/api/tools/jellyfin/health', checkResult:null },
        { name:'Calibre-Web', icon:'📚', status:'Docker 就绪', desc:'电子书管理 (12k⭐) — 在线阅读/书架', url:'http://localhost:3140', bridge:'/api/tools/calibreweb/health', checkResult:null },
        { name:'Mattermost', icon:'💬', status:'Docker 就绪', desc:'团队通讯 (30k⭐) — Slack替代/即时消息', url:'http://localhost:3150', bridge:'/api/tools/mattermost/health', checkResult:null },
        { name:'Focalboard', icon:'📋', status:'Docker 就绪', desc:'项目管理 (22k⭐) — Notion替代/看板', url:'http://localhost:3160', bridge:'/api/tools/focalboard/health', checkResult:null },
        { name:'IT-Tools', icon:'🛠️', status:'Docker 就绪', desc:'Dev工具箱 (25k⭐) — 编码/转换/格式化', url:'http://localhost:3170', bridge:'/api/tools/ittools/health', checkResult:null },
        { name:'osTicket', icon:'🎫', status:'Docker 就绪', desc:'客服工单 (3k⭐) — 工单/FAQ/知识库', url:'http://localhost:3180', bridge:'/api/tools/osticket/health', checkResult:null },
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
    async checkAll() {
      const r = await api.get('/api/v1/tools/health', { timeout: 10000 })
      const health = r.data?.tools || {}
      for (const t of this.tools) {
        const h = health[t.name]
        if (h) {
          t.checkResult = h.alive ? { ok: true, msg: `✅ 运行中 (:${h.port})` } : { ok: false, msg: '⚠️ 容器未运行' }
        }
      }
    },
    async checkTool(t) {
      if(!t.bridge) { this.openDoc(t); return }
      try {
        const r = await api.get('/api/v1/tools/health', { timeout: 8000 })
        const health = r.data?.tools?.[t.name] || {}
        if(health.alive) {
          t.checkResult = { ok: true, msg: `✅ 运行中 (端口 :${health.port})` }
        } else {
          t.checkResult = { ok: false, msg: `⚠️ 容器未运行 — 执行: docker compose -f docker-compose.tools.yml up -d` }
        }
      } catch {
        t.checkResult = { ok: false, msg: '⚠️ 状态未知 — 请先启动 API 服务' }
      }
    },
        } else {
          const status = r.data.status || r.data.container || 'ok'
          t.checkResult = { ok: true, msg: `✅ ${status}` }
        }
      } catch(e) {
        t.checkResult = { ok: false, msg: `⚠️ 状态未知 — 需要启动 Docker 容器才能使用` }
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
.tools-page { padding-bottom: 32px; }
.tool-card { border-radius: 12px; transition: transform .2s,margin .2s; margin-bottom:16px; }
.tool-card:hover { transform: translateY(-2px); }
</style>
