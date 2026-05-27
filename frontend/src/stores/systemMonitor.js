/**
 * AUTO-EVO-AI V0.1 — System Monitor 实时监控 Store
 * 每 5s 自动拉取系统指标，支持告警管理
 */
import { defineStore } from 'pinia'
import { sysmon } from '../api/modules'

export const useSystemMonitorStore = defineStore('systemMonitor', {
  state: () => ({
    metrics: null,
    cpuHistory: [],
    alerts: [],
    alertRules: [],
    loading: false,
    error: null,
    intervalId: null,
  }),

  getters: {
    cpuPercent:          (s) => s.metrics?.cpu_percent ?? 0,
    memoryPercent:       (s) => s.metrics?.memory_percent ?? 0,
    diskPercent:         (s) => s.metrics?.disk_percent ?? 0,
    processCount:        (s) => s.metrics?.process_count ?? 0,
    activeAlertCount:    (s) => s.alerts.filter(a => !a.acked).length,
    criticalAlertCount:  (s) => s.alerts.filter(a => a.severity === 'critical' && !a.acked).length,
  },

  actions: {
    async fetchMetrics() {
      this.loading = true; this.error = null
      try {
        const r = await sysmon.metrics()
        if (r?.success) {
          this.metrics = r.metrics
          const ts = Date.now()
          this.cpuHistory.push({ time: ts, value: r.metrics.cpu_percent ?? 0 })
          if (this.cpuHistory.length > 120) this.cpuHistory = this.cpuHistory.slice(-120)
        }
      } catch (e) { this.error = e.message }
      finally { this.loading = false }
    },

    async fetchAlerts(severity) {
      try {
        const r = await sysmon.alerts(severity)
        if (r?.success) this.alerts = r.active || []
      } catch (e) { /* ignore polling errors */ }
    },

    async fetchAlertRules() {
      try {
        const r = await sysmon.alertRules()
        if (r?.success) this.alertRules = r.rules || []
      } catch (e) { /* ignore */ }
    },

    async ackAlert(alertId) {
      const r = await sysmon.ackAlert(alertId)
      if (r?.success) await this.fetchAlerts()
      return r
    },

    async addRule(rule) {
      const r = await sysmon.addRule(rule)
      if (r?.success) await this.fetchAlertRules()
      return r
    },

    startPolling(interval = 5000) {
      this.stopPolling()
      this.fetchMetrics(); this.fetchAlerts(); this.fetchAlertRules()
      this.intervalId = setInterval(() => {
        this.fetchMetrics(); this.fetchAlerts()
      }, interval)
    },

    stopPolling() {
      if (this.intervalId) { clearInterval(this.intervalId); this.intervalId = null }
    },
  },
})
