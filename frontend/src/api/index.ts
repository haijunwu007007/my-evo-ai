import axios, { AxiosInstance } from 'axios'

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// 响应拦截器
api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg: string = err.response?.data?.error || err.message || '请求失败'
    console.error('[API Error]', msg)
    return Promise.reject(err)
  }
)

// ─── 系统相关 ───
export const getSystemStatus = (): Promise<any> => api.get('/status')
export const getSystemMetrics = (): Promise<any> => api.get('/system/metrics')
export const getAuthStatus = (): Promise<any> => api.get('/auth/status')
export const getDiagnosis = (): Promise<any> => api.get('/diagnosis/system')
export const getDiagnosisModules = (): Promise<any> => api.get('/diagnosis/modules')

// ─── 配置 ───
export const getConfig = (): Promise<any> => api.get('/config')
export const getConfigEntries = (): Promise<any> => api.get('/config/entries')
export const setConfig = (key: string, value: any): Promise<any> => api.put(`/config/${key}`, { value })
export const deleteConfig = (key: string): Promise<any> => api.delete(`/config/${key}`)
export const reloadConfig = (): Promise<any> => api.post('/config/reload')

// ─── 调度器 ───
export const getSchedulerStatus = (): Promise<any> => api.get('/scheduler/status')
export const getSchedulerTasks = (): Promise<any> => api.get('/scheduler/tasks')
export const createSchedulerTask = (data: any): Promise<any> => api.post('/scheduler/tasks', data)
export const toggleSchedulerTask = (id: string|number): Promise<any> => api.post(`/scheduler/tasks/${id}/toggle`)
export const deleteSchedulerTask = (id: string|number): Promise<any> => api.delete(`/scheduler/tasks/${id}`)
export const triggerSchedulerTask = (id: string|number): Promise<any> => api.post(`/scheduler/tasks/${id}/trigger`)

// ─── 事件 ───
export const getEventsStats = (): Promise<any> => api.get('/events/stats')
export const getEventsRules = (): Promise<any> => api.get('/events/rules')
export const createEventRule = (data: any): Promise<any> => api.post('/events/rules', data)
export const deleteEventRule = (id: string|number): Promise<any> => api.delete(`/events/rules/${id}`)

// ─── 管线 ───
export const getPipelines = (): Promise<any> => api.get('/pipelines')
export const createPipeline = (data: any): Promise<any> => api.post('/pipelines', data)
export const executePipeline = (id: string|number): Promise<any> => api.post(`/pipelines/${id}/execute`)
export const deletePipeline = (id: string|number): Promise<any> => api.delete(`/pipelines/${id}`)

// ─── 队列 ───
export const getQueueStats = (): Promise<any> => api.get('/queue/stats')
export const getQueueTasks = (limit = 30): Promise<any> => api.get('/queue/tasks', { params: { limit } })
export const enqueueTask = (data: any): Promise<any> => api.post('/queue/tasks', data)
export const cancelTask = (id: string|number): Promise<any> => api.post(`/queue/tasks/${id}/cancel`)
export const retryTask = (id: string|number): Promise<any> => api.post(`/queue/tasks/${id}/retry`)

// ─── 协调中心 ───
export const getCoordinatorStatus = (): Promise<any> => api.get('/coordinator/status')
export const getCoordinatorCapabilities = (): Promise<any> => api.get('/coordinator/capabilities')
export const executeTask = (task: any): Promise<any> => api.post('/coordinator/execute', { task })

// ─── 模板 ───
export const getTemplates = (): Promise<any> => api.get('/templates')
export const applyTemplate = (id: string|number): Promise<any> => api.post(`/templates/${id}/apply`)

// ─── 模块 ───
export const getModulesCategories = (): Promise<any> => api.get('/modules/categories')
export const rescanModules = (): Promise<any> => api.post('/modules/rescan')

// ─── 监控 ───
export const getMonitorRealtime = (): Promise<any> => api.get('/monitor/realtime')
export const getWsStatus = (): Promise<any> => api.get('/ws/status')

// ─── 安全 ───
export const login = (apiKey: string): Promise<any> => api.post('/auth/login', { api_key: apiKey })
export const getSecurityStatus = (): Promise<any> => api.get('/security/status')

// ─── Webhook ───
export const webhookEvents = (limit = 50): Promise<any> => api.get('/webhook/github/events', { params: { limit } })
export const webhookStats = (): Promise<any> => api.get('/webhook/github/stats')
export const clearWebhooks = (): Promise<any> => api.delete('/webhook/github/events')

// ─── 企业通知 ───
export const notifyStatus = (): Promise<any> => api.get('/notify/status')
export const notifySend = (channel: string, data: any): Promise<any> => api.post('/notify/send', { channel, ...data })
export const notifyTest = (channel: string): Promise<any> => api.post('/notify/test', { channel })
export const notifyConfig = (): Promise<any> => api.get('/notify/config')
export const notifyUpdateConfig = (data: any): Promise<any> => api.put('/notify/config', data)

// ─── CDC ───
export const cdcStatus = (): Promise<any> => api.get('/cdc/status')
export const cdcTables = (): Promise<any> => api.get('/cdc/tables')
export const cdcStart = (config?: any): Promise<any> => api.post('/cdc/start', config || {})
export const cdcStop = (): Promise<any> => api.post('/cdc/stop')
export const cdcEvents = (limit = 50): Promise<any> => api.get('/cdc/events', { params: { limit } })

export default api
