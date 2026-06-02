<template>
  <div class="setup-page">
    <div class="setup-card">
      <!-- 步骤 1: 欢迎 -->
      <div v-if="step === 1" class="step-content">
        <div class="logo-icon">⚡</div>
        <h1>AUTO-EVO-AI V0.1</h1>
        <p class="subtitle">欢迎！首次运行需要完成以下配置</p>
        <ul class="feature-list">
          <li>✅ 452 个智能模块</li>
          <li>✅ 30 个外部工具集成</li>
          <li>✅ 多模型 LLM 网关</li>
          <li>✅ 桌面自动化 + 语音控制</li>
        </ul>
        <button class="setup-btn" @click="step = 2">开始配置 →</button>
      </div>

      <!-- 步骤 2: 管理员账号 -->
      <div v-if="step === 2" class="step-content">
        <h2>📝 创建管理员账号</h2>
        <p class="subtitle">设置用户名和密码用于登录系统</p>
        <div class="form-group">
          <label>用户名</label>
          <input v-model="form.username" placeholder="admin" class="form-input" />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="form.password" type="password" placeholder="至少 4 位" class="form-input" />
        </div>
        <div class="btn-row">
          <button class="setup-btn" @click="step = 1" style="background:#444">← 上一步</button>
          <button class="setup-btn" @click="step = 3" :disabled="!form.username || form.password.length < 4">下一步 →</button>
        </div>
      </div>

      <!-- 步骤 3: API Key -->
      <div v-if="step === 3" class="step-content">
        <h2>🔑 配置 API Key（可选）</h2>
        <p class="subtitle">填写后可直接调用 AI 模型，也可以跳过后期再配</p>
        <div class="form-group">
          <label>智谱 AI (Zhipu) Key</label>
          <input v-model="form.apiKeys.zhipu" placeholder="留空跳过" class="form-input" />
        </div>
        <div class="form-group">
          <label>OpenAI Key</label>
          <input v-model="form.apiKeys.openai" placeholder="sk-..." class="form-input" />
        </div>
        <div class="form-group">
          <label>DeepSeek Key</label>
          <input v-model="form.apiKeys.deepseek" placeholder="sk-..." class="form-input" />
        </div>
        <div class="btn-row">
          <button class="setup-btn" @click="step = 2" style="background:#444">← 上一步</button>
          <button class="setup-btn" @click="submit" :loading="submitting">{{ submitting ? '配置中...' : '✅ 完成配置' }}</button>
        </div>
        <div v-if="errMsg" class="err-msg">{{ errMsg }}</div>
      </div>

      <!-- 完成 -->
      <div v-if="step === 4" class="step-content">
        <div class="logo-icon">🎉</div>
        <h2>配置完成！</h2>
        <p class="subtitle">系统已准备就绪，请使用刚设置的用户名和密码登录</p>
        <button class="setup-btn" @click="goLogin">进入登录 →</button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
const http = axios.create({ baseURL: '/api', timeout: 15000 })
http.interceptors.response.use(r => r.data, e => { throw e })

export default {
  name: 'SetupWizard',
  setup() {
    const router = useRouter()
    const step = ref(1)
    const submitting = ref(false)
    const errMsg = ref('')
    const form = ref({
      username: '',
      password: '',
      apiKeys: { zhipu: '', openai: '', deepseek: '', github: '' } as Record<string, string>,
    })

    async function submit() {
      submitting.value = true; errMsg.value = ''
      try {
        await http.post('/setup/complete', {
          username: form.value.username,
          password: form.value.password,
          api_keys: form.value.apiKeys,
        })
        step.value = 4
      } catch (e: any) {
        errMsg.value = e.response?.data?.detail || e.message || '配置失败'
      } finally { submitting.value = false }
    }

    function goLogin() { router.push('/login') }

    return { step, form, submitting, errMsg, submit, goLogin }
  }
}
</script>

<style scoped>
.setup-page {
  display: flex; justify-content: center; align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.setup-card {
  width: 440px; background: rgba(255,255,255,0.05);
  backdrop-filter: blur(20px); border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.1);
  padding: 36px; box-shadow: 0 25px 50px rgba(0,0,0,0.4);
}
.step-content { text-align: center; }
.logo-icon { font-size: 48px; margin-bottom: 12px; }
h1, h2 { color: #fff; margin: 0 0 8px; }
.subtitle { color: rgba(255,255,255,0.5); font-size: 13px; margin: 0 0 24px; }
.feature-list { text-align: left; list-style: none; padding: 0; margin: 0 0 24px; }
.feature-list li { color: rgba(255,255,255,0.7); padding: 6px 0; font-size: 14px; }
.form-group { text-align: left; margin-bottom: 14px; }
.form-group label { display: block; color: rgba(255,255,255,0.6); font-size: 12px; margin-bottom: 6px; }
.form-input {
  width: 100%; padding: 10px 14px; background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; color: #fff;
  font-size: 14px; outline: none; box-sizing: border-box;
}
.form-input::placeholder { color: rgba(255,255,255,0.3); }
.form-input:focus { border-color: rgba(99,102,241,0.6); box-shadow: 0 0 0 3px rgba(99,102,241,0.15); }
.setup-btn {
  padding: 11px 24px; background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff; border: none; border-radius: 8px; font-size: 14px;
  font-weight: 600; cursor: pointer; margin-top: 8px;
  transition: opacity .2s;
}
.setup-btn:hover { opacity: .9; }
.setup-btn:disabled { opacity: .5; cursor: not-allowed; }
.btn-row { display: flex; gap: 12px; justify-content: center; margin-top: 8px; }
.err-msg { margin-top: 12px; padding: 8px; background: rgba(239,68,68,0.12);
  border: 1px solid rgba(239,68,68,0.25); border-radius: 6px; color: #fca5a5; font-size: 13px; }
</style>
