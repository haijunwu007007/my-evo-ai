/**
 * AUTO-EVO-AI V0.1 — 模块 API 封装
 * 所有模块通过统一的 /api/modules/{name}/execute 端点调用
 */
import api from './index'

// ── 通用类型 ──
type Param = Record<string,any>
type Id = string|number

function execute(name: string, action: string, params: Param = {}): Promise<any> {
  return api.post(`/modules/${name}/execute`, { action, params }).then((r: any) => r.result || r)
}

// ─── System Monitor ───
export const sysmon = {
  metrics:      (p?: Param) => execute('system_monitor', 'get_metrics', p || {}),
  cpu:          ()  => execute('system_monitor', 'get_cpu'),
  memory:       ()  => execute('system_monitor', 'get_memory'),
  disk:         ()  => execute('system_monitor', 'get_disk'),
  network:      ()  => execute('system_monitor', 'get_network'),
  processes:    (l?: number) => execute('system_monitor', 'get_processes', { limit: l || 20 }),
  alerts:       (s?: string) => execute('system_monitor', 'get_alerts', s ? { severity: s } : {}),
  trend:        (m?: string, n?: number) => execute('system_monitor', 'get_trend', { metric: m || 'cpu_percent', minutes: n || 5 }),
  ackAlert:     (id: Id) => execute('system_monitor', 'ack_alert', { alert_id: id }),
  alertRules:   ()  => execute('system_monitor', 'list_alert_rules'),
  addRule:      (r?: Param) => execute('system_monitor', 'add_alert_rule', r),
}

// ─── 模块管理 ───
export function listModules(p?: Param) { return api.get('/modules/list', { params: p }).then((r: any) => (r.data||r).modules||r) }
export function getCategories(s?: Param) { return api.get('/modules/categories', { params: s }).then((r: any) => r.data||r) }
export function rescanModules(m?: string, n?: string) { return api.post('/modules/rescan', { pattern: m, name: n }).then((r: any) => r.result||r) }

// ─── 调度器 ───
export function getScheduler(l?: number) { return api.get('/scheduler/list', { params: { limit: l||100 } }).then((r: any) => r.data||r) }
export function toggleScheduler(id: Id) { return api.post(`/scheduler/${id}/toggle`).then((r: any) => r.data||r) }
export function triggerScheduler(id: Id) { return api.post(`/scheduler/${id}/trigger`).then((r: any) => r.data||r) }
export function removeScheduler(id: Id) { return api.delete(`/scheduler/${id}`).then((r: any) => r.data||r) }

// ─── 事件引擎 ───
export function getEventsStats() { return api.get('/events/stats').then((r: any) => r.data||r) }
export function getEventsRules() { return api.get('/events/rules').then((r: any) => r.data||r) }
export function createEventRule(t?: Param) { return api.post('/events/rules', t).then((r: any) => r.data||r) }
export function updateEventRule(id: Id, t?: Param) { return api.put(`/events/rules/${id}`, t).then((r: any) => r.data||r) }
export function deleteEventRule(id: Id) { return api.delete(`/events/rules/${id}`).then((r: any) => r.data||r) }

// ─── 管线引擎 ───
export function getPipelines(params?: Param) { return api.get('/pipelines/list', { params }).then((r: any) => r.data||r) }
export function createPipeline(t?: Param) { return api.post('/pipelines/create', t).then((r: any) => r.data||r) }
export function executePipeline(id: Id) { return api.post(`/pipelines/${id}/execute`).then((r: any) => r.data||r) }
export function deletePipeline(id: Id) { return api.delete(`/pipelines/${id}`).then((r: any) => r.data||r) }

// ─── 任务队列 ───
export function getQueueStats() { return api.get('/queue/stats').then((r: any) => r.data||r) }
export function getQueueTasks(params?: Param) { return api.get('/queue/list', { params }).then((r: any) => r.data||r) }
export function retryQueueTask(id: Id) { return api.post(`/queue/${id}/retry`).then((r: any) => r.data||r) }
export function cancelQueueTask(id: Id) { return api.post(`/queue/${id}/cancel`).then((r: any) => r.data||r) }

// ─── 安全中心 ───
export function getSecurityEvents(params?: Param) { return api.get('/security/events', { params }).then((r: any) => r.data||r) }
export function getSecurityStats() { return api.get('/security/stats').then((r: any) => r.data||r) }

// ─── SSO / Gitea ───
export function loginSSO(username: string, password: string, roles?: string[]) { return api.post('/auth/login', { username, password, roles }).then((r: any) => r.data||r) }
export function registerSSO(username: string, password: string, roles?: string[]) { return api.post('/auth/register', { username, password, roles }).then((r: any) => r.data||r) }
export function getUsers() { return api.get('/auth/users').then((r: any) => r.data||r) }

// ─── 数据分析 ───
export function getDataAnalysis(params?: Param) { return api.get('/data/analysis', { params }).then((r: any) => r.data||r) }

// ─── 运维管理 ───
export function getOperations(params?: Param) { return api.get('/ops/status', { params }).then((r: any) => r.data||r) }

// ─── 系统设置 ───
export function getSystemConfig() { return api.get('/config').then((r: any) => r.data||r) }
export function updateSystemConfig(key: string, value: any) { return api.put('/config', { key, value }).then((r: any) => r.data||r) }

// ─── Webhook ───
export function webhookEvents(params?: Param) { return api.get('/webhook/github/events', { params }).then((r: any) => r.data||r) }
export function webhookStats() { return api.get('/webhook/github/stats').then((r: any) => r.data||r) }
export function clearWebhooks() { return api.delete('/webhook/github/events').then((r: any) => r.data||r) }

// ─── 通知 ───
export function notifyStats() { return api.get('/notify/stats').then((r: any) => r.data||r) }
export function notifyHistory(params?: Param) { return api.get('/notify/history', { params }).then((r: any) => r.data||r) }
export function sendNotify(channel: string, msg_type: string, content: string) { return api.post('/notify/send', { channel, msg_type, content }).then((r: any) => r.data||r) }
export function testNotifyChannel(channel: string) { return api.post(`/notify/test/${channel}`).then((r: any) => r.data||r) }

// ─── CDC ───
export function cdcStatus() { return api.get('/cdc/status').then((r: any) => r.data||r) }
export function cdcStart() { return api.post('/cdc/start').then((r: any) => r.data||r) }
export function cdcStop() { return api.post('/cdc/stop').then((r: any) => r.data||r) }
export function cdcTables() { return api.get('/cdc/tables').then((r: any) => r.data||r) }

// ─── AI Chat ───
export function aiChat(messages: any[], model?: string) { return api.post('/ai/chat', { messages, model }).then((r: any) => r.data||r) }
export function aiProviders() { return api.get('/ai/providers').then((r: any) => r.data||r) }
export function aiModels() { return api.get('/ai/models').then((r: any) => r.data||r) }
