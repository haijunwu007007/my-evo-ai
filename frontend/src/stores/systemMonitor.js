/**
 * AUTO-EVO-AI V0.1 — System Monitor 实时监控 Store
 * 支持 WebSocket 实时推送 + HTTP 轮询兜底
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
    ws: null,
    wsConnected: false,
    useWs: false,
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
    _pushMetrics(m) {
      this.metrics = m
      const ts = Date.now()
      this.cpuHistory.push({ time: ts, value: m.cpu_percent ?? 0 })
      if (this.cpuHistory.length > 120) this.cpuHistory = this.cpuHistory.slice(-120)
    },

    // ── WebSocket 模式 ──
    connectWs() {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) return
      const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
      const url = `${proto}//${location.host}/ws`
      try {
        this.ws = new WebSocket(url)
        this.ws.onopen = () => {
          this.wsConnected = true
          this.useWs = true
          // 订阅实时指标推送
          this._wsSend({ action: 'call', module: 'system_monitor', method: 'get_metrics' })
        }
        this.ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(ev.data)
            if (msg.type === 'result' && msg.data?.metrics) {
              this._pushMetrics(msg.data.metrics)
            } else if (msg.type === 'health_update') {
              // 健康广播包含模块指标
            } else if (msg.type === 'module_activity' && msg.data) {
              // 活动广播
            }
          } catch (_) { /* ignore parse errors */ }
        }
        this.ws.onclose = () => {
          this.wsConnected = false
          this.useWs = false
          // WS断开后降级为HTTP轮询
          if (this.intervalId) this.startPolling()
        }
        this.ws.onerror = () => {
          this.wsConnected = false
          this.useWs = false
        }
      } catch (_) {
        this.useWs = false
      }
    },

    _wsSend(obj) {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify(obj))
      }
    },

    disconnectWs() {
      if (this.ws) { try { this.ws.close() } catch(_) {}; this.ws = null }
      this.wsConnected = false
      this.useWs = false
    },

    // ── HTTP 轮询（WS兜底） ──
    async fetchMetrics() {
      this.loading = true; this.error = null
      try {
        const r = await sysmon.metrics()
        if (r?.success) this._pushMetrics(r.metrics)
      } catch (e) { this.error = e.message }
      finally { this.loading = false }
    },

    async fetchAlerts(severity) {
      try {
        const r = await sysmon.alerts(severity)
        if (r?.success) this.alerts = r.active || []
      } catch (e) { /* ignore */ }
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
      // 优先WebSocket
      this.connectWs()
      // WS未连上时用HTTP轮询
      if (!this.useWs) {
        this.fetchMetrics(); this.fetchAlerts(); this.fetchAlertRules()
        this.intervalId = setInterval(() => {
          this.fetchMetrics(); this.fetchAlerts()
        }, interval)
      } else {
        // WS模式下每5s发一次请求，后台会自动广播
        this.intervalId = setInterval(() => {
          this._wsSend({ action: 'call', module: 'system_monitor', method: 'get_metrics' })
        }, 5000)
      }
    },

    stopPolling() {
      if (this.intervalId) { clearInterval(this.intervalId); this.intervalId = null }
      this.disconnectWs()
    },
  },
})
