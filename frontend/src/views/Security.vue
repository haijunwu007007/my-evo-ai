<template>
  <div class="security-page">
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="never" class="page-card">
          <template #header><div class="card-header">🔒 认证状态</div></template>
          <div class="info-row" v-for="(v,k) in auth" :key="k"><span class="info-key">{{k}}</span><el-tag :type="v?'success':'danger'" size="small">{{v?'✅':'❌'}}</el-tag></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="page-card">
          <template #header><div class="card-header">🛡️ API 安全</div></template>
          <div class="info-row" v-for="(v,k) in sec" :key="k"><span class="info-key">{{k}}</span><el-tag :type="v?'success':'danger'" size="small">{{v?'✅':'❌'}}</el-tag></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { getAuthStatus, getSecurityStatus } from '@/api'
const auth = ref({}); const sec = ref({})
onMounted(async () => {
  try { const [a, s] = await Promise.all([getAuthStatus(), getSecurityStatus()]); auth.value = a; sec.value = s } catch {}
})
</script>
<style scoped>
.security-page{max-width:800px}
.page-card{background:#1a1a2e;border:1px solid #2d2d44;border-radius:12px}
.card-header{font-weight:600}
.info-row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #2d2d44;font-size:13px}
.info-key{color:#a0aec0;text-transform:capitalize}
</style>
