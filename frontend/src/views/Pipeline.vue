<template>
  <div class="pipeline-page">
    <el-card shadow="never" class="page-card">
      <template #header>
        <div class="card-header"><span>🔗 管线引擎</span><el-button size="small" type="primary" @click="showCreate=true">新建管线</el-button></div>
      </template>
      <el-table :data="pipelines" stripe v-if="pipelines.length">
        <el-table-column prop="name" label="管线名称" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="status" label="状态" width="90"><template #default="{row}"><el-tag :type="row.status==='running'?'success':'info'" size="small">{{row.status}}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{row}">
            <el-button text size="small" @click="exec(row.id)">执行</el-button>
            <el-popconfirm title="删除？" @confirm="remove(row.id)"><template #reference><el-button text type="danger" size="small">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="无管线" />
    </el-card>
    <el-dialog v-model="showCreate" title="新建管线" width="450px">
      <el-form :model="form" label-width="60px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCreate=false">取消</el-button><el-button type="primary" @click="create">创建</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getPipelines, createPipeline, executePipeline, deletePipeline } from '@/api'
const pipelines = ref([]); const showCreate = ref(false)
const form = ref({name:'',description:''})
const load = async () => { try { const r = await getPipelines(); pipelines.value = r.pipelines||[] } catch {} }
const create = async () => { await createPipeline(form.value); showCreate.value=false; load() }
const exec = async (id) => { await executePipeline(id); load() }
const remove = async (id) => { await deletePipeline(id); load() }
onMounted(load)
</script>
<style scoped>
.pipeline-page{max-width:1000px}
.page-card{background:#1a1a2e;border:1px solid #2d2d44;border-radius:12px}
.card-header{display:flex;justify-content:space-between;align-items:center;font-weight:600}
</style>
