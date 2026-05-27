/**
 * AUTO-EVO-AI V0.1 — Data Analysis 数据分析 Store
 */
import { defineStore } from 'pinia'
import { da } from '../api/modules'

export const useDataAnalysisStore = defineStore('dataAnalysis', {
  state: () => ({
    result: null,
    loading: false,
    error: null,
    history: [],
  }),

  actions: {
    async describe(data) {
      this.loading = true; this.error = null
      try {
        const r = await da.describe(data)
        this.result = r?.success ? r : null
        if (!r?.success) this.error = r?.error || '分析失败'
        if (r?.success) this.history.push({ action: 'describe', time: Date.now(), data })
        return r
      } catch (e) { this.error = e.message }
      finally { this.loading = false }
    },

    async correlate(x, y) {
      this.loading = true; this.error = null
      try {
        const r = await da.correlation(x, y)
        this.result = r?.success ? r : null
        return r
      } catch (e) { this.error = e.message }
      finally { this.loading = false }
    },

    async outliers(data, method) {
      this.loading = true; this.error = null
      try {
        const r = await da.outliers(data, method)
        this.result = r?.success ? r : null
        return r
      } catch (e) { this.error = e.message }
      finally { this.loading = false }
    },

    async histogram(data, bins) {
      this.loading = true; this.error = null
      try {
        const r = await da.histogram(data, bins)
        this.result = r?.success ? r : null
        return r
      } catch (e) { this.error = e.message }
      finally { this.loading = false }
    },

    async normalize(data, method) {
      this.loading = true; this.error = null
      try {
        const r = await da.normalize(data, method)
        this.result = r?.success ? r : null
        return r
      } catch (e) { this.error = e.message }
      finally { this.loading = false }
    },

    async regress(x, y) {
      this.loading = true; this.error = null
      try {
        const r = await da.regression(x, y)
        this.result = r?.success ? r : null
        return r
      } catch (e) { this.error = e.message }
      finally { this.loading = false }
    },

    async cluster(data, k) {
      this.loading = true; this.error = null
      try {
        const r = await da.clustering(data, k)
        this.result = r?.success ? r : null
        return r
      } catch (e) { this.error = e.message }
      finally { this.loading = false }
    },

    async summarize() {
      this.loading = true; this.error = null
      try {
        const r = await da.summarize()
        this.result = r?.success ? r : null
        return r
      } catch (e) { this.error = e.message }
      finally { this.loading = false }
    },

    async exportData(data, format) {
      try {
        return await da.export(data, format)
      } catch (e) { this.error = e.message }
    },

    clearResult() { this.result = null; this.error = null },
  },
})
