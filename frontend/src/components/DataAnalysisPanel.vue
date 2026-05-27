<template>
  <div class="da-panel">
    <el-row :gutter="16">
      <!-- 输入区 -->
      <el-col :span="8">
        <el-card shadow="never">
          <template #header><b>数据输入</b></template>
          <el-input v-model="inputData" type="textarea" :rows="6" placeholder="输入数字，逗号分隔，如：1,2,3,4,5,6,7,8,9,10" />
          <div style="margin-top:8px">
            <el-button size="small" type="primary" @click="doDescribe">描述统计</el-button>
            <el-button size="small" type="success" @click="doOutliers">异常检测</el-button>
            <el-button size="small" type="warning" @click="doHistogram">直方图</el-button>
            <el-button size="small" @click="doNormalize">归一化</el-button>
          </div>

          <el-divider />
          <b>回归分析</b>
          <el-input v-model="inputX" type="textarea" :rows="2" placeholder="X 值，逗号分隔" style="margin:4px 0" />
          <el-input v-model="inputY" type="textarea" :rows="2" placeholder="Y 值，逗号分隔" />
          <el-button size="small" type="warning" style="margin-top:4px" @click="doRegression">线性回归</el-button>
          <el-button size="small" @click="doCorrelation">相关系数</el-button>

          <el-divider />
          <b>聚类分析</b>
          <div style="display:flex;gap:4px;margin-top:4px">
            <el-input-number v-model="clusterK" :min="2" :max="10" size="small" />
            <el-button size="small" type="danger" @click="doCluster">KMeans</el-button>
          </div>

          <el-divider />
          <el-button size="small" @click="doSummarize">系统数据摘要</el-button>
          <el-button size="small" @click="doExport">导出 CSV</el-button>
        </el-card>
      </el-col>

      <!-- 结果区 -->
      <el-col :span="16">
        <el-card shadow="never">
          <template #header><b>分析结果</b></template>
          <div v-if="!result" style="text-align:center;color:#999;padding:40px">等待分析...</div>
          <div v-else-if="result.error" style="color:#f56c6c">{{ result.error }}</div>
          <div v-else>
            <!-- 描述统计 -->
            <el-descriptions v-if="result.stats" :column="3" border size="small">
              <el-descriptions-item v-for="(v,k) in result.stats" :key="k" :label="k">{{ v }}</el-descriptions-item>
            </el-descriptions>

            <!-- 相关系数 -->
            <div v-if="result.pearson !== undefined">
              <el-tag :type="Math.abs(result.pearson) > 0.7 ? 'success' : 'info'">
                r = {{ result.pearson }} ({{ result.interpretation }})
              </el-tag>
            </div>

            <!-- 回归 -->
            <div v-if="result.slope !== undefined">
              <el-descriptions :column="2" border size="small">
                <el-descriptions-item label="公式">{{ result.formula }}</el-descriptions-item>
                <el-descriptions-item label="R²">{{ result.r_squared }}</el-descriptions-item>
              </el-descriptions>
            </div>

            <!-- 异常检测 -->
            <div v-if="result.anomalies !== undefined">
              <el-tag :type="result.anomalies.length ? 'danger' : 'success'" style="margin-bottom:4px">
                发现 {{ result.anomalies.length }} 个异常 ({{ result.anomaly_rate }}%)
              </el-tag>
              <div v-if="result.anomalies.length">{{ result.anomalies.join(', ') }}</div>
            </div>

            <!-- 直方图 -->
            <div v-if="result.histogram">
              <div v-for="(b,i) in result.histogram" :key="i" class="bar-row">
                <span class="bar-label">{{ (result.min + i * result.bin_width).toFixed(1) }}</span>
                <div class="bar-track"><div class="bar-fill" :style="{ width: (b / Math.max(...result.histogram) * 100) + '%' }" /></div>
                <span class="bar-count">{{ b }}</span>
              </div>
            </div>

            <!-- 归一化 -->
            <div v-if="result.normalized">
              <el-tag>归一化 {{ result.method }}</el-tag>
              <div style="margin-top:4px;font-size:12px;color:#666">{{ result.normalized.slice(0,20).join(', ') }}</div>
            </div>

            <!-- 聚类 -->
            <div v-if="result.k !== undefined">
              <el-tag>{{ result.k }} 个簇</el-tag>
              <div v-if="result.wcss !== undefined" style="font-size:12px;color:#999">WCSS: {{ result.wcss.toFixed(2) }}</div>
            </div>

            <!-- CSV 导出 -->
            <div v-if="result.csv">
              <el-input :model-value="result.csv" type="textarea" :rows="6" readonly />
            </div>

            <!-- 系统摘要 -->
            <div v-if="result.report">
              <pre style="font-size:12px;background:#f5f7fa;padding:8px;border-radius:4px">{{ JSON.stringify(result.report, null, 2) }}</pre>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useDataAnalysisStore } from '../stores/dataAnalysis'

const store = useDataAnalysisStore()
const result = ref(null)

const inputData = ref('')
const inputX = ref('')
const inputY = ref('')
const clusterK = ref(3)

function parse(v) { return v.split(',').map(s => parseFloat(s.trim())).filter(n => !isNaN(n)) }

async function doDescribe() { result.value = await store.describe(parse(inputData.value)) }
async function doOutliers() { result.value = await store.outliers(parse(inputData.value)) }
async function doHistogram() { result.value = await store.histogram(parse(inputData.value), 10) }
async function doNormalize() { result.value = await store.normalize(parse(inputData.value)) }
async function doRegression() { result.value = await store.regress(parse(inputX.value), parse(inputY.value)) }
async function doCorrelation() { result.value = await store.correlate(parse(inputX.value), parse(inputY.value)) }
async function doCluster() { result.value = await store.cluster(parse(inputData.value), clusterK.value) }
async function doSummarize() { result.value = await store.summarize() }
async function doExport() { result.value = await store.exportData(parse(inputData.value)) }
</script>

<style scoped>
.bar-row { display: flex; align-items: center; gap: 8px; margin: 2px 0; font-size: 12px; }
.bar-label { min-width: 50px; text-align: right; color: #666; }
.bar-track { flex: 1; height: 14px; background: #f0f2f5; border-radius: 3px; }
.bar-fill { height: 100%; background: #409eff; border-radius: 3px; transition: width .3s; }
.bar-count { min-width: 30px; color: #999; }
</style>
