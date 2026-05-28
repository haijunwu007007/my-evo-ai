<template>
  <div class="modules-page">
    <!-- 顶部统计 -->
    <el-row :gutter="12" style="margin-bottom:16px">
      <el-col :span="6" v-for="s in stats" :key="s.label">
        <div class="mini-stat" :style="{ '--c': s.color }">
          <div class="mini-val" :style="{ color: s.color }">{{ s.val }}</div>
          <div class="mini-label">{{ s.label }}</div>
        </div>
      </el-col>
    </el-row>

    <div class="panel">
      <!-- 工具栏 -->
      <div class="toolbar">
        <el-input
          v-model="search"
          placeholder="🔍 搜索模块名 / 分类…"
          clearable
          class="search-input"
          size="default"
        />
        <div class="toolbar-right">
          <el-select v-model="filterGrade" placeholder="等级" clearable size="default" style="width:100px">
            <el-option label="Grade A" value="A" />
            <el-option label="Grade B" value="B" />
            <el-option label="Grade C" value="C" />
            <el-option label="Stub" value="Stub" />
          </el-select>
          <el-select v-model="filterCat" placeholder="分类" clearable size="default" style="width:130px">
            <el-option v-for="c in allCats" :key="c" :label="c" :value="c" />
          </el-select>
          <el-radio-group v-model="viewMode" size="small">
            <el-radio-button value="card">卡片</el-radio-button>
            <el-radio-button value="table">列表</el-radio-button>
          </el-radio-group>
          <el-button size="small" @click="rescan" :loading="rescanning">
            {{ rescanning ? '扫描中…' : '🔄 重扫' }}
          </el-button>
        </div>
      </div>

      <!-- 卡片视图 -->
      <div v-if="viewMode === 'card'" class="card-view">
        <div v-for="(mods, cat) in filteredCatMap" :key="cat" class="cat-group">
          <div class="cat-header">
            <span class="cat-title">{{ cat }}</span>
            <span class="cat-count">{{ mods.length }}</span>
          </div>
          <div class="mod-grid">
            <div
              class="mod-card"
              v-for="m in mods" :key="m.id || m.name"
              :class="gradeClass(m.grade)"
              @click="selectModule(m)"
            >
              <div class="mod-badge" :class="gradeClass(m.grade)">{{ m.grade || '?' }}</div>
              <div class="mod-name">{{ m.name || m }}</div>
              <div class="mod-actions" v-if="typeof m === 'object'">
                <el-tag size="small" :type="m.real_logic ? 'success' : 'warning'" effect="dark">
                  {{ m.real_logic ? 'REAL' : 'MOCK' }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>
        <el-empty v-if="!Object.keys(filteredCatMap).length" description="无匹配模块" :image-size="60" />
      </div>

      <!-- 列表视图 -->
      <div v-else class="table-view">
        <el-table :data="flatModules" stripe height="600" :empty-text="'暂无数据'" class="mod-table" @row-click="selectModule">
          <el-table-column label="模块名" prop="name" min-width="200" sortable>
            <template #default="{ row }">
              <span class="mod-name-cell">{{ row.name }}</span>
            </template>
          </el-table-column>
          <el-table-column label="分类" prop="group" width="120" sortable>
            <template #default="{ row }">
              <el-tag size="small" effect="plain">{{ row.group || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="等级" prop="grade" width="90" sortable>
            <template #default="{ row }">
              <el-tag size="small" :type="gradeTagType(row.grade)" effect="dark">{{ row.grade || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="row.real_logic ? 'success' : 'warning'" effect="dark">
                {{ row.real_logic ? 'REAL' : 'MOCK' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="版本" prop="version" width="80">
            <template #default="{ row }">
              <span style="font-size:11px;color:#4a5568">{{ row.version || 'V0.1' }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 模块详情抽屉 -->
    <el-drawer v-model="drawerVisible" title="模块详情" size="360px" direction="rtl" class="mod-drawer">
      <div v-if="selectedMod" class="mod-detail">
        <div class="detail-header">
          <div class="detail-icon">📦</div>
          <div>
            <div class="detail-name">{{ selectedMod.name || selectedMod }}</div>
            <el-tag :type="gradeTagType(selectedMod.grade)" size="small" effect="dark" style="margin-top:4px">
              {{ selectedMod.grade || 'N/A' }}
            </el-tag>
          </div>
        </div>
        <el-descriptions :column="1" border size="small" style="margin-top:16px">
          <el-descriptions-item label="ID">{{ selectedMod.id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="分组">{{ selectedMod.group || '-' }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{ selectedMod.version || 'V0.1' }}</el-descriptions-item>
          <el-descriptions-item label="业务逻辑">
            <el-tag :type="selectedMod.real_logic ? 'success' : 'warning'" size="small">
              {{ selectedMod.real_logic ? '真实' : '模拟' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="描述">{{ selectedMod.description || '—' }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { rescanModules } from '@/api'
import api from '@/api'

const cats = ref({})
const search = ref('')
const filterGrade = ref('')
const filterCat = ref('')
const viewMode = ref('card')
const rescanning = ref(false)
const drawerVisible = ref(false)
const selectedMod = ref(null)
const allModules = ref([])

const allCats = computed(() => Object.keys(cats.value))

const gradeClass = (g) => {
  if (!g) return 'grade-unknown'
  const upper = String(g).toUpperCase()
  if (upper === 'A') return 'grade-a'
  if (upper === 'B') return 'grade-b'
  if (upper === 'C') return 'grade-c'
  return 'grade-stub'
}

const gradeTagType = (g) => {
  if (!g) return 'info'
  const upper = String(g).toUpperCase()
  if (upper === 'A') return 'success'
  if (upper === 'B') return 'primary'
  if (upper === 'C') return 'warning'
  return 'danger'
}

const filteredCatMap = computed(() => {
  const result = {}
  for (const [cat, mods] of Object.entries(cats.value)) {
    if (filterCat.value && cat !== filterCat.value) continue
    const filtered = mods.filter(m => {
      const name = typeof m === 'string' ? m : (m.name || '')
      const grade = typeof m === 'object' ? (m.grade || '') : ''
      if (search.value && !name.toLowerCase().includes(search.value.toLowerCase()) && !cat.toLowerCase().includes(search.value.toLowerCase())) return false
      if (filterGrade.value && grade.toUpperCase() !== filterGrade.value.toUpperCase()) return false
      return true
    })
    if (filtered.length) result[cat] = filtered
  }
  return result
})

const flatModules = computed(() => {
  const list = []
  for (const [cat, mods] of Object.entries(filteredCatMap.value)) {
    for (const m of mods) {
      list.push(typeof m === 'string' ? { name: m, group: cat } : { ...m, group: m.group || cat })
    }
  }
  return list
})

const stats = computed(() => {
  const total = allModules.value.length
  const A = allModules.value.filter(m => (m.grade || '').toUpperCase() === 'A').length
  // API 返回 is_real，前端兼容两种字段名
  const real = allModules.value.filter(m => m.is_real === true || m.real_logic === true).length
  const grps = Object.keys(cats.value).length
  return [
    { label: '总模块', val: total, color: '#6366f1' },
    { label: 'Grade A', val: A, color: '#10b981' },
    { label: '真实逻辑', val: real, color: '#06b6d4' },
    { label: '分类数', val: grps, color: '#f59e0b' },
  ]
})

const selectModule = (m) => {
  selectedMod.value = typeof m === 'string' ? { name: m } : m
  drawerVisible.value = true
}

const load = async () => {
  try {
    // 从 /api/modules/list 获取全部模块（limit=500 不打分页）
    const r = await api.get('/modules/list', { params: { limit: 500, offset: 0 } })
    const mods = r.modules || []
    allModules.value = mods
    // 按 category 分组
    const grouped = {}
    for (const m of mods) {
      const cat = m.category || '其他'
      if (!grouped[cat]) grouped[cat] = []
      grouped[cat].push(m)
    }
    cats.value = grouped
  } catch (e) {
    console.error('加载模块失败', e)
  }
}

const rescan = async () => {
  rescanning.value = true
  try {
    await rescanModules()
    await load()
    ElMessage.success('扫描完成')
  } catch {
    ElMessage.error('扫描失败')
  }
  rescanning.value = false
}

onMounted(load)
</script>

<style scoped>
.modules-page { max-width: 1280px; padding-bottom: 32px; }

/* 迷你统计 */
.mini-stat {
  background: linear-gradient(135deg, #1a1a2e, #16213e);
  border: 1px solid #2d2d44;
  border-left: 3px solid var(--c, #6366f1);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 0;
}
.mini-val { font-size: 26px; font-weight: 700; line-height: 1.1; }
.mini-label { font-size: 12px; color: #7b8fa1; margin-top: 2px; }

/* 面板 */
.panel {
  background: #1a1a2e;
  border: 1px solid #2d2d44;
  border-radius: 12px;
  overflow: hidden;
}

/* 工具栏 */
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid #2d2d44;
  flex-wrap: wrap;
}
.search-input { flex: 1; min-width: 180px; }
.search-input :deep(.el-input__wrapper) { background: #0f0f1a; border-color: #2d2d44; }
.toolbar-right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

/* 卡片视图 */
.card-view { padding: 16px; max-height: 680px; overflow: auto; }
.cat-group { margin-bottom: 20px; }
.cat-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.cat-title { font-size: 12px; font-weight: 700; color: #6366f1; text-transform: uppercase; letter-spacing: 1px; }
.cat-count { background: #6366f1; color: #fff; font-size: 11px; border-radius: 10px; padding: 1px 7px; }
.mod-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.mod-card {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: #0f0f1a;
  border: 1px solid #1f1f33;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  font-size: 12px;
  color: #e2e8f0;
}
.mod-card:hover { border-color: #6366f1; background: #1a1a30; transform: translateY(-1px); }
.mod-badge {
  font-size: 10px;
  font-weight: 700;
  width: 18px;
  height: 18px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.grade-a .mod-badge { background: rgba(16,185,129,0.2); color: #10b981; }
.grade-b .mod-badge { background: rgba(99,102,241,0.2); color: #6366f1; }
.grade-c .mod-badge { background: rgba(245,158,11,0.2); color: #f59e0b; }
.grade-stub .mod-badge { background: rgba(239,68,68,0.2); color: #ef4444; }
.grade-unknown .mod-badge { background: rgba(74,85,104,0.2); color: #4a5568; }
.mod-name { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 140px; }
.mod-actions { margin-left: auto; }

/* 列表视图 */
.table-view { padding: 0; }
.mod-table { --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent; }
.mod-table :deep(.el-table__header) { background: #0f0f1a; }
.mod-table :deep(.el-table__row) { background: transparent; }
.mod-table :deep(.el-table__row:hover > td) { background: rgba(99,102,241,0.06) !important; }
.mod-name-cell { font-size: 13px; font-weight: 500; color: #e2e8f0; }

/* 抽屉 */
.mod-detail { padding: 4px; }
.detail-header { display: flex; gap: 12px; align-items: flex-start; margin-bottom: 8px; }
.detail-icon { font-size: 32px; }
.detail-name { font-size: 16px; font-weight: 700; color: #e2e8f0; }
</style>
