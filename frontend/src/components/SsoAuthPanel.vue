<template>
  <div class="sso-panel">
    <el-row :gutter="16">
      <!-- 用户注册 -->
      <el-col :span="8">
        <el-card shadow="never">
          <template #header><b>注册用户</b></template>
          <el-form :model="regForm" label-width="70" size="small">
            <el-form-item label="用户名"><el-input v-model="regForm.username" /></el-form-item>
            <el-form-item label="密码"><el-input v-model="regForm.password" type="password" show-password /></el-form-item>
            <el-form-item label="角色"><el-select v-model="regForm.roles" multiple style="width:100%">
              <el-option label="admin" value="admin" disabled /><el-option label="user" value="user" /><el-option label="viewer" value="viewer" />
            </el-select></el-form-item>
            <el-form-item><el-button type="primary" @click="register" :loading="store.loading">注册</el-button></el-form-item>
          </el-form>
          <el-alert v-if="store.error" :title="store.error" type="error" show-icon :closable="false" />
        </el-card>
      </el-col>

      <!-- 用户认证 -->
      <el-col :span="8">
        <el-card shadow="never">
          <template #header><b>用户认证</b></template>
          <el-form :model="authForm" label-width="70" size="small">
            <el-form-item label="用户名"><el-input v-model="authForm.username" /></el-form-item>
            <el-form-item label="密码"><el-input v-model="authForm.password" type="password" show-password /></el-form-item>
            <el-form-item><el-button type="success" @click="authenticate" :loading="store.loading">认证</el-button></el-form-item>
          </el-form>
          <div v-if="store.currentUser" class="auth-result">
            <el-tag type="success">✅ {{ store.currentUser.username }} ({{ store.currentUser.roles?.join(',') }})</el-tag>
          </div>
        </el-card>

        <el-card shadow="never" style="margin-top:12px">
          <template #header><b>JWT 令牌</b></template>
          <el-form :model="jwtForm" label-width="70" size="small">
            <el-form-item label="用户ID"><el-input v-model="jwtForm.userId" /></el-form-item>
            <el-form-item label="角色"><el-select v-model="jwtForm.role" style="width:100%">
              <el-option label="admin" value="admin" /><el-option label="user" value="user" />
            </el-select></el-form-item>
            <el-form-item><el-button @click="genJwt" type="warning">签发 JWT</el-button></el-form-item>
          </el-form>
          <div v-if="store.jwtToken" class="jwt-result">
            <el-input :model-value="store.jwtToken" type="textarea" :rows="2" readonly />
          </div>
        </el-card>
      </el-col>

      <!-- 活跃会话 -->
      <el-col :span="8">
        <el-card shadow="never">
          <template #header><b>活跃会话 ({{ sessions.length }})</b></template>
          <el-table :data="sessions" size="small" stripe max-height="360">
            <el-table-column prop="user_id" label="用户" width="80" />
            <el-table-column prop="apps" label="应用" min-width="100">
              <template #default="{ row }">{{ row.apps?.join(',') || '-' }}</template>
            </el-table-column>
            <el-table-column prop="expires_at" label="过期" width="90">
              <template #default="{ row }">
                <span v-if="row.expires_at">{{ new Date(row.expires_at * 1000).toLocaleTimeString() }}</span>
              </template>
            </el-table-column>
          </el-table>
          <el-button size="small" style="margin-top:8px" @click="refresh">刷新</el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useSsoAuthStore } from '../stores/ssoAuth'

const store = useSsoAuthStore()
const sessions = ref([])

const regForm = ref({ username: '', password: '', roles: ['user'] })
const authForm = ref({ username: '', password: '' })
const jwtForm = ref({ userId: 'user1', role: 'user' })

async function register() { await store.registerUser(regForm.value.username, regForm.value.password, regForm.value.roles) }
async function authenticate() { await store.authenticate(authForm.value.username, authForm.value.password) }
async function genJwt() { await store.generateJwt(jwtForm.value.userId, jwtForm.value.role) }
async function refresh() {
  const r = await store.listSessions()
  if (r?.sessions) sessions.value = r.sessions
}

onMounted(refresh)
</script>

<style scoped>
.auth-result, .jwt-result { margin-top: 8px; }
</style>
