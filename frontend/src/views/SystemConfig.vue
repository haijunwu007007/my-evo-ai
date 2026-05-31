<template>
  <div class="config-page">
    <h2>⚙️ 系统配置</h2>
    <el-tabs v-model="tab">
      <!-- AI 提供商 -->
      <el-tab-pane label="🤖 AI 提供商" name="ai">
        <el-card shadow="never" class="page-card">
          <template #header><span>AI 模型配置</span></template>
          <el-form label-width="140px">
            <el-form-item label="默认 AI 提供商">
              <el-select v-model="form.ai_provider" style="width:200px">
                <el-option label="智谱 (Zhipu)" value="zhipu" />
                <el-option label="API2D" value="api2d" />
              </el-select>
            </el-form-item>
            <el-form-item label="API2D Key">
              <el-input v-model="form.api2d_key" placeholder="fk-..." show-password style="width:400px" />
            </el-form-item>
            <el-form-item label="API2D 模型">
              <el-input v-model="form.api2d_model" placeholder="gpt-3.5-turbo" style="width:200px" />
            </el-form-item>
            <el-form-item label="智谱 Key">
              <el-input v-model="form.zhipu_key" placeholder="..." show-password style="width:400px" />
            </el-form-item>
            <el-form-item label="智谱 模型">
              <el-input v-model="form.zhipu_model" placeholder="glm-4.7" style="width:200px" />
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
      <!-- 通知 -->
      <el-tab-pane label="📢 通知" name="notify">
        <el-card shadow="never" class="page-card">
          <template #header><span>通知渠道配置</span></template>
          <el-form label-width="140px">
            <el-form-item label="企业微信 Webhook">
              <el-input v-model="form.wecom_webhook" placeholder="https://qyapi.weixin.qq.com/..." style="width:500px" />
            </el-form-item>
            <el-form-item label="钉钉 Webhook">
              <el-input v-model="form.dingtalk_webhook" placeholder="https://oapi.dingtalk.com/..." style="width:500px" />
            </el-form-item>
            <el-form-item label="飞书 Webhook">
              <el-input v-model="form.feishu_webhook" placeholder="https://open.feishu.cn/..." style="width:500px" />
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
      <!-- 外部服务 -->
      <el-tab-pane label="🔌 外部服务" name="external">
        <el-card shadow="never" class="page-card">
          <template #header><span>外部 API 配置</span></template>
          <el-form label-width="160px">
            <el-form-item label="GitHub Token">
              <el-input v-model="form.github_token" placeholder="ghp_..." show-password style="width:400px" />
              <div class="hint">用于 github_scanner、web_scraper 等模块</div>
            </el-form-item>
            <el-form-item label="Telegram Bot Token">
              <el-input v-model="form.telegram_token" placeholder="..." show-password style="width:400px" />
              <div class="hint">用于 telegram_bridge 模块</div>
            </el-form-item>
            <el-form-item label="SMTP 邮箱">
              <el-input v-model="form.smtp_email" placeholder="user@example.com" style="width:300px" />
            </el-form-item>
            <el-form-item label="SMTP 密码">
              <el-input v-model="form.smtp_password" placeholder="..." show-password style="width:300px" />
            </el-form-item>
            <el-form-item label="OpenAI Key">
              <el-input v-model="form.openai_key" placeholder="sk-..." show-password style="width:400px" />
            </el-form-item>
            <el-form-item label="DeepSeek Key">
              <el-input v-model="form.deepseek_key" placeholder="sk-..." show-password style="width:400px" />
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
      <!-- 系统 -->
      <el-tab-pane label="⚡ 系统" name="system">
        <el-card shadow="never" class="page-card">
          <template #header><span>系统设置</span></template>
          <el-form label-width="140px">
            <el-form-item label="启用自适应引擎">
              <el-switch v-model="form.enable_evo" />
            </el-form-item>
            <el-form-item label="启用参数自进化">
              <el-switch v-model="form.enable_param_evo" />
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>
    <div style="display:flex;gap:12px;margin-top:16px;justify-content:flex-end">
      <el-button type="primary" @click="save">💾 保存配置</el-button>
      <el-button @click="load">🔄 重置</el-button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getConfig, setConfig } from '@/api'
const tab = ref('ai')
const form = ref({
  ai_provider: 'api2d', api2d_key: '', api2d_model: 'gpt-3.5-turbo',
  zhipu_key: '', zhipu_model: 'glm-4.7',
  wecom_webhook: '', dingtalk_webhook: '', feishu_webhook: '',
  github_token: '', telegram_token: '',
  smtp_email: '', smtp_password: '',
  openai_key: '', deepseek_key: '',
  enable_evo: true, enable_param_evo: true,
})
const load = async () => {
  const r = await getConfig()
  if (r?.success && r.data) Object.assign(form.value, r.data)
}
const save = async () => {
  await setConfig('api_keys', form.value)
  ElMessage.success('配置已保存')
}
onMounted(load)
</script>
<style scoped>
.config-page{max-width:900px;margin:0 auto;padding-bottom:32px}
.page-card{background:var(--bg-card);border:1px solid var(--border-subtle);border-radius:12px;margin-bottom:16px}
.hint{font-size:11px;color:var(--text-muted);margin-top:2px}
:deep(.el-form-item){margin-bottom:14px}
</style>
