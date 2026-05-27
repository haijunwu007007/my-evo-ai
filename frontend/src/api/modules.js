/**
 * AUTO-EVO-AI V0.1 — 模块 API 封装
 * 所有模块通过统一的 /api/modules/{name}/execute 端点调用
 */
import api from './index'

function execute(name, action, params = {}) {
  return api.post(`/modules/${name}/execute`, { action, params })
}

// ─── System Monitor ───
export const sysmon = {
  metrics:      (p) => execute('system_monitor', 'get_metrics', p || {}),
  cpu:          ()  => execute('system_monitor', 'get_cpu'),
  memory:       ()  => execute('system_monitor', 'get_memory'),
  disk:         ()  => execute('system_monitor', 'get_disk'),
  network:      ()  => execute('system_monitor', 'get_network'),
  processes:    (l) => execute('system_monitor', 'get_processes', { limit: l || 20 }),
  alerts:       (s) => execute('system_monitor', 'get_alerts', s ? { severity: s } : {}),
  trend:        (m, n) => execute('system_monitor', 'get_trend', { metric: m || 'cpu_percent', minutes: n || 5 }),
  ackAlert:     (id) => execute('system_monitor', 'ack_alert', { alert_id: id }),
  alertRules:   ()  => execute('system_monitor', 'list_alert_rules'),
  addRule:      (r) => execute('system_monitor', 'add_alert_rule', r),
}

// ─── SSO Auth ───
export const sso = {
  status:       () => execute('sso_auth', 'status'),
  login:        (uid, un, attrs) => execute('sso_auth', 'login', { user_id: uid, username: un, attributes: attrs }),
  validate:     (t) => execute('sso_auth', 'validate', { token: t }),
  logout:       (t, uid) => execute('sso_auth', 'logout', { token: t, user_id: uid }),
  registerUser: (un, pw, roles) => execute('sso_auth', 'register_user', { username: un, password: pw, roles: roles || ['user'] }),
  authenticate: (un, pw) => execute('sso_auth', 'authenticate', { username: un, password: pw }),
  generateJwt:  (uid, role) => execute('sso_auth', 'generate_jwt', { user_id: uid, role: role || 'user' }),
  verifyJwt:    (t) => execute('sso_auth', 'verify_jwt', { token: t }),
  listSessions: (l) => execute('sso_auth', 'list_sessions', { limit: l || 50 }),
}

// ─── Data Analysis ───
export const da = {
  status:       () => execute('data_analysis', 'status'),
  describe:     (data) => execute('data_analysis', 'describe', { data }),
  correlation:  (x, y) => execute('data_analysis', 'correlation', { x, y }),
  outliers:     (data, m) => execute('data_analysis', 'outliers', { data, method: m || 'iqr' }),
  histogram:    (data, bins) => execute('data_analysis', 'histogram', { data, bins: bins || 10 }),
  normalize:    (data, m) => execute('data_analysis', 'normalize', { data, method: m || 'minmax' }),
  regression:   (x, y) => execute('data_analysis', 'regression', { x, y }),
  clustering:   (data, k) => execute('data_analysis', 'clustering', { data, k: k || 3 }),
  summarize:    () => execute('data_analysis', 'summarize'),
  export:       (data, fmt) => execute('data_analysis', 'export', { data, format: fmt || 'csv' }),
}

export default { sysmon, sso, da }
