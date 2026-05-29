<template>
  <div class="events-page">
    <div v-if="loading" style="display:flex;gap:16px;margin-bottom:16px">
      <el-skeleton-item variant="rect" style="width:30%;height:80px;border-radius:12px" />
      <el-skeleton-item variant="rect" style="width:30%;height:80px;border-radius:12px" />
      <el-skeleton-item variant="rect" style="width:30%;height:80px;border-radius:12px" />
    </div>
    <div v-else>
      <el-row :gutter="16">
        <el-col :span="8" v-for="s in stats" :key="s.key">
          <el-card shadow="never" class="stat-card">
            <div class="stat-val" :style="{color:s.color}">{{ s.val }}</div>
            <div class="stat-lbl">{{ s.label }}</div>
          </el-card>
        </el-col>
      </el-row>
    </div>
    <el-card shadow="never" class="page-card" style="margin-top:16px">
      <template #header>
        <div class="card-header"><span>📋 事件规则</span><el-button size="small" type="primary" @click="showCreate=true" :loading="loading">新建规则</el-button></div>
      </template>
      <el-skeleton :loading="loading" animated>
        <template #default>
          <el-table :data="rules" stripe v-if="rules.length">
            <el-table-column prop="name" label="规则名称" />
            <el-table-column prop="pattern" label="模式" />
            <el-table-column prop="action" label="动作" width="100" />
            <el-table-column label="操作" width="80"><template #default="{row}"><el-popconfirm title="删除？" @confirm="delRule(row.id)"><template #reference><el-button text type="danger" size="small">删除</el-button></template></el-popconfirm></template></el-table-column>
          </el-table>
          <el-empty v-else-if="!loadErr" description="无事件规则" />
          <el-empty v-else description="加载失败"><template #extra><el-button size="small" @click="load">重试</el-button></template></el-empty>
        </template>
      </el-skeleton>
    </el-card>
    <el-dialog v-model="showCreate" title="新建规则" width="400px">
      <el-form :model="ruleForm" label-width="60px">
        <el-form-item label="名称"><el-input v-model="ruleForm.name" /></el-form-item>
        <el-form-item label="模式"><el-input v-model="ruleForm.pattern" placeholder="*" /></el-form-item>
        <el-form-item label="动作"><el-select v-model="ruleForm.action" style="width:100%"><el-option label="通知" value="notify" /><el-option label="记录" value="log" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCreate=false">取消</el-button><el-button type="primary" @click="createRule">创建</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getEventsStats, getEventsRules, createEventRule, deleteEventRule } from '@/api'
const loading = ref(true); const loadErr = ref(false)
const stats = ref([{key:'total',label:'总事件',val:0,color:'#6366f1'},{key:'rules',label:'规则数',val:0,color:'#10b981'},{key:'hour',label:'最近1小时',val:0,color:'#f59e0b'}])
const rules = ref([]); const showCreate = ref(false)
const ruleForm = ref({name:'',pattern:'*',action:'notify'})
const load = async () => {
  loading.value = true; loadErr.value = false
  try {
    const [es, er] = await Promise.all([getEventsStats(), getEventsRules()])
    stats.value[0].val = es.total_events||'0'; stats.value[1].val = es.total_rules||'0'; stats.value[2].val = es.events_last_hour||'0'
    rules.value = er.rules||[]
  } catch { loadErr.value = true }
  finally { loading.value = false }
}
const createRule = async () => { await createEventRule(ruleForm.value); showCreate.value=false; load() }
const delRule = async (id) => { await deleteEventRule(id); load() }
onMounted(load)
</script>
<style scoped>
.events-page{max-width:1000px}
.stat-card{background:#1a1a2e;border:1px solid #2d2d44;border-radius:12px;text-align:center;padding:16px}
.stat-val{font-size:28px;font-weight:700}
.stat-lbl{font-size:13px;color:#a0aec0;margin-top:4px}
.page-card{background:#1a1a2e;border:1px solid #2d2d44;border-radius:12px}
.card-header{display:flex;justify-content:space-between;align-items:center;font-weight:600}
</style>
