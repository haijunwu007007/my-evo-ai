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
      <el-button type="primary" @click="localLogin" style="width:100%">登录</el-button>
    </el-card>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api/modules'

export default {
  name: 'LoginView',
  setup() {
    const router = useRouter()
    const route = useRoute()
    const username = ref('')
    const password = ref('')

    function oauthLogin(provider) {
      ElMessage.info(`跳转 ${provider} 授权页面`)
      window.location.href = `/api/auth/oauth/${provider}?redirect_uri=${encodeURIComponent(window.location.origin + '/oauth/callback')}`
    }

    async function localLogin() {
      try {
        const r = await api.sso.login({ username: username.value, password: password.value })
        if (r && r.success) {
          localStorage.setItem('evo_token', r.session_token || r.token || '')
          ElMessage.success('登录成功')
          const redirect = route.query.redirect || '/dashboard'
          router.push(redirect)
        } else {
          ElMessage.error(r?.error || '登录失败')
        }
      } catch (e) {
        ElMessage.error('请求失败')
      }
    }

    return { username, password, oauthLogin, localLogin }
  }
}
</script>

<style scoped>
.login-page { display:flex; justify-content:center; align-items:center; min-height:100vh; background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); }
.login-card { width:420px; text-align:center; }
.subtitle { color:#999; font-size:13px; }
</style>
