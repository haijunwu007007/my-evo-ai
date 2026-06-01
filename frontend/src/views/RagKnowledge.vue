<template>
  <div class="rag-container">
    <el-page-header title="知识库" content="RAG 知识库管理" @back="$router.push('/dashboard')" />
    <el-divider />
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header><span>知识库文档</span></template>
          <el-empty v-if="!documents.length" description="暂无文档，上传文件构建知识库" />
          <el-table v-else :data="documents" stripe style="width:100%" size="small">
            <el-table-column prop="name" label="文件名" />
            <el-table-column prop="size" label="大小" width="100" />
            <el-table-column prop="chunks" label="分块数" width="80" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'ready' ? 'success' : 'warning'" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button type="danger" size="small" @click="deleteDoc(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span>上传文档</span></template>
          <el-upload drag :http-request="uploadDoc" accept=".txt,.md,.pdf,.docx">
            <el-icon class="upload-icon" size="40"><UploadFilled /></el-icon>
            <div>拖拽或点击上传文件</div>
            <template #tip><div style="font-size:12px;color:#999">支持 txt/md/pdf/docx</div></template>
          </el-upload>
        </el-card>
        <el-card shadow="hover" style="margin-top:16px">
          <template #header><span>知识库统计</span></template>
          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="文档数">{{ documents.length }}</el-descriptions-item>
            <el-descriptions-item label="向量维度">1536</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'

interface Document {
  name: string; size: string; chunks: number; status: string
}

const documents = ref<Document[]>([])

onMounted(async () => {
  try {
    const r = await fetch('/api/rag/documents')
    const d = await r.json()
    if (d.success) documents.value = d.documents || []
  } catch { /* offline */ }
})

const uploadDoc = async (opt: any) => {
  try {
    const form = new FormData()
    form.append('file', opt.file)
    const r = await fetch('/api/rag/upload', { method: 'POST', body: form })
    const d = await r.json()
    if (d.success) {
      ElMessage.success('上传成功')
      documents.value.push(d.doc)
    } else {
      ElMessage.error(d.error || '上传失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '上传失败')
  }
}

const deleteDoc = async (doc: Document) => {
  try {
    const r = await fetch(`/api/rag/delete?name=${encodeURIComponent(doc.name)}`, { method: 'DELETE' })
    const d = await r.json()
    if (d.success) {
      ElMessage.success('已删除')
      documents.value = documents.value.filter(x => x.name !== doc.name)
    }
  } catch { /* ignore */ }
}
</script>

<style scoped>
.rag-container { padding: 20px; }
.upload-icon { margin-bottom: 10px; }
</style>
