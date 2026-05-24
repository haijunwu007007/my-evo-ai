


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

