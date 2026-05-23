<template>
  <div class="modules-page">
    <el-card shadow="never" class="page-card">
      <template #header>
        <div class="card-header">
          <span>📦 模块管理 ({{ categories.length }} 类)</span>
          <el-button size="small" @click="rescan">重新扫描</el-button>
        </div>
      </template>
      <div v-for="(mods, cat) in catMap" :key="cat" class="cat-group">
        <div class="cat-title">{{ cat }} ({{ mods.length }})</div>
        <div class="cat-tags">
          <el-tag v-for="m in mods" :key="m" size="small" style="margin:4px" effect="plain">{{ m }}</el-tag>
        </div>
      </div>
      <el-empty v-if="!Object.keys(catMap).length" description="暂无模块数据" />
    </el-card>
  </div>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import { getModulesCategories, rescanModules } from '@/api'
const cats = ref([])
const catMap = computed(() => cats.value)
const load = async () => { try { const r = await getModulesCategories(); cats.value = r.categories||{} } catch {} }
const rescan = async () => { try { await rescanModules(); load(); ElMessage.success('扫描完成') } catch {} }
onMounted(load)
</script>
<style scoped>
.modules-page{max-width:1000px}
.page-card{background:#1a1a2e;border:1px solid #2d2d44;border-radius:12px}
.card-header{display:flex;justify-content:space-between;align-items:center;font-weight:600}
.cat-group{margin-bottom:16px}
.cat-title{font-size:13px;font-weight:600;color:#6366f1;margin-bottom:4px;text-transform:capitalize}
.cat-tags{display:flex;flex-wrap:wrap}
</style>
