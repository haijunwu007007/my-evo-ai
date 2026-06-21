<template>
  <div id="app-root" :class="theme">
    <header class="app-header">
      <div class="hdr-left">
        <span class="logo">⚡ AUTO-EVO-AI</span>
        <span class="model-badge">{{ currentModel }}</span>
      </div>
      <div class="hdr-right">
        <button @click="toggleTheme" class="hdr-btn" v-html="theme === 'dark' ? '&#127769;' : '&#127774;'"></button>
        <button @click="newChat" class="hdr-btn">🔄 新对话</button>
        <button @click="showHistory = !showHistory" class="hdr-btn">📋 历史</button>
        <button @click="logout" class="hdr-btn">🔓 退出</button>
      </div>
    </header>
    <nav class="app-nav">
      <router-link v-for="t in topTabs" :key="t.path" :to="t.path" class="nav-tab">{{ t.label }}</router-link>
    </nav>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script>
export default {
  data() {
    return {
      theme: localStorage.getItem('evo-theme') || 'light',
      currentModel: 'GLM-4-Flash',
      showHistory: false,
      topTabs: [
        { path: '/', label: '💬 对话' },
        { path: '/dashboard', label: '📊 仪表盘' },
        { path: '/chat', label: '🪐 开源中心' },
        { path: '/automations', label: '🤖 自动化' },
        { path: '/company', label: '📊 虚拟公司' },
        { path: '/admin', label: '🏢 企业管理' },
        { path: '/canvas', label: '🎨 编排画布' },
        { path: '/n8n', label: '📝 工作流' },
        { path: '/capabilities', label: '🧠 能力中心' },
        { path: '/deploy', label: '🚀 一键部署' },
        { path: '/video', label: '🎬 视频生成' },
        { path: '/agents', label: '🤖 智能体' },
      ]
    }
  },
  methods: {
    toggleTheme() {
      this.theme = this.theme === 'dark' ? 'light' : 'dark'
      localStorage.setItem('evo-theme', this.theme)
    },
    newChat() { this.$router.push('/') },
    logout() { localStorage.removeItem('evo_user'); this.$router.push('/login') }
  }
}
</script>

<style>
:root{--bg:#eef0f6;--bg2:#f8f9fc;--card:#fff;--text:#1a1a2e;--text2:#6c757d;--input-bg:#fff;--accent:#4361ee;--accent2:#7209b7;--user-msg:#4361ee;--ai-msg:#e8ecf4;--border:#d0d5e0;--glass:rgba(255,255,255,.7);--glow:rgba(67,97,238,.2)}
#app-root.dark{--bg:#0b0b16;--bg2:#12122a;--card:#1a1a3e;--text:#e0e6f0;--text2:#8892b0;--input-bg:#12122a;--accent:#4361ee;--accent2:#7209b7;--user-msg:#4361ee;--ai-msg:#1a1a3e;--border:#2a2a5a;--glass:rgba(255,255,255,.04);--glow:rgba(67,97,238,.3)}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;min-height:100vh}
.app-header{display:flex;align-items:center;justify-content:space-between;padding:8px 16px;background:var(--bg);border-bottom:1px solid var(--border)}
.hdr-left,.hdr-right{display:flex;align-items:center;gap:8px}
.logo{font-weight:700;font-size:14px;color:var(--accent)}
.model-badge{background:var(--glass);padding:2px 10px;border-radius:10px;font-size:11px;color:var(--text2);border:1px solid var(--border)}
.hdr-btn{background:var(--bg);border:1px solid var(--border);color:var(--text);padding:4px 10px;border-radius:6px;cursor:pointer;font-size:12px}
.hdr-btn:hover{background:var(--accent);color:#fff}
.app-nav{display:flex;gap:2px;padding:6px 12px;flex-wrap:wrap;background:var(--glass);border-bottom:1px solid var(--border)}
.nav-tab{padding:4px 10px;border-radius:6px;font-size:11px;color:var(--text2);text-decoration:none;cursor:pointer}
.nav-tab:hover,.nav-tab.router-link-active{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff}
.app-main{flex:1;padding:12px;max-width:800px;margin:0 auto;width:100%}
</style>
