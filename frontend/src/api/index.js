import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// 响应拦截器
api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.error || err.message || '请求失败'
    console.error('[API Error]', msg)
    return Promise.reject(err)
  }
)

// ─── 系统相关 ───
export const getSystemStatus = () => api.get('/status')
export const getSystemMetrics = () => api.get('/system/metrics')
export const getAuthStatus = () => api.get('/auth/status')
export const getDiagnosis = () => api.get('/diagnosis/system')
export const getDiagnosisModules = () => api.get('/diagnosis/modules')

// ─── 配置 ───
export const getConfig = () => api.get('/config')
export const getConfigEntries = () => api.get('/config/entries')
export const setConfig = (key, value) => api.put(`/config/${key}`, { value })
export const deleteConfig = (key) => api.delete(`/config/${key}`)
export const reloadConfig = () => api.post('/config/reload')

// ─── 调度器 ───
export const getSchedulerStatus = () => api.get('/scheduler/status')
export const getSchedulerTasks = () => api.get('/scheduler/tasks')
export const createSchedulerTask = (data) => api.post('/scheduler/tasks', data)
export const toggleSchedulerTask = (id) => api.post(`/scheduler/tasks/${id}/toggle`)
export const deleteSchedulerTask = (id) => api.delete(`/scheduler/tasks/${id}`)
export const triggerSchedulerTask = (id) => api.post(`/scheduler/tasks/${id}/trigger`)

// ─── 事件 ───
export const getEventsStats = () => api.get('/events/stats')
export const getEventsRules = () => api.get('/events/rules')
export const createEventRule = (data) => api.post('/events/rules', data)
export const deleteEventRule = (id) => api.delete(`/events/rules/${id}`)

// ─── 管线 ───
export const getPipelines = () => api.get('/pipelines')
export const createPipeline = (data) => api.post('/pipelines', data)
export const executePipeline = (id) => api.post(`/pipelines/${id}/execute`)
export const deletePipeline = (id) => api.delete(`/pipelines/${id}`)

// ─── 队列 ───
export const getQueueStats = () => api.get('/queue/stats')
export const getQueueTasks = (limit = 30) => api.get('/queue/tasks', { params: { limit } })
export const enqueueTask = (data) => api.post('/queue/tasks', data)
export const cancelTask = (id) => api.post(`/queue/tasks/${id}/cancel`)
export const retryTask = (id) => api.post(`/queue/tasks/${id}/retry`)

// ─── 协调中心 ───
export const getCoordinatorStatus = () => api.get('/coordinator/status')
export const getCoordinatorCapabilities = () => api.get('/coordinator/capabilities')
export const executeTask = (task) => api.post('/coordinator/execute', { task })

// ─── 模板 ───
export const getTemplates = () => api.get('/templates')
export const applyTemplate = (id) => api.post(`/templates/${id}/apply`)

// ─── 模块 ───
export const getModulesCategories = () => api.get('/modules/categories')
export const rescanModules = () => api.post('/modules/rescan')

// ─── 监控 ───
export const getMonitorRealtime = () => api.get('/monitor/realtime')
export const getWsStatus = () => api.get('/ws/status')

// ─── 安全 ───
export const login = (apiKey) => api.post('/auth/login', { api_key: apiKey })
export const getSecurityStatus = () => api.get('/security/status')

export default api
