<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="logo-icon">⚡</div>
        <h2>AUTO-EVO-AI V0.1</h2>
        <p>上市公司级 AI 自动化编排系统</p>
      </div>

      <div class="login-body">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="username" placeholder="输入 admin 获得管理员权限" class="form-input" @keyup.enter="localLogin" />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="password" type="password" placeholder="留空即可" class="form-input" @keyup.enter="localLogin" />
        </div>
        <button class="login-btn" @click="localLogin" :disabled="loginLoading">
          {{ loginLoading ? '登录中...' : '登  录' }}
        </button>
        <div v-if="errMsg" class="err-msg">{{ errMsg }}</div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'

const http = axios.create({ baseURL: '/api', timeout: 15000, headers: { 'Content-Type': 'application/json' } })
http.interceptors.response.use(r => r.data, e => { throw e })

export default {
  name: 'LoginView',
  setup() {
    const router = useRouter()
    const route = useRoute()
    const username = ref('')
    const password = ref('')
    const loginLoading = ref(false)
    const errMsg = ref('')

    // 首次运行检测：如果系统未配置则跳设置向导
    http.get('/setup/status').then(r => {
      const d = r?.data || r
      if (d?.setup_required) router.replace('/setup')
    }).catch(() => {})

    async function localLogin() {
      errMsg.value = ''
      if (!username.value) { errMsg.value = '请输入用户名'; return }
      loginLoading.value = true
      try {
        const r = await http.post('/auth/login', { username: username.value })
        const d = r?.data || r
        if (d && d.access_token) {
          localStorage.setItem('evo_token', d.access_token)
          const redirect = (route.query.redirect as string) || '/dashboard'
          setTimeout(() => router.push(redirect), 100)
        } else {
          errMsg.value = d?.detail || '登录失败'
        }
      } catch (e: any) {
        errMsg.value = e.response?.data?.detail || e.message || '请求失败'
      } finally {
        loginLoading.value = false
      }
    }

    return { username, password, loginLoading, errMsg, localLogin }
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.login-card {
  width: 380px;
  background: rgba(255,255,255,0.05);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.1);
  overflow: hidden;
  box-shadow: 0 25px 50px rgba(0,0,0,0.4);
}
.login-header {
  text-align: center;
  padding: 32px 24px 20px;
}
.logo-icon {
  font-size: 40px;
  margin-bottom: 12px;
}
.login-header h2 {
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 6px;
  letter-spacing: 0.5px;
}
.login-header p {
  color: rgba(255,255,255,0.5);
  font-size: 12px;
  margin: 0;
}
.login-body {
  padding: 0 24px 28px;
}
.form-group {
  margin-bottom: 14px;
}
.form-group label {
  display: block;
  color: rgba(255,255,255,0.6);
  font-size: 12px;
  margin-bottom: 6px;
  font-weight: 500;
}
.form-input {
  width: 100%;
  padding: 10px 14px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.form-input::placeholder {
  color: rgba(255,255,255,0.3);
}
.form-input:focus {
  border-color: rgba(99,102,241,0.6);
  box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
}
.login-btn {
  width: 100%;
  padding: 11px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.1s;
  letter-spacing: 4px;
  margin-top: 4px;
}
.login-btn:hover { opacity: 0.9; }
.login-btn:active { transform: scale(0.98); }
.login-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.err-msg {
  margin-top: 12px;
  padding: 8px 12px;
  background: rgba(239,68,68,0.12);
  border: 1px solid rgba(239,68,68,0.25);
  border-radius: 6px;
  color: #fca5a5;
  font-size: 13px;
  text-align: center;
}
</style>
