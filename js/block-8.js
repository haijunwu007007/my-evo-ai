
// ═══════════════════════════════════════════════════════
// i18n 国际化系统
// ═══════════════════════════════════════════════════════
var I18N = {
    current: localStorage.getItem('evo-locale') || 'zh',
    translations: {
        zh: {
            // 侧边栏
            'nav.dashboard': '监控面板', 'nav.agents': 'Agent管理', 'nav.workflows': '工作流编排',
            'nav.tasks': '任务中心', 'nav.memory': '记忆管理', 'nav.evolution': '进化中心',
            'nav.routines': 'Routines', 'nav.tools': '工具集成', 'nav.config': '配置中心',
            'nav.security': '安全治理', 'nav.perf': '性能监控', 'nav.alerts': '告警中心',
            'nav.logs': '日志中心', 'nav.backup': '容灾备份', 'nav.audit': '安全审计',
            'nav.users': '用户管理', 'nav.api': 'API管理', 'nav.settings': '系统设置',
            'nav.github': 'GitHub扫描', 'nav.scheduler': '调度配置', 'nav.reports': '报告中心',
            'nav.feedback': '用户反馈', 'nav.about': '关于系统',
            // 状态
            'status.online': '在线', 'status.offline': '离线', 'status.running': '运行中',
            'status.idle': '空闲', 'status.error': '异常',
            // 操作
            'btn.execute': '执行', 'btn.stop': '停止', 'btn.restart': '重启',
            'btn.configure': '配置', 'btn.delete': '删除', 'btn.save': '保存',
            'btn.cancel': '取消', 'btn.refresh': '刷新', 'btn.export': '导出',
            'btn.import': '导入', 'btn.search': '搜索',
            // 通用
            'common.modules': '模块', 'common.engines': '引擎', 'common.tasks': '任务',
            'common.events': '事件', 'common.pipelines': '管线', 'common.schedules': '调度',
            'common.total': '总计', 'common.active': '活跃', 'common.inactive': '未激活',
            'common.loading': '加载中...', 'common.noData': '暂无数据',
            'common.success': '操作成功', 'common.failed': '操作失败',
            'common.confirm': '确认', 'common.warning': '警告',
            // 实时推送
            'ws.connected': '实时连接已建立', 'ws.disconnected': '实时连接断开',
            'ws.reconnecting': '正在重新连接...', 'ws.moduleExecuted': '模块执行完成',
            'ws.taskCompleted': '任务完成', 'ws.alertTriggered': '告警触发',
            'ws.newEvent': '新事件',
        },
        en: {
            'nav.dashboard': 'Dashboard', 'nav.agents': 'Agents', 'nav.workflows': 'Workflows',
            'nav.tasks': 'Tasks', 'nav.memory': 'Memory', 'nav.evolution': 'Evolution',
            'nav.routines': 'Routines', 'nav.tools': 'Tools', 'nav.config': 'Config Center',
            'nav.security': 'Security', 'nav.perf': 'Performance', 'nav.alerts': 'Alerts',
            'nav.logs': 'Logs', 'nav.backup': 'Backup', 'nav.audit': 'Audit',
            'nav.users': 'Users', 'nav.api': 'API', 'nav.settings': 'Settings',
            'nav.github': 'GitHub Scan', 'nav.scheduler': 'Scheduler', 'nav.reports': 'Reports',
            'nav.feedback': 'Feedback', 'nav.about': 'About',
            'status.online': 'Online', 'status.offline': 'Offline', 'status.running': 'Running',
            'status.idle': 'Idle', 'status.error': 'Error',
            'btn.execute': 'Execute', 'btn.stop': 'Stop', 'btn.restart': 'Restart',
            'btn.configure': 'Configure', 'btn.delete': 'Delete', 'btn.save': 'Save',
            'btn.cancel': 'Cancel', 'btn.refresh': 'Refresh', 'btn.export': 'Export',
            'btn.import': 'Import', 'btn.search': 'Search',
            'common.modules': 'Modules', 'common.engines': 'Engines', 'common.tasks': 'Tasks',
            'common.events': 'Events', 'common.pipelines': 'Pipelines', 'common.schedules': 'Schedules',
            'common.total': 'Total', 'common.active': 'Active', 'common.inactive': 'Inactive',
            'common.loading': 'Loading...', 'common.noData': 'No Data',
            'common.success': 'Success', 'common.failed': 'Failed',
            'common.confirm': 'Confirm', 'common.warning': 'Warning',
            'ws.connected': 'Realtime Connected', 'ws.disconnected': 'Realtime Disconnected',
            'ws.reconnecting': 'Reconnecting...', 'ws.moduleExecuted': 'Module Executed',
            'ws.taskCompleted': 'Task Completed', 'ws.alertTriggered': 'Alert Triggered',
            'ws.newEvent': 'New Event',
        }
    },
    t(key) {
        return this.translations[this.current]?.[key] || this.translations['zh']?.[key] || key;
    },
    setLocale(lang) {
        this.current = lang;
        localStorage.setItem('evo-locale', lang);
        this.applyTranslations();
    },
    applyTranslations() {
        // 翻译所有带data-i18n属性的元素
        document.querySelectorAll('[data-i18n]').forEach(el => {
            var key = el.getAttribute('data-i18n');
            var text = this.t(key);
            if (text !== key) el.textContent = text;
        });
        // 翻译placeholder
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            var key = el.getAttribute('data-i18n-placeholder');
            var text = this.t(key);
            if (text !== key) el.placeholder = text;
        });
        // 更新语言按钮状态
        document.querySelectorAll('.i18n-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.lang === this.current);
        });
        // 更新页面标题
        document.title = this.current === 'zh' ? 'AUTO-EVO-AI V0.1' : 'AUTO-EVO-AI V0.1';
    }
};

// 语言切换器
function initI18NSwitcher() {
    var container = document.createElement('div');
    container.className = 'i18n-switcher';
    container.innerHTML = `
        <button class="i18n-btn ${I18N.current==='zh'?'active':''}" data-lang="zh" onclick="I18N.setLocale('zh')">中文</button>
        <button class="i18n-btn ${I18N.current==='en'?'active':''}" data-lang="en" onclick="I18N.setLocale('en')">EN</button>
    `;
    document.body.appendChild(container);
}

// ═══════════════════════════════════════════════════════
// WebSocket 实时推送增强
// ═══════════════════════════════════════════════════════
var WSRealtime = {
    ws: null,
    reconnectTimer: null,
    reconnectDelay: 3000,
    maxReconnectDelay: 30000,
    statusEl: null,
    
    init() {
        this.connect();
    },
    
    connect() {
        var protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        var API_PORT = 8765;
        var url = `${protocol}//127.0.0.1:${API_PORT}/ws/events`;
        
        try {
            this.ws = new WebSocket(url);
            this.updateStatus('connecting');
            
            this.ws.onopen = () => {
                console.log('[WS] Connected to', url);
                this.updateStatus('connected');
                this.reconnectDelay = 3000;
                this.showToast(I18N.t('ws.connected'), '', 'success');
            };
            
            this.ws.onmessage = (event) => {
                try {
                    var data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (e) {}
            };
            
            this.ws.onclose = () => {
                this.updateStatus('disconnected');
                this.scheduleReconnect();
            };
            
            this.ws.onerror = () => {
                this.updateStatus('disconnected');
            };
        } catch (e) {
            this.scheduleReconnect();
        }
    },
    
    scheduleReconnect() {
        if (this.reconnectTimer) return;
        this.showToast(I18N.t('ws.reconnecting'), '', 'warning');
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.maxReconnectDelay);
            this.connect();
        }, this.reconnectDelay);
    },
    
    handleMessage(data) {
        var type = data.type || data.event_type || '';
        switch(type) {
            case 'module_executed':
                this.showToast(I18N.t('ws.moduleExecuted'), data.module || data.name || '', 'info');
                break;
            case 'task_completed':
                this.showToast(I18N.t('ws.taskCompleted'), data.task_id || '', 'success');
                break;
            case 'alert_triggered':
                this.showToast(I18N.t('ws.alertTriggered'), data.message || '', 'error');
                break;
            case 'event':
                this.showToast(I18N.t('ws.newEvent'), data.channel || '', 'info');
                break;
            default:
                if (data.message) this.showToast('Notification', data.message, 'info');
        }
        // 触发自定义事件供页面逻辑监听
        window.dispatchEvent(new CustomEvent('evo-ws-message', { detail: data }));
    },
    
    updateStatus(state) {
        if (!this.statusEl) {
            this.statusEl = document.createElement('div');
            this.statusEl.className = 'ws-status-dot';
            this.statusEl.title = 'WebSocket';
            var header = document.querySelector('.header-title') || document.querySelector('h1') || document.body;
            header.appendChild(this.statusEl);
        }
        this.statusEl.className = `ws-status-dot ${state}`;
        this.statusEl.title = state === 'connected' ? 'Live' : state;
    },
    
    showToast(title, body, type) {
        var toast = document.createElement('div');
        toast.className = 'ws-toast';
        var colors = { success: '#22c55e', error: '#ef4444', warning: '#eab308', info: '#6366f1' };
        toast.style.borderColor = colors[type] || colors.info;
        toast.innerHTML = `<div class="ws-toast-title">${title}</div>${body ? `<div>${body}</div>` : ''}`;
        document.body.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add('show'));
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 500);
        }, 4000);
    },
    
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    },
    
    disconnect() {
        if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
        if (this.ws) this.ws.close();
    }
};

// ═══════════════════════════════════════════════════════
// PWA Service Worker 注册
// ═══════════════════════════════════════════════════════
function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js').then(reg => {
            console.log('[PWA] SW registered:', reg.scope);
            // 检查更新
            reg.addEventListener('updatefound', () => {
                var newWorker = reg.installing;
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'activated' && navigator.serviceWorker.controller) {
                        // 新版本已激活
                        console.log('[PWA] New version available');
                    }
                });
            });
        }).catch(err => {
            console.log('[PWA] SW registration failed:', err.message);
        });
    }
}

// ═══════════════════════════════════════════════════════
// 初始化
// ═══════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    // 注册PWA
    registerServiceWorker();
    
    // 初始化i18n（延迟1秒避免和Setup Wizard冲突）
    setTimeout(() => {
        initI18NSwitcher();
        I18N.applyTranslations();
    }, 2000);
    
    // 启动WebSocket实时推送（延迟3秒，等服务完全就绪）
    setTimeout(() => {
        WSRealtime.init();
    }, 3000);
});

// 在线/离线状态监听
window.addEventListener('online', () => {
    WSRealtime.connect();
    WSRealtime.showToast(I18N.t('status.online'), '', 'success');
});
window.addEventListener('offline', () => {
    WSRealtime.updateStatus('disconnected');
    WSRealtime.showToast(I18N.t('status.offline'), '', 'warning');
});

// Ensure WebSocket toast notifications work
if (typeof WSRealtime !== 'undefined' && WSRealtime.showToast) {
    var origToast = WSRealtime.showToast;
    WSRealtime.showToast = function(msg, title, type) {
        // Create visible toast in DOM
        var toast = document.createElement('div');
        toast.style.cssText = 'position:fixed;bottom:20px;right:20px;padding:14px 24px;border-radius:12px;color:#fff;font-size:14px;z-index:100000;max-width:360px;box-shadow:0 8px 30px rgba(0,0,0,0.3);transition:opacity 0.3s;';
        var colors = {info:'#6366f1',success:'#22c55e',warning:'#f59e0b',error:'#ef4444'};
        toast.style.background = colors[type] || colors.info;
        toast.textContent = (title ? title + ': ' : '') + msg;
        document.body.appendChild(toast);
        setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 4000);
    };
}

