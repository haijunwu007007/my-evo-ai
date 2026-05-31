<template>
  <div class="login-page">
    <el-card class="login-card">
      <h2>AUTO-EVO-AI V0.1</h2>
      <p class="subtitle">上市公司级 AI 自动化编排系统</p>
      <el-divider />
      <h4>OAuth2 登录</h4>
      <el-button type="primary" @click="oauthLogin('github')" style="width:100%;margin-bottom:10px">
        <i class="el-icon-platform-eleme"></i> GitHub 登录
      </el-button>
      <el-button type="danger" @click="oauthLogin('google')" style="width:100%;margin-bottom:10px">
        Google 登录
      </el-button>
      <el-button type="success" @click="oauthLogin('wechat')" style="width:100%">
        微信登录
      </el-button>
      <el-divider>或</el-divider>
      <h4>本地账户</h4>
      <el-input v-model="username" placeholder="用户名" style="margin-bottom:10px" />
      <el-input v-model="password" type="password" placeholder="密码" style="margin-bottom:10px" show-password />
      <el-button type="primary" @click="localLogin" :loading="loginLoading" style="width:100%">{{ loginLoading ? '登录中...' : '登录' }}</el-button>
    </el-card>
  </div>
</template>

<script lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
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

    function oauthLogin(provider: any) {
      ElMessage.info(`跳转 ${provider} 授权页面`)
      window.location.href = `/api/auth/oauth/${provider}?redirect_uri=${encodeURIComponent(window.location.origin + '/oauth/callback')}`
    }

    async function localLogin() {
      try {
        if (!username.value) { ElMessage.warning('请输入用户名'); return }
        loginLoading.value = true
        const r = await http.post('/auth/login', { username: username.value })
        const d = r?.data || r
        if (d && d.access_token) {
          localStorage.setItem('evo_token', d.access_token)
          ElMessage.success('登录成功')
          const redirect = route.query.redirect || '/dashboard'
          setTimeout(() => router.push(redirect), 100)
        } else {
          ElMessage.error(d?.detail || '登录失败')
        }
      } catch (e: any) {
        const msg = e.response?.data?.detail || e.message || '请求失败'
        ElMessage.error(msg)
      } finally {
        loginLoading.value = false
      }
    }

    return { username, password, loginLoading, oauthLogin, localLogin }
  }
}
</script>

<style scoped>
.login-page { display:flex; justify-content:center; align-items:center; min-height:100vh; background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); }
.login-card { width:420px; text-align:center; }
.subtitle { color:#999; font-size:13px; }
</style>
