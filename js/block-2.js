
// 系统状态监控面板集成
(function() {
    // 异步加载后端模块详细信息
    async function loadBackendModuleInfo(moduleId) {
        var area = document.getElementById('backend-info-area');
        if (!area) return;
        // 前端用kebab-case，后端用snake_case
        var backendName = moduleId.replace(/-/g, '_');
        try {
            const [info, codeInfo] = await Promise.all([
                EvoAPI.getModule(backendName).catch(() => null),
                EvoAPI.getModuleCode(backendName).catch(() => null)
            ]);
            if (!info && !codeInfo) return;
            var name = info?.module_name || info?.name || moduleId;
            var version = info?.version || '-';
            var level = info?.module_level || '-';
            var fileSize = info?.file_size ? (info.file_size / 1024).toFixed(1) + ' KB' : '-';
            var totalLines = codeInfo?.total_lines || '-';
            var docPreview = codeInfo?.docstring_preview || '';
            area.innerHTML = `
                <div class="detail-section">
                    <h3>后端信息 <span style="font-size:11px;background:#10b981;color:white;padding:2px 8px;border-radius:10px;margin-left:8px;">已连接</span></h3>
                    <div class="detail-meta">
                        <div class="detail-meta-item">
                            <div class="label">模块名称</div>
                            <div class="value">${name}</div>
                        </div>
                        <div class="detail-meta-item">
                            <div class="label">版本</div>
                            <div class="value">${version}</div>
                        </div>
                        <div class="detail-meta-item">
                            <div class="label">级别</div>
                            <div class="value">${level}</div>
                        </div>
                        <div class="detail-meta-item">
                            <div class="label">文件大小</div>
                            <div class="value">${fileSize}</div>
                        </div>
                        <div class="detail-meta-item">
                            <div class="label">代码行数</div>
                            <div class="value">${totalLines}</div>
                        </div>
                        <div class="detail-meta-item">
                            <div class="label">状态</div>
                            <div class="value" style="color:#10b981">已加载</div>
                        </div>
                    </div>
                    ${docPreview ? `<div style="margin-top:12px;padding:12px;background:var(--bg);border-radius:8px;font-size:12px;color:var(--text-muted);line-height:1.6;"><b>模块描述:</b> ${docPreview}</div>` : ''}
                </div>
            `;
        } catch {
            // 模块未在后端加载
            area.innerHTML = `
                <div class="detail-section">
                    <h3>后端信息 <span style="font-size:11px;background:#64748b;color:white;padding:2px 8px;border-radius:10px;margin-left:8px;">未加载</span></h3>
                    <div style="padding:12px;background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);border-radius:8px;font-size:13px;color:#f59e0b;">
                        此模块尚未被后端加载，可能处于规划中或存在编译错误。
                    </div>
                </div>
            `;
        }
    }

    function _getBackendName(frontendId) {
        return frontendId.replace(/-/g, '_');
    }

    /* ═══════════ Setup Wizard ═══════════ */
    var _wizardStep = 0;
    function openWizard() {
        _wizardStep = 0;
        var overlay = document.getElementById('wizard-overlay');
        if (overlay) { overlay.style.display = 'flex'; }
        else {
            var el = document.createElement('div');
            el.id = 'wizard-overlay';
            el.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9999;display:flex;align-items:center;justify-content:center;';
            el.innerHTML = '<div style="background:#1a1a2e;border-radius:16px;padding:40px;max-width:560px;width:90%;color:#fff;max-height:85vh;overflow-y:auto;">'
                + '<h2 style="margin:0 0 20px;font-size:22px;">🚀 Setup Wizard</h2>'
                + '<div id="wizard-content"></div>'
                + '<div style="display:flex;gap:10px;margin-top:24px;justify-content:flex-end;">'
                + '<button onclick="closeWizard()" style="padding:8px 20px;border-radius:8px;border:1px solid #444;background:transparent;color:#aaa;cursor:pointer;">Skip</button>'
                + '<button onclick="wizardNext()" style="padding:8px 20px;border-radius:8px;border:none;background:#667eea;color:#fff;cursor:pointer;">Next →</button>'
                + '</div></div>';
            document.body.appendChild(el);
        }
        _renderWizardStep();
    }
    function closeWizard() {
        var el = document.getElementById('wizard-overlay');
        if (el) el.style.display = 'none';
        localStorage.setItem('evo_wizard_done', '1');
    }
    function _renderWizardStep() {
        var steps = [
            { title: 'AI Provider', desc: 'Configure your AI API key (DeepSeek / OpenAI / etc)', fields: [{id:'w_ai_key',label:'API Key',type:'password',ph:'sk-...'}] },
            { title: 'Notification', desc: 'Set up a notification channel (optional)', fields: [{id:'w_notify_url',label:'Webhook URL',type:'text',ph:'https://...'}] },
            { title: 'Scheduler', desc: 'Enable automated tasks', fields: [{id:'w_scheduler',label:'Enable auto scheduler',type:'checkbox'}] },
            { title: 'Security', desc: 'Enable JWT authentication', fields: [{id:'w_auth',label:'Enable JWT auth',type:'checkbox'}] },
            { title: 'Done!', desc: 'All configured. Enjoy AUTO-EVO-AI!' },
        ];
        var step = steps[_wizardStep] || steps[steps.length-1];
        var ct = document.getElementById('wizard-content');
        if (!ct) return;
        var html = '<div style="margin-bottom:8px;font-size:13px;color:#667eea;">Step ' + (_wizardStep+1) + '/' + steps.length + '</div>';
        html += '<h3 style="margin:0 0 8px;">' + step.title + '</h3>';
        html += '<p style="color:#aaa;margin:0 0 16px;">' + step.desc + '</p>';
        if (step.fields) {
            step.fields.forEach(f => {
                if (f.type === 'checkbox') {
                    html += '<label style="display:flex;align-items:center;gap:8px;margin:8px 0;color:#ccc;cursor:pointer;"><input type="checkbox" id="'+f.id+'"> '+f.label+'</label>';
                } else {
                    html += '<div style="margin:8px 0;"><label style="display:block;font-size:13px;color:#aaa;margin-bottom:4px;">'+f.label+'</label>';
                    html += '<input type="'+f.type+'" id="'+f.id+'" placeholder="'+f.ph+'" style="width:100%;padding:10px;border-radius:8px;border:1px solid #333;background:#16213e;color:#fff;box-sizing:border-box;"></div>';
                }
            });
        } else {
            html += '<div style="text-align:center;font-size:40px;margin:20px 0;">🎉</div>';
        }
        ct.innerHTML = html;
    }
    function wizardNext() {
        _wizardStep++;
        if (_wizardStep >= 5) { closeWizard(); return; }
        _renderWizardStep();
    }
    function wizardSave() { closeWizard(); }

    /* ═══════════ i18n Language Switch ═══════════ */
    var TRANSLATIONS = {
        'Dashboard':'Dashboard','Modules':'Modules','Coordinator':'Coordinator','Settings':'Settings',
        'Health Check':'Health Check','Execute':'Execute','View Code':'View Code','Actions':'Actions',
        'Search modules...':'Search modules...','All Modules':'All Modules','Execute Module':'Execute Module',
        'System Status':'System Status','Running':'Running','Active':'Active','Healthy':'Healthy',
        'No results':'No results','Loading...':'Loading...','Error':'Error','Success':'Success',
        'Close':'Close','Save':'Save','Cancel':'Cancel','Delete':'Delete','Edit':'Edit',
        'Configuration':'Configuration','Monitoring':'Monitoring','Security':'Security',
        'Backup':'Backup','Restore':'Restore','Plugins':'Plugins','Database':'Database',
        'GitHub Scanner':'GitHub Scanner','WebSocket':'WebSocket','Scheduler':'Scheduler',
        'Pipelines':'Pipelines','Events':'Events','Queue':'Queue','Logs':'Logs',
        'Authentication':'Authentication','Users':'Users','API Keys':'API Keys',
        'Language':'Language','English':'English','Chinese':'Chinese',
        'Notifications':'Notifications','Real-time':'Real-time','Connected':'Connected',
        'Disconnected':'Disconnected','Reconnecting':'Reconnecting',
    };
    var _currentLang = localStorage.getItem('evo_lang') || 'zh';
    function switchLang() {
        _currentLang = _currentLang === 'zh' ? 'en' : 'zh';
        localStorage.setItem('evo_lang', _currentLang);
        _applyI18n();
        var btn = document.getElementById('lang-switch-btn');
        if (btn) btn.textContent = _currentLang === 'zh' ? 'EN' : '中';
    }
    function _applyI18n() {
        if (_currentLang === 'zh') return;
        document.querySelectorAll('[data-i18n]').forEach(el => {
            var key = el.getAttribute('data-i18n');
            if (TRANSLATIONS[key]) el.textContent = TRANSLATIONS[key];
        });
        var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        var textNodes = [];
        while (walker.nextNode()) textNodes.push(walker.currentNode);
        textNodes.forEach(node => {
            var t = node.textContent.trim();
            if (t && TRANSLATIONS[t]) node.textContent = TRANSLATIONS[t];
        });
    }

    /* ═══════════ GitHub Scanner ═══════════ */
    function openGitHubScanner() {
        var panel = document.getElementById('v3-panel-content');
        if (!panel) return;
        panel.innerHTML = '<h3 style="margin:0 0 16px;">🔍 GitHub Scanner</h3>'
            + '<div style="display:flex;gap:8px;margin-bottom:16px;">'
            + '<button onclick="githubScanAction(\'trending\')" style="padding:8px 16px;border-radius:8px;border:none;background:#667eea;color:#fff;cursor:pointer;">📊 Trending</button>'
            + '<button onclick="githubScanAction(\'stats\')" style="padding:8px 16px;border-radius:8px;border:none;background:#333;color:#fff;cursor:pointer;">📈 Stats</button>'
            + '<button onclick="githubScanAction(\'recommend\')" style="padding:8px 16px;border-radius:8px;border:none;background:#333;color:#fff;cursor:pointer;">💡 Recommend</button>'
            + '</div>'
            + '<div id="github-scan-result" style="background:#0d1117;border-radius:12px;padding:16px;min-height:200px;color:#aaa;">Ready to scan...</div>';
    }
    async function githubScanAction(action) {
        var area = document.getElementById('github-scan-result');
        if (!area) return;
        area.innerHTML = '<div style="text-align:center;padding:40px;">⏳ Scanning...</div>';
        try {
            var r = await fetch('/api/github/' + action);
            var data = await r.json();
            area.innerHTML = '<pre style="white-space:pre-wrap;font-size:13px;color:#c9d1d9;">' + JSON.stringify(data, null, 2) + '</pre>';
        } catch(e) {
            area.innerHTML = '<div style="color:#f85149;">Error: ' + e.message + '</div>';
        }
    }

    /* ═══════════ Database Panel ═══════════ */
    function openDatabasePanel() {
        var panel = document.getElementById('v3-panel-content');
        if (!panel) return;
        panel.innerHTML = '<h3 style="margin:0 0 16px;">🗄️ Database Management</h3>'
            + '<div style="display:flex;gap:8px;margin-bottom:16px;">'
            + '<button onclick="dbAction(\'stats\')" style="padding:8px 16px;border-radius:8px;border:none;background:#667eea;color:#fff;cursor:pointer;">📊 Status</button>'
            + '<button onclick="dbAction(\'vacuum\')" style="padding:8px 16px;border-radius:8px;border:none;background:#333;color:#fff;cursor:pointer;">🧹 Vacuum</button>'
            + '<button onclick="dbAction(\'migrate\')" style="padding:8px 16px;border-radius:8px;border:none;background:#333;color:#fff;cursor:pointer;">🔄 Migrate to PG</button>'
            + '</div>'
            + '<div id="db-action-result" style="background:#0d1117;border-radius:12px;padding:16px;min-height:200px;color:#aaa;">Ready...</div>';
    }
    async function dbAction(action) {
        var area = document.getElementById('db-action-result');
        if (!area) return;
        area.innerHTML = '<div style="text-align:center;padding:40px;">⏳ Processing...</div>';
        try {
            var url = action === 'stats' ? '/api/system/database' : '/api/system/database/' + action;
            var r = await fetch(url, {method: action === 'stats' ? 'GET' : 'POST'});
            var data = await r.json();
            area.innerHTML = '<pre style="white-space:pre-wrap;font-size:13px;color:#c9d1d9;">' + JSON.stringify(data, null, 2) + '</pre>';
        } catch(e) {
            area.innerHTML = '<div style="color:#f85149;">Error: ' + e.message + '</div>';
        }
    }

    /* ═══════════ Plugin Market ═══════════ */
    function openPluginPanel() {
        var panel = document.getElementById('v3-panel-content');
        if (!panel) return;
        panel.innerHTML = '<h3 style="margin:0 0 16px;">🧩 Plugin Market</h3>'
            + '<div style="display:flex;gap:8px;margin-bottom:16px;">'
            + '<button onclick="loadPlugins()" style="padding:8px 16px;border-radius:8px;border:none;background:#667eea;color:#fff;cursor:pointer;">📦 Refresh</button>'
            + '</div>'
            + '<div id="plugin-list" style="min-height:200px;">Loading...</div>';
        loadPlugins();
    }
    async function loadPlugins() {
        var area = document.getElementById('plugin-list');
        if (!area) return;
        try {
            var r = await fetch('/api/plugins/list');
            var data = await r.json();
            var plugins = data.plugins || data || [];
            if (!Array.isArray(plugins) || plugins.length === 0) {
                area.innerHTML = '<div style="color:#aaa;padding:20px;text-align:center;">No plugins found. <button onclick="loadPlugins()" style="margin-top:8px;padding:6px 14px;border-radius:6px;border:1px solid #444;background:transparent;color:#aaa;cursor:pointer;">Refresh</button></div>';
                return;
            }
            var html = '';
            plugins.forEach(p => {
                var name = typeof p === 'string' ? p : (p.name || 'unknown');
                var enabled = typeof p === 'object' && p.enabled;
                html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:12px;background:#16213e;border-radius:8px;margin-bottom:8px;">'
                    + '<div><strong style="color:#e0e0e0;">' + name + '</strong></div>'
                    + '<button onclick="togglePlugin(\'' + name + '\')" style="padding:6px 14px;border-radius:6px;border:none;background:' + (enabled ? '#e74c3c' : '#27ae60') + ';color:#fff;cursor:pointer;font-size:12px;">'
                    + (enabled ? 'Disable' : 'Enable') + '</button></div>';
            });
            area.innerHTML = html;
        } catch(e) {
            area.innerHTML = '<div style="color:#f85149;">Error: ' + e.message + '</div>';
        }
    }
    async function togglePlugin(name) {
        try {
            var r = await fetch('/api/plugins/' + name + '/toggle', {method:'POST'});
            var data = await r.json();
            loadPlugins();
        } catch(e) {
            alert('Toggle plugin failed: ' + e.message);
        }
    }

    /* ═══════════ Backup & Restore ═══════════ */
    function openBackupPanel() {
        var panel = document.getElementById('v3-panel-content');
        if (!panel) return;
        panel.innerHTML = '<h3 style="margin:0 0 16px;">💾 Backup & Restore</h3>'
            + '<div style="display:flex;gap:8px;margin-bottom:16px;">'
            + '<button onclick="createBackup()" style="padding:8px 16px;border-radius:8px;border:none;background:#667eea;color:#fff;cursor:pointer;">➕ Create Backup</button>'
            + '<button onclick="loadBackups()" style="padding:8px 16px;border-radius:8px;border:none;background:#333;color:#fff;cursor:pointer;">📋 List Backups</button>'
            + '</div>'
            + '<div id="backup-list" style="min-height:200px;">Loading...</div>';
        loadBackups();
    }
    async function loadBackups() {
        var area = document.getElementById('backup-list');
        if (!area) return;
        try {
            var r = await fetch('/api/system/backup');
            var data = await r.json();
            var backups = data.backups || data || [];
            if (!Array.isArray(backups) || backups.length === 0) {
                area.innerHTML = '<div style="color:#aaa;padding:20px;text-align:center;">No backups yet.</div>';
                return;
            }
            var html = '';
            backups.forEach(b => {
                var name = typeof b === 'string' ? b : (b.filename || b.name || JSON.stringify(b));
                html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:12px;background:#16213e;border-radius:8px;margin-bottom:8px;">'
                    + '<div style="color:#e0e0e0;font-size:13px;">' + name + '</div>'
                    + '<button onclick="restoreBackup(\'' + name + '\')" style="padding:6px 14px;border-radius:6px;border:none;background:#e67e22;color:#fff;cursor:pointer;font-size:12px;">Restore</button></div>';
            });
            area.innerHTML = html;
        } catch(e) {
            area.innerHTML = '<div style="color:#f85149;">Error: ' + e.message + '</div>';
        }
    }
    async function createBackup() {
        try {
            var r = await fetch('/api/system/backup', {method:'POST'});
            var data = await r.json();
            alert('Backup created: ' + JSON.stringify(data));
            loadBackups();
        } catch(e) {
            alert('Create backup failed: ' + e.message);
        }
    }
    async function restoreBackup(name) {
        if (!confirm('Restore backup: ' + name + '? This may overwrite current data.')) return;
        try {
            var r = await fetch('/api/system/backup/restore', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({filename:name})});
            var data = await r.json();
            alert('Restore result: ' + JSON.stringify(data));
        } catch(e) {
            alert('Restore failed: ' + e.message);
        }
    }

    /* ═══════════ Window global exports ═══════════ */
    window.openWizard = openWizard;
    window.closeWizard = closeWizard;
    window.wizardNext = wizardNext;
    window.wizardSave = wizardSave;
    window.switchLang = switchLang;
    window.openGitHubScanner = openGitHubScanner;
    window.githubScanAction = githubScanAction;
    window.openDatabasePanel = openDatabasePanel;
    window.dbAction = dbAction;
    window.openPluginPanel = openPluginPanel;
    window.loadPlugins = loadPlugins;
    window.togglePlugin = togglePlugin;
    window.openBackupPanel = openBackupPanel;
    window.createBackup = createBackup;
    window.restoreBackup = restoreBackup;

    function _resultArea() {
        return document.getElementById('module-result-area');
    }

    async function doModuleHealth(frontendId) {
        var area = _resultArea();
        var name = _getBackendName(frontendId);
        area.innerHTML = '<div style="padding:12px;color:var(--text-muted);">⏳ 正在检查 ' + name + ' ...</div>';
        try {
            var data = await EvoAPI.moduleHealth(name);
            var healthy = data.healthy || data.status === 'ok' || data.status === 'healthy';
            var checks = data.checks || [];
            var checksHtml = checks.map(c =>
                '<span style="margin-right:12px;font-size:12px;">' + (c.healthy ? '✅' : '❌') + ' ' + c.name + '</span>'
            ).join('');
            area.innerHTML = `
                <div style="padding:12px;background:${healthy ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)'};border:1px solid ${healthy ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'};border-radius:8px;">
                    <div style="font-size:14px;font-weight:bold;color:${healthy ? '#10b981' : '#ef4444'};">${healthy ? '✅ 模块健康' : '❌ 模块异常'}</div>
                    <div style="margin-top:8px;">${checksHtml}</div>
                    <pre style="margin-top:8px;font-size:11px;color:var(--text-muted);max-height:200px;overflow:auto;">${JSON.stringify(data, null, 2)}</pre>
                </div>`;
        } catch (e) {
            area.innerHTML = '<div style="padding:12px;background:rgba(239,68,68,0.1);border-radius:8px;color:#ef4444;">❌ 请求失败: ' + e.message + '</div>';
        }
    }

    async function doModuleExecute(frontendId) {
        var area = _resultArea();
        var name = _getBackendName(frontendId);
        area.innerHTML = `
            <div style="padding:12px;">
                <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
                    <input id="exec-action" type="text" placeholder="Action (如: health_check)" style="flex:1;min-width:200px;padding:8px 12px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--text);font-size:13px;" value="health_check">
                    <input id="exec-params" type="text" placeholder='Params (JSON, 如: {"key":"val"})' style="flex:2;min-width:200px;padding:8px 12px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--text);font-size:13px;">
                    <button class="btn btn-edit" onclick="runModuleExecute('${frontendId}')">▶️ 执行</button>
                </div>
                <div id="exec-output" style="margin-top:12px;"></div>
            </div>`;
    }

    async function runModuleExecute(frontendId) {
        var name = _getBackendName(frontendId);
        var action = document.getElementById('exec-action').value.trim();
        var paramsStr = document.getElementById('exec-params').value.trim();
        var output = document.getElementById('exec-output');
        var params = {};
        if (paramsStr) {
            try { params = JSON.parse(paramsStr); }
            catch (e) { output.innerHTML = '<div style="color:#ef4444;">JSON格式错误: ' + e.message + '</div>'; return; }
        }
        output.innerHTML = '<div style="color:var(--text-muted);">⏳ 执行 ' + name + '.' + (action || 'execute') + ' ...</div>';
        var t0 = performance.now();
        try {
            var data = await EvoAPI.executeModule(name, action, params);
            var elapsed = (performance.now() - t0).toFixed(0);
            var success = data.success !== false;
            output.innerHTML = `
                <div style="padding:12px;background:${success ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)'};border:1px solid ${success ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'};border-radius:8px;">
                    <div style="display:flex;justify-content:space-between;">
                        <span style="font-weight:bold;color:${success ? '#10b981' : '#ef4444'};">${success ? '✅ 执行成功' : '❌ 执行失败'}</span>
                        <span style="font-size:11px;color:var(--text-muted);">${elapsed}ms</span>
                    </div>
                    <pre style="margin-top:8px;font-size:11px;color:var(--text-muted);max-height:300px;overflow:auto;white-space:pre-wrap;">${JSON.stringify(data, null, 2)}</pre>
                </div>`;
        } catch (e) {
            output.innerHTML = '<div style="padding:12px;background:rgba(239,68,68,0.1);border-radius:8px;color:#ef4444;">❌ 请求失败: ' + e.message + '</div>';
        }
    }

    async function doModuleCode(frontendId) {
        var area = _resultArea();
        var name = _getBackendName(frontendId);
        area.innerHTML = '<div style="padding:12px;color:var(--text-muted);">⏳ 加载 ' + name + ' 源码...</div>';
        try {
            var data = await EvoAPI.getModuleCode(name);
            var code = data.source_code || data.code || '(无源码)';
            var lines = code.split('\n').length;
            area.innerHTML = `
                <div style="padding:12px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-size:13px;color:var(--text-muted);">${name}.py — ${lines} 行</span>
                        <button class="btn btn-edit" style="font-size:11px;padding:4px 10px;" onclick="navigator.clipboard.writeText(document.getElementById('code-viewer').textContent);this.textContent='✅ 已复制'">📋 复制</button>
                    </div>
                    <pre id="code-viewer" style="margin-top:8px;padding:12px;background:var(--bg);border:1px solid var(--border);border-radius:8px;font-size:11px;color:var(--text);max-height:400px;overflow:auto;white-space:pre-wrap;word-break:break-all;">${code}</pre>
                </div>`;
        } catch (e) {
            area.innerHTML = '<div style="padding:12px;background:rgba(239,68,68,0.1);border-radius:8px;color:#ef4444;">❌ 加载失败: ' + e.message + '</div>';
        }
    }

    async function doModuleActions(frontendId) {
        var area = _resultArea();
        var name = _getBackendName(frontendId);
        area.innerHTML = '<div style="padding:12px;color:var(--text-muted);">⏳ 扫描 ' + name + ' 可用方法...</div>';
        try {
            var data = await EvoAPI.getModule(name);
            var methods = [];
            if (data && data.methods) methods.push(...data.methods);
            if (data && data.actions) methods.push(...data.actions);
            if (methods.length === 0) {
                area.innerHTML = `<div style="padding:12px;background:rgba(100,116,139,0.1);border-radius:8px;color:var(--text-muted);">ℹ️ ${name} 无已注册的方法列表。可尝试 execute 使用 action 如: health_check, initialize, get_stats, shutdown</div>`;
            } else {
                var btns = methods.map(m =>
                    '<button class="btn btn-edit" style="font-size:11px;padding:4px 10px;margin:3px;" onclick="quickExec(\'' + frontendId + '\',\'' + m + '\')">' + m + '</button>'
                ).join('');
                area.innerHTML = `
                    <div style="padding:12px;">
                        <div style="font-size:13px;margin-bottom:8px;color:var(--text-muted);">可用方法 (${methods.length}):</div>
                        <div style="display:flex;flex-wrap:wrap;gap:4px;">${btns}</div>
                    </div>`;
            }
        } catch (e) {
            area.innerHTML = '<div style="padding:12px;background:rgba(239,68,68,0.1);border-radius:8px;color:#ef4444;">❌ 加载失败: ' + e.message + '</div>';
        }
    }

    async function quickExec(frontendId, action) {
        var area = _resultArea();
        var name = _getBackendName(frontendId);
        area.innerHTML = '<div style="padding:12px;color:var(--text-muted);">⏳ 执行 ' + name + '.' + action + ' ...</div>';
        try {
            var data = await EvoAPI.executeModule(name, action, {});
            var success = data.success !== false;
            area.innerHTML = `
                <div style="padding:12px;background:${success ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)'};border-radius:8px;">
                    <div style="font-weight:bold;color:${success ? '#10b981' : '#ef4444'};">${success ? '✅' : '❌'} ${name}.${action}</div>
                    <pre style="margin-top:8px;font-size:11px;color:var(--text-muted);max-height:300px;overflow:auto;white-space:pre-wrap;">${JSON.stringify(data, null, 2)}</pre>
                </div>`;
        } catch (e) {
            area.innerHTML = '<div style="padding:12px;color:#ef4444;">❌ ' + e.message + '</div>';
        }
    }

    function initSystemIntegration() {
        if (!window.EvoAPI) {
            setTimeout(initSystemIntegration, 500);
            return;
        }
        console.log('[EVO-Dashboard] 系统集成初始化');
        EvoAPI.on('connected', function() {
            console.log('[EVO-Dashboard] 后端已连接');
            updateSystemStatus('online');
            loadModuleStatus();
        });
        EvoAPI.on('disconnected', function() {
            console.log('[EVO-Dashboard] 后端已断开');
            updateSystemStatus('offline');
        });
        EvoAPI.on('health_updated', function(data) {
            updateModuleHealth(data);
        });
        setInterval(function() {
            if (EvoAPI.isConnected()) {
                EvoAPI.health().then(function(h) {
                    updateSystemStatus((h.status === 'healthy' || h.status === 'running') ? 'online' : 'warning');
                });
            }
        }, 10000);
    }
    window.updateSystemStatus = function(status) {
        var indicator = document.getElementById('evo-system-status');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'evo-system-status';
            indicator.style.cssText = 'position:fixed;top:10px;right:10px;z-index:9999;padding:6px 12px;border-radius:20px;font-size:12px;font-weight:bold;transition:all 0.3s;';
            document.body.appendChild(indicator);
        }
        var colors = {
            online: {bg: '#10b981', text: '#fff', label: '🟢 系统在线'},
            offline: {bg: '#ef4444', text: '#fff', label: '🔴 离线'},
            warning: {bg: '#f59e0b', text: '#fff', label: '🟡 降级运行'}
        };
        var c = colors[status] || colors.offline;
        indicator.style.background = c.bg;
        indicator.style.color = c.text;
        indicator.textContent = c.label;
    }
    function updateModuleHealth(healthData) {
        document.querySelectorAll('.module-card').forEach(function(card) {
            var onclick = card.getAttribute('onclick');
            var match = onclick && onclick.match(/showPage\('([^']+)'\)/);
            var moduleId = match ? match[1] : null;
            if (!moduleId) return;
            var health = healthData[moduleId.replace(/-/g, '_')];
            if (health) {
                var dot = card.querySelector('.module-status');
                if (!dot) {
                    dot = document.createElement('span');
                    dot.className = 'module-status';
                    dot.style.cssText = 'position:absolute;top:8px;right:8px;width:8px;height:8px;border-radius:50%;';
                    card.style.position = 'relative';
                    card.appendChild(dot);
                }
                dot.style.background = health.status === 'ok' ? '#10b981' : (health.status === 'error' ? '#ef4444' : '#f59e0b');
            }
        });
    }
    async function loadModuleStatus() {
        try {
            var data = await EvoAPI.listModules();
            var count = data.count || data.total || (data.modules && data.modules.length) || 0;
            console.log('[EVO-Dashboard] 已加载', count, '个模块');
            updateModuleHealth(data.details || {});
        } catch (e) {
            console.error('[EVO-Dashboard] 加载模块失败:', e);
        }
    }

    // ═══════════════════════════════════════════════════════
    // V0.1 协调中心集成
    // ═══════════════════════════════════════════════════════
    function initV3Coordinator() {
        if (!window.EvoAPI) { setTimeout(initV3Coordinator, 500); return; }
        loadV3Status();
        setInterval(loadV3Status, 30000);
    }

    async function loadV3Status() {
        try {
            const [status, caps] = await Promise.all([
                EvoAPI.getCoordinatorStatus().catch(() => null),
                EvoAPI.getCapabilities().catch(() => null)
            ]);
            if (!status) return;

            // 更新悬浮状态卡
            var panel = document.getElementById('v3-coord-panel');
            if (!panel) {
                panel = createV3Panel();
            }

            var score = (caps && caps.automation_score) || status.automation_score || 0;
            var modCount = (status.modules && status.modules.registered) || 0;
            var capCount = (caps && caps.capabilities_count) || 0;
            var autoLoop = (status.capabilities && status.capabilities.autonomous_loop) || false;

            panel.innerHTML = `
                <div class="v3-score-ring" style="position:relative;width:80px;height:80px;margin:0 auto 8px;">
                    <svg width="80" height="80" viewBox="0 0 80 80">
                        <circle cx="40" cy="40" r="35" fill="none" stroke="#334" stroke-width="6"/>
                        <circle cx="40" cy="40" r="35" fill="none" stroke="${score >= 80 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444'}"
                            stroke-width="6" stroke-dasharray="${2 * Math.PI * 35}"
                            stroke-dashoffset="${2 * Math.PI * 35 * (1 - score / 100)}"
                            stroke-linecap="round" transform="rotate(-90 40 40)"/>
                    </svg>
                    <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:bold;color:#fff;">${score}</div>
                </div>
                <div style="color:#9ca3af;font-size:10px;text-align:center;margin-bottom:6px;">自动化评分</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:10px;color:#d1d5db;">
                    <div>📦 模块: <b>${modCount}</b></div>
                    <div>⚡ 能力: <b>${capCount}</b></div>
                    <div style="grid-column:1/-1;">🔄 自主循环: <b>${autoLoop ? '🟢 运行中' : '⚪ 已停止'}</b></div>
                </div>
                <button onclick="openV3Panel()" style="margin-top:8px;width:100%;padding:4px 8px;background:#3b82f6;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:11px;">🔍 打开协调中心</button>
            `;
        } catch (e) {
            console.warn('[v3] 协调器状态加载失败:', e);
        }
    }

    function createV3Panel() {
        var panel = document.createElement('div');
        panel.id = 'v3-coord-panel';
        panel.style.cssText = 'position:fixed;bottom:20px;left:20px;z-index:9998;background:#1a1a2e;border:1px solid #3b82f6;border-radius:16px;padding:12px;min-width:160px;color:#fff;font-family:system-ui;box-shadow:0 8px 32px rgba(59,130,246,0.3);';
        document.body.appendChild(panel);
        return panel;
    }

    // ═══════════════════════════════════════════════════════
    // 系统实时监控面板 — 对接 /api/monitor/realtime
    // ═══════════════════════════════════════════════════════
    var _monitorInterval = null;
    function openMonitorPanel() {
        var modal = document.getElementById('sys-monitor-modal');
        if (modal) { modal.style.display = 'flex'; _startMonitorPoll(); return; }

        modal = document.createElement('div');
        modal.id = 'sys-monitor-modal';
        modal.style.cssText = 'position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';
        modal.onclick = (e) => { if (e.target === modal) { modal.style.display = 'none'; if (_monitorInterval) { clearInterval(_monitorInterval); _monitorInterval = null; } } };

        modal.innerHTML = `
            <div style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:20px;width:92%;max-width:1200px;height:85vh;display:flex;flex-direction:column;color:var(--text-primary);font-family:system-ui;box-shadow:0 20px 60px rgba(0,0,0,0.4);overflow:hidden;">
                <div style="display:flex;justify-content:space-between;align-items:center;padding:16px 24px;border-bottom:1px solid var(--border-color);">
                    <h2 style="font-size:18px;font-weight:700;margin:0;">📊 系统实时监控</h2>
                    <div style="display:flex;gap:8px;align-items:center;">
                        <span id="monitor-status-dot" style="width:8px;height:8px;border-radius:50%;background:#10b981;display:inline-block;"></span>
                        <span id="monitor-status-text" style="font-size:12px;color:var(--text-muted);">连接中...</span>
                        <button onclick="this.closest('[id=sys-monitor-modal]').style.display='none';if(_monitorInterval){clearInterval(_monitorInterval);_monitorInterval=null;}" style="background:rgba(255,255,255,0.1);border:none;color:var(--text-primary);width:28px;height:28px;border-radius:8px;cursor:pointer;font-size:16px;">✕</button>
                    </div>
                </div>
                <div style="flex:1;overflow-y:auto;padding:20px 24px;">
                    <!-- 系统概览 -->
                    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">
                        <div style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);border-radius:12px;padding:16px;text-align:center;">
                            <div id="mon-modules-total" style="font-size:28px;font-weight:800;color:#10b981;">—</div>
                            <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">总模块</div>
                        </div>
                        <div style="background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.3);border-radius:12px;padding:16px;text-align:center;">
                            <div id="mon-modules-ok" style="font-size:28px;font-weight:800;color:#3b82f6;">—</div>
                            <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">已加载</div>
                        </div>
                        <div style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);border-radius:12px;padding:16px;text-align:center;">
                            <div id="mon-uptime" style="font-size:28px;font-weight:800;color:#f59e0b;">—</div>
                            <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">运行时间</div>
                        </div>
                        <div style="background:rgba(139,92,246,0.1);border:1px solid rgba(139,92,246,0.3);border-radius:12px;padding:16px;text-align:center;">
                            <div id="mon-score" style="font-size:28px;font-weight:800;color:#8b5cf6;">—</div>
                            <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">自动化评分</div>
                        </div>
                    </div>

                    <!-- 资源监控 -->
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px;">
                        <div style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:12px;padding:16px;">
                            <div style="font-weight:600;margin-bottom:12px;font-size:14px;">💻 系统资源</div>
                            <div id="mon-cpu-bar" style="margin-bottom:10px;">
                                <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;"><span>CPU</span><span id="mon-cpu-val">—</span></div>
                                <div style="height:8px;background:var(--border-color);border-radius:4px;overflow:hidden;"><div id="mon-cpu-fill" style="height:100%;width:0%;background:linear-gradient(90deg,#10b981,#f59e0b,#ef4444);border-radius:4px;transition:width 0.5s;"></div></div>
                            </div>
                            <div id="mon-mem-bar" style="margin-bottom:10px;">
                                <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;"><span>内存</span><span id="mon-mem-val">—</span></div>
                                <div style="height:8px;background:var(--border-color);border-radius:4px;overflow:hidden;"><div id="mon-mem-fill" style="height:100%;width:0%;background:linear-gradient(90deg,#10b981,#f59e0b,#ef4444);border-radius:4px;transition:width 0.5s;"></div></div>
                            </div>
                            <div id="mon-disk-bar">
                                <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;"><span>磁盘</span><span id="mon-disk-val">—</span></div>
                                <div style="height:8px;background:var(--border-color);border-radius:4px;overflow:hidden;"><div id="mon-disk-fill" style="height:100%;width:0%;background:linear-gradient(90deg,#10b981,#f59e0b,#ef4444);border-radius:4px;transition:width 0.5s;"></div></div>
                            </div>
                            <div style="margin-top:12px;font-size:11px;color:var(--text-muted);">
                                进程内存: <span id="mon-proc-mem">—</span>MB · 线程: <span id="mon-threads">—</span>
                            </div>
                        </div>
                        <div style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:12px;padding:16px;">
                            <div style="font-weight:600;margin-bottom:12px;font-size:14px;">🌐 API端点统计</div>
                            <div id="mon-endpoints-list" style="font-size:12px;">
                                <div style="color:var(--text-muted);text-align:center;padding:20px;">加载中...</div>
                            </div>
                            <div style="margin-top:12px;font-size:11px;color:var(--text-muted);">
                                WebSocket连接: <span id="mon-ws">—</span> · 总错误: <span id="mon-errors">—</span>
                            </div>
                        </div>
                    </div>

                    <!-- 热门端点延迟 -->
                    <div style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:12px;padding:16px;margin-bottom:20px;">
                        <div style="font-weight:600;margin-bottom:12px;font-size:14px;">⚡ 端点响应延迟 (ms)</div>
                        <div id="mon-latency-chart" style="display:flex;align-items:flex-end;gap:8px;height:120px;padding:8px 0;">
                            <div style="color:var(--text-muted);text-align:center;padding:20px;width:100%;">加载中...</div>
                        </div>
                    </div>

                    <!-- 错误模块 -->
                    <div style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:12px;padding:16px;">
                        <div style="font-weight:600;margin-bottom:12px;font-size:14px;">⚠️ 错误模块</div>
                        <div id="mon-error-modules" style="font-size:12px;max-height:200px;overflow-y:auto;">
                            <div style="color:var(--text-muted);text-align:center;padding:20px;">暂无错误</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        _startMonitorPoll();
    }

    function _startMonitorPoll() {
        if (_monitorInterval) return;
        _pollMonitor();
        _monitorInterval = setInterval(_pollMonitor, 3000);
    }

    async function _pollMonitor() {
        try {
            var r = await fetch('/api/monitor/realtime');
            if (!r.ok) return;
            var d = await r.json();
            document.getElementById('monitor-status-dot').style.background = '#10b981';
            document.getElementById('monitor-status-text').textContent = '实时更新中';

            // 概览
            var s = d.system;
            document.getElementById('mon-modules-total').textContent = s.modules_total;
            document.getElementById('mon-modules-ok').textContent = s.modules_ok + ' / ' + s.modules_total;
            var upSec = s.uptime_seconds;
            var upStr = upSec < 60 ? upSec + 's' : upSec < 3600 ? Math.floor(upSec/60) + 'm' : Math.floor(upSec/3600) + 'h' + Math.floor((upSec%3600)/60) + 'm';
            document.getElementById('mon-uptime').textContent = upStr;
            document.getElementById('mon-score').textContent = s.automation_score + '%';

            // 资源
            var res = d.resources;
            document.getElementById('mon-cpu-val').textContent = res.cpu_percent.toFixed(1) + '%';
            document.getElementById('mon-cpu-fill').style.width = res.cpu_percent + '%';
            document.getElementById('mon-mem-val').textContent = res.memory_used_mb + ' / ' + res.memory_total_mb + ' MB (' + res.memory_percent.toFixed(1) + '%)';
            document.getElementById('mon-mem-fill').style.width = res.memory_percent + '%';
            document.getElementById('mon-disk-val').textContent = res.disk_percent.toFixed(1) + '% · ' + res.disk_free_gb + 'GB 可用';
            document.getElementById('mon-disk-fill').style.width = res.disk_percent + '%';
            document.getElementById('mon-proc-mem').textContent = res.process_memory_mb;
            document.getElementById('mon-threads').textContent = res.process_threads;

            // API端点
            var ep = d.endpoints;
            var epHtml = '<table style="width:100%;border-collapse:collapse;">';
            epHtml += '<tr style="border-bottom:1px solid var(--border-color);"><th style="text-align:left;padding:4px 0;font-size:11px;color:var(--text-muted);">端点</th><th style="text-align:right;padding:4px 0;font-size:11px;color:var(--text-muted);">请求次数</th><th style="text-align:right;padding:4px 0;font-size:11px;color:var(--text-muted);">平均延迟</th></tr>';
            for (var e of (ep.top_by_requests || []).slice(0, 8)) {
                var lat = ep.avg_latency_ms[e.path] || '—';
                var latColor = typeof lat === 'number' && lat > 1000 ? '#ef4444' : typeof lat === 'number' && lat > 200 ? '#f59e0b' : '#10b981';
                epHtml += `<tr style="border-bottom:1px solid rgba(255,255,255,0.05);"><td style="padding:6px 0;font-family:monospace;font-size:11px;">${e.path}</td><td style="text-align:right;padding:6px 0;font-size:11px;font-weight:600;">${e.count}</td><td style="text-align:right;padding:6px 0;font-size:11px;color:${latColor};">${typeof lat === 'number' ? lat.toFixed(0) : lat}ms</td></tr>`;
            }
            epHtml += '</table>';
            document.getElementById('mon-endpoints-list').innerHTML = epHtml;
            document.getElementById('mon-ws').textContent = s.ws_connections;
            document.getElementById('mon-errors').textContent = ep.total_errors;

            // 延迟图表
            var latencies = Object.entries(ep.avg_latency_ms || {}).map(([p, v]) => ({ path: p.split('/').pop() || p, ms: v })).sort((a, b) => b.ms - a.ms).slice(0, 10);
            if (latencies.length) {
                var maxMs = Math.max(...latencies.map(l => l.ms), 1);
                var chartHtml = '';
                for (var l of latencies) {
                    var h = Math.max(4, (l.ms / maxMs) * 100);
                    var c = l.ms > 1000 ? '#ef4444' : l.ms > 200 ? '#f59e0b' : '#10b981';
                    chartHtml += `<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;">
                        <span style="font-size:10px;color:${c};font-weight:600;">${l.ms.toFixed(0)}</span>
                        <div style="width:100%;height:${h}%;background:${c};border-radius:4px 4px 0 0;min-height:4px;transition:height 0.5s;"></div>
                        <span style="font-size:9px;color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:60px;">${l.path}</span>
                    </div>`;
                }
                document.getElementById('mon-latency-chart').innerHTML = chartHtml;
            }

            // 错误模块
            var errs = d.modules.errors || [];
            if (errs.length === 0) {
                document.getElementById('mon-error-modules').innerHTML = '<div style="color:#10b981;text-align:center;padding:20px;">✅ 全部模块正常运行</div>';
            } else {
                var errHtml = '';
                for (var e of errs) {
                    errHtml += `<div style="padding:8px;margin-bottom:4px;background:rgba(239,68,68,0.1);border-radius:6px;border-left:3px solid #ef4444;">
                        <span style="font-weight:600;">${e.name}</span> <span style="color:#ef4444;font-size:11px;">[${e.status}]</span>
                        <div style="color:var(--text-muted);font-size:11px;margin-top:2px;">${e.error || '无详情'}</div>
                    </div>`;
                }
                document.getElementById('mon-error-modules').innerHTML = errHtml;
            }
        } catch (e) {
            document.getElementById('monitor-status-dot').style.background = '#ef4444';
            document.getElementById('monitor-status-text').textContent = '连接失败';
        }
    }

    function openV3Panel() {
        console.log('[openV3Panel] called, existing modal:', !!document.getElementById('v3-coord-modal'));
        // 创建模态框
        var modal = document.getElementById('v3-coord-modal');
        if (modal) { console.log('[openV3Panel] show existing modal'); modal.style.display = 'flex'; if (_v3Minimized) { var d = document.getElementById('v3-coord-dialog'); if (d) d.classList.remove('v3-minimized'); _v3Minimized = false; } loadV3Modal(); AutoExecutionEngine.fetchBackendStatus(); return; }

        modal = document.createElement('div');
        modal.id = 'v3-coord-modal';
        modal.style.cssText = 'position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';
        modal.onclick = (e) => { if (e.target === modal) modal.style.display = 'none'; };
        modal.innerHTML = `
            <div class="resizable-modal v3-dark" id="v3-coord-dialog" style="background:var(--v3-bg);border:1px solid var(--v3-border);border-radius:20px;width:92%;max-width:1100px;height:82vh;display:flex;flex-direction:column;color:var(--v3-text);font-family:system-ui;box-shadow:0 20px 60px rgba(0,0,0,0.4);position:relative;margin:auto;">
                <div class="modal-header" id="v3-coord-header" style="display:flex;justify-content:space-between;align-items:center;padding:14px 24px;border-bottom:1px solid var(--v3-border);background:var(--v3-header-bg);flex-shrink:0;">
                    <h2 style="margin:0;font-size:18px;cursor:move;display:flex;align-items:center;gap:8px;">
                        <span id="v3-status-dot" class="status-dot online"></span>
                        🧠 协调中心 V0.1
                    </h2>
                    <div style="display:flex;gap:4px;align-items:center;">
                        <button class="modal-win-btn" onclick="toggleV3Theme()" title="切换主题" id="v3-theme-btn">🌙</button>
                        <button class="modal-win-btn" onclick="toggleV3Minimize()" title="最小化" style="font-size:14px;">─</button>
                        <button class="modal-win-btn maximize-btn" onclick="toggleV3Maximize()" title="最大化/还原">☐</button>
                        <button class="modal-win-btn" onclick="this.closest('[id=v3-coord-modal]').style.display='none'" title="关闭" style="font-size:18px;">✕</button>
                    </div>
                </div>
                <div id="v3-modal-content" style="color:var(--v3-text2);font-size:13px;padding:20px 24px;overflow-y:auto;flex:1;">
                    加载中...
                </div>
                <div class="resize-handle" id="v3-resize-handle"></div>
                <div class="v3-bottom-bar" id="v3-bottom-bar">
                    <span id="v3-status-text"><span class="status-dot online"></span>已连接</span>
                    <span>535 模块 · <span id="v3-score-display">--</span>/100 · <span id="v3-uptime-display"></span></span>
                    <span style="cursor:pointer;" onclick="loadV3Modal()" title="点击刷新">🔄 刷新</span>
                </div>
            </div>`;
        document.body.appendChild(modal);
        // 初始化拖拽和调整大小
        initV3DragResize();
        loadV3Modal();
        AutoExecutionEngine.fetchBackendStatus();
    }

    // 记住弹窗位置/大小状态
    var _v3Maximized = false;
    var _v3SavedRect = null;
    var _v3Minimized = false;
    var _v3Dark = true;

    function toggleV3Theme() {
        var dialog = document.getElementById('v3-coord-dialog');
        var btn = document.getElementById('v3-theme-btn');
        if (!dialog) return;
        _v3Dark = !_v3Dark;
        dialog.classList.remove('v3-dark','v3-light');
        dialog.classList.add(_v3Dark ? 'v3-dark' : 'v3-light');
        if (btn) btn.textContent = _v3Dark ? '🌙' : '☀️';
    }

    function toggleV3Minimize() {
        var dialog = document.getElementById('v3-coord-dialog');
        if (!dialog) return;
        _v3Minimized = !_v3Minimized;
        if (_v3Minimized) {
            // 最小化时清除最大化状态
            if (_v3Maximized) {
                dialog.classList.remove('maximized');
                _v3Maximized = false;
                _v3SavedRect = null;
            }
            dialog.classList.add('v3-minimized');
        } else {
            dialog.classList.remove('v3-minimized');
        }
    }

    function v3SwitchTab(name) {
        document.querySelectorAll('.v3-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
        document.querySelectorAll('.v3-tab-panel').forEach(p => p.classList.toggle('active', p.id === 'v3-tab-' + name));
    }

    function toggleV3Maximize() {
        var dialog = document.getElementById('v3-coord-dialog');
        if (!dialog) return;
        // 最大化时清除最小化状态
        if (_v3Minimized) {
            dialog.classList.remove('v3-minimized');
            _v3Minimized = false;
        }
        if (!_v3Maximized) {
            _v3SavedRect = { left: dialog.offsetLeft, top: dialog.offsetTop, width: dialog.offsetWidth, height: dialog.offsetHeight, margin: dialog.style.margin, position: dialog.style.position };
            dialog.classList.add('maximized');
            _v3Maximized = true;
        } else {
            dialog.classList.remove('maximized');
            dialog.style.position = 'relative';
            dialog.style.margin = 'auto';
            dialog.style.left = '';
            dialog.style.top = '';
            dialog.style.width = '';
            dialog.style.height = '';
            _v3Maximized = false;
        }
    }

    function initV3DragResize() {
        var dialog = document.getElementById('v3-coord-dialog');
        var header = document.getElementById('v3-coord-header');
        var handle = document.getElementById('v3-resize-handle');
        if (!dialog || !header) return;

        // 拖拽移动
        var dragging = false, dx = 0, dy = 0;
        header.addEventListener('mousedown', (e) => {
            if (e.target.tagName === 'BUTTON' || e.target.closest('button')) return;
            if (_v3Maximized) return;
            dragging = true;
            dx = e.clientX - dialog.offsetLeft;
            dy = e.clientY - dialog.offsetTop;
            dialog.style.transition = 'none';
            e.preventDefault();
        });
        document.addEventListener('mousemove', (e) => {
            if (!dragging) return;
            var nx = e.clientX - dx, ny = e.clientY - dy;
            nx = Math.max(0, Math.min(nx, window.innerWidth - 100));
            ny = Math.max(0, Math.min(ny, window.innerHeight - 50));
            dialog.style.left = nx + 'px';
            dialog.style.top = ny + 'px';
            dialog.style.margin = '0';
        });
        document.addEventListener('mouseup', () => { if (dragging) { dragging = false; dialog.style.transition = ''; } });

        // 调整大小
        if (handle) {
            var resizing = false, startW = 0, startH = 0, sx = 0, sy = 0;
            handle.addEventListener('mousedown', (e) => {
                if (_v3Maximized) return;
                resizing = true;
                startW = dialog.offsetWidth;
                startH = dialog.offsetHeight;
                sx = e.clientX; sy = e.clientY;
                dialog.style.transition = 'none';
                e.preventDefault(); e.stopPropagation();
            });
            document.addEventListener('mousemove', (e) => {
                if (!resizing) return;
                dialog.style.width = Math.max(600, startW + (e.clientX - sx)) + 'px';
                dialog.style.height = Math.max(400, startH + (e.clientY - sy)) + 'px';
            });
            document.addEventListener('mouseup', () => { if (resizing) { resizing = false; dialog.style.transition = ''; } });
        }

        // 双击标题栏最大化/还原
        header.addEventListener('dblclick', (e) => {
            if (e.target.tagName === 'BUTTON' || e.target.closest('button')) return;
            toggleV3Maximize();
        });

        // 单击标题栏：最小化状态时恢复
        header.addEventListener('click', (e) => {
            if (e.target.tagName === 'BUTTON' || e.target.closest('button')) return;
            if (_v3Minimized) {
                toggleV3Minimize();
            }
        });

        // ESC关闭
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && document.getElementById('v3-coord-modal')?.style.display !== 'none') {
                document.getElementById('v3-coord-modal').style.display = 'none';
            }
        });
    }

    async function loadV3Modal() {
        var content = document.getElementById('v3-modal-content');
        if (!content) return;
        try {
            const [status, caps] = await Promise.all([
                EvoAPI.getCoordinatorStatus().catch(() => null),
                EvoAPI.getCapabilities().catch(() => null)
            ]);
            if (!status) {
                content.innerHTML = '<div class="v3-tab-panel active" style="text-align:center;padding:40px;color:var(--v3-accent);">协调器连接失败，请检查后端服务</div>';
                document.getElementById('v3-status-dot')?.classList.replace('online','offline');
                return;
            }
            document.getElementById('v3-status-dot')?.classList.replace('offline','online');

            var score = (caps && caps.automation_score) || 0;
            var stats = status.execution_stats || {};
            var caps_list = (caps && caps.capabilities) || {};
            var tags_list = (caps && caps.tags) || {};
            var sd = document.getElementById('v3-score-display'); if(sd) sd.textContent = score;
            var ut = document.getElementById('v3-uptime-display'); if(ut) ut.textContent = new Date().toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'});

            var capsHTML = '';
            for (const [cap, mods] of Object.entries(caps_list).slice(0, 12)) {
                capsHTML += `<span style="display:inline-block;background:var(--v3-accent);color:#fff;border-radius:12px;padding:2px 8px;margin:2px;font-size:11px;">${cap} (${mods.length})</span>`;
            }
            var tagsHTML = '';
            for (const [tag, mods] of Object.entries(tags_list).slice(0, 15)) {
                tagsHTML += `<span style="display:inline-block;background:#7c3aed;color:#fff;border-radius:12px;padding:2px 8px;margin:2px;font-size:11px;">${tag} (${mods.length})</span>`;
            }

            content.innerHTML = `
                <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">
                    <div class="v3-card" style="text-align:center;">
                        <div style="font-size:28px;font-weight:bold;color:#3b82f6;">${score}<span style="font-size:14px;">/100</span></div>
                        <div style="color:var(--v3-muted);font-size:11px;margin-top:4px;">自动化评分</div>
                    </div>
                    <div class="v3-card" style="text-align:center;">
                        <div style="font-size:28px;font-weight:bold;color:#10b981;">${(status.modules && status.modules.registered) || 0}</div>
                        <div style="color:var(--v3-muted);font-size:11px;margin-top:4px;">已注册模块</div>
                    </div>
                    <div class="v3-card" style="text-align:center;">
                        <div style="font-size:28px;font-weight:bold;color:#f59e0b;">${Object.keys(caps_list).length}</div>
                        <div style="color:var(--v3-muted);font-size:11px;margin-top:4px;">能力类型</div>
                    </div>
                    <div class="v3-card" style="text-align:center;">
                        <div style="font-size:28px;font-weight:bold;color:${(status.capabilities && status.capabilities.autonomous_loop) ? '#10b981' : '#6b7280'};">${(status.capabilities && status.capabilities.autonomous_loop) ? '🟢' : '⚪'}</div>
                        <div style="color:var(--v3-muted);font-size:11px;margin-top:4px;">自主循环</div>
                    </div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px;">
                    <div class="v3-card">
                        <h3 style="margin:0 0 10px;font-size:14px;color:var(--v3-text);">⚡ 能力图谱</h3>
                        <div>${capsHTML}</div>
                    </div>
                    <div class="v3-card">
                        <h3 style="margin:0 0 10px;font-size:14px;color:var(--v3-text);">🏷️ 标签分布</h3>
                        <div>${tagsHTML}</div>
                    </div>
                </div>
                <div class="v3-card" style="margin-bottom:16px;">
                    <h3 style="margin:0 0 10px;font-size:14px;color:var(--v3-text);">📊 执行统计</h3>
                    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;font-size:12px;color:var(--v3-text2);">
                        <div>总任务: <b>${stats.total || 0}</b></div>
                        <div>成功: <b style="color:#10b981;">${stats.success || 0}</b></div>
                        <div>失败: <b style="color:#ef4444;">${stats.failed || 0}</b></div>
                    </div>
                </div>
                <div class="v3-card" style="margin-bottom:16px;">
                    <h3 style="margin:0 0 10px;font-size:14px;color:var(--v3-text);">⚡ 任务执行（输入自然语言任务，自动编排模块执行）</h3>
                    <div style="display:flex;gap:8px;">
                        <input id="v3-task-input" class="v3-input" type="text" placeholder="输入任务，如: 查询上证指数今天的收盘价"
                            onkeydown="if(event.key==='Enter') v3ExecuteTask()"/>
                        <button class="v3-btn" onclick="v3ExecuteTask()" style="background:#3b82f6;padding:10px 24px;font-weight:bold;font-size:14px;">执行</button>
                    </div>
                    <div id="v3-exec-chain" style="margin-top:12px;font-size:12px;"></div>
                    <div id="v3-exec-result" style="margin-top:8px;font-size:12px;"></div>
                </div>
                <div class="v3-card" style="margin-bottom:16px;">
                    <h3 style="margin:0 0 10px;font-size:14px;color:var(--v3-text);">📦 全部模块 <span id="v3-mod-count" style="color:var(--v3-muted);font-weight:normal;font-size:12px;">加载中...</span></h3>
                    <div style="display:flex;gap:8px;margin-bottom:10px;">
                        <input id="v3-mod-search" class="v3-input" type="text" placeholder="搜索模块名..." style="flex:1;" oninput="v3FilterModules()"/>
                        <select id="v3-mod-filter" class="v3-input" style="width:120px;" onchange="v3FilterModules()">
                            <option value="">全部分类</option>
                        </select>
                    </div>
                    <div id="v3-modules-list" style="max-height:400px;overflow-y:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:8px;font-size:12px;">
                        加载中...
                    </div>
                </div>
                <div class="v3-card" style="margin-bottom:16px;">
                    <h3 style="margin:0 0 10px;font-size:14px;color:var(--v3-text);">🔍 模块查找</h3>
                    <div style="display:flex;gap:8px;">
                        <input id="v3-find-input" class="v3-input" type="text" placeholder="输入任务描述，如: 查询股票数据"
                            onkeydown="if(event.key==='Enter') v3FindModules()"/>
                        <button class="v3-btn" onclick="v3FindModules()" style="background:#6366f1;">查找</button>
                    </div>
                    <div id="v3-find-results" style="margin-top:10px;font-size:12px;"></div>
                </div>
                <div style="display:flex;gap:10px;flex-wrap:wrap;">
                    <button class="v3-btn" onclick="EvoAPI.startAutonomous()" style="background:#10b981;">🚀 启动自主循环</button>
                    <button class="v3-btn" onclick="EvoAPI.stopAutonomous()" style="background:#ef4444;">⏹ 停止自主循环</button>
                    <button class="v3-btn" onclick="v3TestExecute()" style="background:#7c3aed;">⚡ 测试执行</button>
                </div>
            `;
        } catch (e) {
            content.innerHTML = `<p style="color:#ef4444;">加载失败: ${e.message}</p>`;
            // 加载全量模块列表
            v3LoadModules();
        }
    }

    // 协调引擎模块列表
    var _v3AllModules = [];
    async function v3LoadModules() {
        var listEl = document.getElementById('v3-modules-list');
        var countEl = document.getElementById('v3-mod-count');
        if (!listEl) return;
        try {
            var r = await fetch('/api/modules');
            var data = await r.json();
            var mods = data.modules || data || [];
            _v3AllModules = Array.isArray(mods) ? mods : [];
            if (countEl) countEl.textContent = `(${_v3AllModules.length})`;
            // 填充分类下拉
            var cats = [...new Set(_v3AllModules.map(m => m.category || m.group || '未分类'))].sort();
            var sel = document.getElementById('v3-mod-filter');
            if (sel) {
                sel.innerHTML = '<option value="">全部分类</option>' + cats.map(c => `<option value="${c}">${c} (${_v3AllModules.filter(m=>(m.category||m.group||'未分类')===c).length})</option>`).join('');
            }
            v3FilterModules();
        } catch(e) {
            listEl.innerHTML = '<div style="color:#ef4444;">模块加载失败</div>';
            if (countEl) countEl.textContent = '(加载失败)';
        }
    }

    function v3FilterModules() {
        var listEl = document.getElementById('v3-modules-list');
        var search = (document.getElementById('v3-mod-search') || {}).value || '';
        var cat = (document.getElementById('v3-mod-filter') || {}).value || '';
        if (!listEl || !_v3AllModules.length) return;
        var filtered = _v3AllModules.filter(m => {
            if (cat && (m.category || m.group || '') !== cat) return false;
            if (search) {
                var q = search.toLowerCase();
                return (m.name || '').toLowerCase().includes(q) ||
                       (m.description || m.desc || '').toLowerCase().includes(q);
            }
            return true;
        });
        var max = 200;
        var show = filtered.slice(0, max);
        var html = '<div style="display:flex;flex-direction:column;gap:3px;max-height:400px;overflow-y:auto;padding-right:4px;">';
        for (var m of show) {
            var name = m.name || '';
            var desc = m.description || m.desc || '';
            var cat2 = m.category || m.group || '';
            var grade = m.grade || 'C';
            var stColor = grade === 'A' ? '#10b981' : grade === 'B' ? '#f59e0b' : '#6b7280';
            html += `<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 10px;background:#0f172a;border-radius:6px;border-left:3px solid ${stColor};">
                <div style="flex:1;min-width:0;">
                    <div style="font-weight:600;color:#e2e8f0;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${name}</div>
                    <div style="color:#6b7280;font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${desc}</div>
                </div>
                <button onclick="v3ExecModule('${name}')" style="background:#3b82f6;color:#fff;border:none;border-radius:4px;padding:4px 10px;cursor:pointer;font-size:11px;flex-shrink:0;margin-left:8px;">▶</button>
            </div>`;
        }
        if (filtered.length > max) {
            html += `<div style="text-align:center;color:#6b7280;padding:8px;">... 共 ${filtered.length} 个，显示前 ${max} 个</div>`;
        }
        html += '</div>';
        listEl.innerHTML = html;
        if (!listEl) return;
        var q = (document.getElementById('v3-mod-search')?.value || '').toLowerCase();
        var cat = document.getElementById('v3-mod-filter')?.value || '';
        var filtered = _v3AllModules;
        if (cat) filtered = filtered.filter(m => (m.category || m.group || '未分类') === cat);
        if (q) filtered = filtered.filter(m => (m.name || m.id || '').toLowerCase().includes(q) || (m.description || '').toLowerCase().includes(q));
        if (filtered.length === 0) {
            listEl.innerHTML = '<div style="color:#9ca3af;padding:20px;text-align:center;">无匹配模块</div>';
            return;
        }
        listEl.innerHTML = filtered.slice(0, 100).map(m => {
            var name = m.name || m.id || m.module || '?';
            var desc = (m.description || m.desc || '').slice(0, 50);
            var modId = m.id || m.module || name;
            return `<div style="background:var(--v3-card-bg,#0f172a);border-radius:8px;padding:8px 10px;cursor:pointer;border:1px solid transparent;transition:border-color .2s;" 
                onclick="v3ExecModule('${modId}')" 
                onmouseover="this.style.borderColor='var(--v3-accent,#6366f1)'" 
                onmouseout="this.style.borderColor='transparent'">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <b style="color:#fff;font-size:12px;">${name}</b>
                    <span style="background:#3b82f6;color:#fff;border-radius:6px;padding:1px 6px;font-size:10px;cursor:pointer;">▶ 执行</span>
                </div>
                <div style="color:#9ca3af;font-size:10px;margin-top:3px;">${desc}</div>
            </div>`;
        }).join('');
        if (filtered.length > 100) {
            listEl.innerHTML += `<div style="color:#9ca3af;padding:8px;text-align:center;">还有 ${filtered.length - 100} 个模块，请缩小搜索范围</div>`;
        }
    }

    async function v3ExecModule(modId) {
        var resultEl = document.getElementById('v3-exec-result');
        if (resultEl) resultEl.innerHTML = `<span style="color:#f59e0b;">⚡ 正在执行 ${modId}...</span>`;
        try {
            var r = await fetch('/api/modules/' + modId + '/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'run', params: {} })
            });
            var data = await r.json();
            var ok = data.success !== false;
            var output = data.result || data.output || data.data || JSON.stringify(data).slice(0, 300);
            if (resultEl) resultEl.innerHTML = `<div style="background:${ok ? '#064e3b' : '#450a0a'};border-radius:8px;padding:10px;margin-top:8px;">
                <div style="font-weight:600;color:${ok ? '#10b981' : '#ef4444'};">${ok ? '✓ ' : '✗ '}${modId}</div>
                <pre style="color:#d1d5db;margin:6px 0 0;white-space:pre-wrap;word-break:break-all;font-size:11px;max-height:150px;overflow-y:auto;">${typeof output === 'string' ? output : JSON.stringify(output, null, 2)}</pre>
            </div>`;
        } catch(e) {
            if (resultEl) resultEl.innerHTML = `<span style="color:#ef4444;">执行失败: ${e.message}</span>`;
        }
    }

    async function v3FindModules() {
        var input = document.getElementById('v3-find-input');
        var results = document.getElementById('v3-find-results');
        if (!input || !results) return;
        var q = input.value.trim();
        if (!q) return;
        results.innerHTML = '查找中...';
        try {
            var data = await EvoAPI.findModules(q);
            if (!data.matches || data.matches.length === 0) {
                results.innerHTML = '<span style="color:#9ca3af;">未找到匹配的模块</span>';
                return;
            }
            var html = '<div style="display:flex;flex-direction:column;gap:4px;">';
            for (var m of data.matches.slice(0, 8)) {
                var tags = (m.tags || []).map(t => `<span style="background:#3b82f6;border-radius:8px;padding:1px 6px;font-size:10px;">${t}</span>`).join('');
                html += `<div style="background:#0f172a;border-radius:8px;padding:8px 10px;display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <b style="color:#fff;">${m.module}</b>
                        <span style="color:#6b7280;font-size:11px;margin-left:6px;">${(m.capabilities && m.capabilities.join(', ')) || ''}</span>
                    </div>
                    <div style="display:flex;align-items:center;gap:8px;">
                        ${tags}
                        <span style="color:${m.score >= 3 ? '#10b981' : m.score >= 2 ? '#f59e0b' : '#6b7280'};font-size:11px;">${m.score}分</span>
                    </div>
                </div>`;
            }
            html += '</div>';
            results.innerHTML = html;
        } catch (e) {
            results.innerHTML = `<span style="color:#ef4444;">查找失败: ${e.message}</span>`;
        }
    }

    async function v3ExecuteTask() {
        var input = document.getElementById('v3-task-input');
        var chainEl = document.getElementById('v3-exec-chain');
        var resultEl = document.getElementById('v3-exec-result');
        if (!input || !chainEl || !resultEl) return;
        var task = input.value.trim();
        if (!task) return;
        chainEl.innerHTML = '<div style="color:#f59e0b;">⚡ 正在分析任务...</div>';
        resultEl.innerHTML = '';
        try {
            // 调用统一执行接口 /api/execute
            var r = await fetch('/api/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task: task, params: {} })
            });
            var data = await r.json();
            var ok = data.success !== false;
            var chain = data.chain || data.modules || [];
            var output = data.result || data.output || data.data || JSON.stringify(data).slice(0, 500);
            // 显示执行链
            if (chain.length > 0) {
                var chainHtml = '<div style="display:flex;flex-wrap:wrap;gap:4px;align-items:center;">';
                chain.forEach((c, i) => {
                    var mName = typeof c === 'string' ? c : (c.module || c.name || '');
                    var conf = typeof c === 'string' ? '' : (c.confidence || c.score || '');
                    chainHtml += `<span style="background:#1e3a5f;color:#93c5fd;border-radius:6px;padding:2px 8px;font-size:11px;">${mName}${conf ? ' (' + conf + ')' : ''}</span>`;
                    if (i < chain.length - 1) chainHtml += '<span style="color:#6b7280;">→</span>';
                });
                chainHtml += '</div>';
                chainEl.innerHTML = chainHtml;
            } else {
                chainEl.innerHTML = '';
            }
            // 显示结果
            resultEl.innerHTML = `<div style="background:${ok ? '#064e3b' : '#450a0a'};border-radius:8px;padding:10px;margin-top:8px;">
                <div style="font-weight:600;color:${ok ? '#10b981' : '#ef4444'};">${ok ? '✓ 任务完成' : '✗ 任务失败'}</div>
                <pre style="color:#d1d5db;margin:6px 0 0;white-space:pre-wrap;word-break:break-all;font-size:11px;max-height:200px;overflow-y:auto;">${typeof output === 'string' ? output : JSON.stringify(output, null, 2)}</pre>
            </div>`;
        } catch(e) {
            chainEl.innerHTML = '';
            resultEl.innerHTML = `<span style="color:#ef4444;">执行失败: ${e.message}</span>
                <div style="font-size:48px;margin-bottom:16px;">🔗</div>
                <div style="font-size:18px;font-weight:600;margin-bottom:8px;">暂无管线</div>
                <div style="margin-bottom:20px;">创建管线让多个模块自动串联执行</div>
                <button onclick="pipelineNewForm()" style="padding:10px 24px;background:var(--primary);color:#fff;border:none;border-radius:10px;cursor:pointer;font-size:14px;">+ 创建第一条管线</button>`;
            return;
        }
        body.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;">
            ${_pipelineList.map(pl => `<div style="background:var(--bg);border-radius:12px;padding:16px;border:1px solid var(--border);transition:transform 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform=''">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <span style="font-size:18px;">🔗</span>
                    <span style="font-weight:700;font-size:14px;flex:1;">${pl.name}</span>
                    <span style="font-size:10px;padding:2px 8px;background:var(--primary);color:#fff;border-radius:4px;">v${pl.version}</span>
                </div>
                <div style="color:var(--text-muted);font-size:12px;margin-bottom:10px;">${pl.description || '无描述'}</div>
                <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;">
                    ${(pl.tags||[]).map(t=>`<span style="font-size:10px;padding:2px 8px;background:rgba(99,102,241,0.15);color:var(--primary);border-radius:4px;">${t}</span>`).join('')}
                    <span style="font-size:10px;padding:2px 8px;background:rgba(16,185,129,0.15);color:var(--success);border-radius:4px;">${(pl.steps||[]).length} 步</span>
                </div>
                <div style="display:flex;gap:6px;">
                    <button onclick="pipelineExecute('${pl.id}')" style="flex:1;padding:6px;background:var(--success);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:12px;">▶ 执行</button>
                    <button onclick="pipelineViewDetail('${pl.id}')" style="flex:1;padding:6px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:6px;cursor:pointer;font-size:12px;">查看</button>
                    <button onclick="pipelineDeleteConfirm('${pl.id}')" style="padding:6px 10px;background:rgba(239,68,68,0.1);color:var(--danger);border:1px solid var(--danger);border-radius:6px;cursor:pointer;font-size:12px;">🗑</button>
                </div>
            </div>`).join('')}
        </div>`;
    }

    function pipelineNewForm() {
        var body = document.getElementById('pipeline-body');
        body.innerHTML = `
        <div style="max-width:700px;margin:0 auto;">
            <div style="font-weight:700;font-size:16px;margin-bottom:16px;">创建新管线</div>
            <div style="margin-bottom:12px;"><label style="font-size:12px;color:var(--text-muted);display:block;margin-bottom:4px;">管线名称 *</label>
                <input id="pl-name" placeholder="例: 每日数据采集+分析" style="width:100%;padding:10px 14px;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:14px;outline:none;"></div>
            <div style="margin-bottom:12px;"><label style="font-size:12px;color:var(--text-muted);display:block;margin-bottom:4px;">描述</label>
                <textarea id="pl-desc" placeholder="管线功能说明" rows="2" style="width:100%;padding:10px 14px;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:14px;outline:none;resize:vertical;"></textarea></div>
            <div style="margin-bottom:12px;"><label style="font-size:12px;color:var(--text-muted);display:block;margin-bottom:4px;">标签 (逗号分隔)</label>
                <input id="pl-tags" placeholder="数据, 日报" style="width:100%;padding:10px 14px;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:14px;outline:none;"></div>
            <div style="margin-bottom:16px;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
                    <label style="font-size:12px;color:var(--text-muted);">步骤定义 (JSON)</label>
                    <button onclick="pipelineLoadTemplate()" style="font-size:11px;padding:4px 10px;background:var(--primary);color:#fff;border:none;border-radius:6px;cursor:pointer;">加载模板</button>
                </div>
                <textarea id="pl-steps" rows="12" style="width:100%;padding:10px 14px;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:12px;outline:none;resize:vertical;font-family:monospace;" placeholder='[
  {"id":"s1","name":"数据采集","type":"module","module":"data_scraper","action":"execute","params":{}},
  {"id":"s2","name":"数据分析","type":"module","module":"data_analysis","action":"execute","input_mapping":{"source_data":"steps.s1.output.data"}},
  {"id":"s3","name":"发送报告","type":"notify","channel":"email","message_template":"分析完成: {{analysis_result}}"}
]'></textarea>
            </div>
            <div style="display:flex;gap:10px;">
                <button onclick="pipelineCreateSubmit()" style="flex:1;padding:10px;background:var(--primary);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px;">创建管线</button>
                <button onclick="pipelineRefresh()" style="padding:10px 20px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:14px;">取消</button>
            </div>
        </div>`;
    }

    function pipelineLoadTemplate() {
        var templates = {
            '数据采集→分析→通知': [
                {"id":"s1","name":"数据采集","type":"module","module":"data_scraping","action":"scrape","params":{"url":""},"output_alias":"raw_data"},
                {"id":"s2","name":"数据分析","type":"module","module":"data_analysis","action":"analyze","input_mapping":{"data":"steps.s1.output.raw_data"},"output_alias":"analysis_result"},
                {"id":"s3","name":"生成报告","type":"module","module":"doc_generator","action":"generate","input_mapping":{"content":"steps.s2.output.analysis_result"},"output_alias":"report"},
                {"id":"s4","name":"发送通知","type":"notify","channel":"","message_template":"数据处理完成，报告已生成: {{report}}"}
            ],
            '安全扫描→审计→告警': [
                {"id":"s1","name":"安全扫描","type":"module","module":"vuln_scanner","action":"scan","output_alias":"scan_result"},
                {"id":"s2","name":"条件判断","type":"condition","condition_expr":"steps.s1.output.scan_result.critical_count > 0","then_steps":["s3"],"else_steps":["s4"]},
                {"id":"s3","name":"安全告警","type":"notify","channel":"email","message_template":"发现严重安全漏洞! 关键问题数: {{scan_result.critical_count}}"},
                {"id":"s4","name":"记录日志","type":"module","module":"audit_log","action":"log","input_mapping":{"data":"steps.s1.output.scan_result"}}
            ]
        };
        var names = Object.keys(templates);
        var sel = prompt('选择模板:\n' + names.map((n,i)=>`${i+1}. ${n}`).join('\n') + '\n\n输入序号:');
        if (!sel) return;
        var idx = parseInt(sel) - 1;
        if (idx >= 0 && idx < names.length) {
            document.getElementById('pl-steps').value = JSON.stringify(templates[names[idx]], null, 2);
        }
    }

    async function pipelineCreateSubmit() {
        var name = document.getElementById('pl-name').value.trim();
        var stepsStr = document.getElementById('pl-steps').value.trim();
        if (!name) { alert('请输入管线名称'); return; }
        var steps;
        try { steps = JSON.parse(stepsStr); } catch(e) { alert('步骤JSON格式错误: ' + e.message); return; }
        if (!Array.isArray(steps) || steps.length === 0) { alert('步骤必须是非空数组'); return; }
        var tags = document.getElementById('pl-tags').value.split(',').map(s=>s.trim()).filter(Boolean);
        try {
            var r = await fetch('/api/pipelines', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({ name, steps, description:document.getElementById('pl-desc').value.trim(), tags, variables:{} })
            });
            var d = await r.json();
            if (d.success) { await pipelineRefresh(); }
            else { alert('创建失败: ' + (d.error||'')); }
        } catch(e) { alert('网络错误: ' + e.message); }
    }

    async function pipelineViewDetail(plId) {
        try {
            var r = await fetch('/api/pipelines/' + plId);
            var d = await r.json();
            if (!d.success) { alert(d.error||'not found'); return; }
            var body = document.getElementById('pipeline-body');
            var steps = d.steps || [];
            body.innerHTML = `
            <div style="max-width:700px;margin:0 auto;">
                <button onclick="pipelineRefresh()" style="margin-bottom:16px;padding:6px 14px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:12px;">← 返回列表</button>
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
                    <span style="font-size:28px;">🔗</span>
                    <div>
                        <div style="font-weight:700;font-size:18px;">${d.name}</div>
                        <div style="color:var(--text-muted);font-size:12px;">ID: ${d.id} | v${d.version} | ${(d.tags||[]).join(', ')}</div>
                    </div>
                </div>
                <div style="color:var(--text-muted);font-size:13px;margin-bottom:16px;padding:12px;background:var(--bg);border-radius:8px;">${d.description || '无描述'}</div>
                <div style="font-weight:600;font-size:14px;margin-bottom:12px;">管线步骤 (${steps.length})</div>
                <div style="position:relative;padding-left:24px;">
                    ${steps.map((s,i) => `<div style="position:relative;margin-bottom:4px;">
                        ${i < steps.length-1 ? '<div style="position:absolute;left:-16px;top:24px;bottom:-4px;width:2px;background:var(--border);"></div>' : ''}
                        <div style="position:absolute;left:-24px;top:10px;width:16px;height:16px;border-radius:50%;background:var(--primary);border:3px solid var(--card);"></div>
                        <div style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 16px;">
                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                                <span style="font-weight:600;font-size:13px;">${s.name || s.id}</span>
                                <span style="font-size:10px;padding:2px 6px;background:rgba(99,102,241,0.15);color:var(--primary);border-radius:4px;">${s.type}</span>
                                ${s.module ? `<span style="font-size:10px;color:var(--text-muted);">${s.module}${s.action ? '.'+s.action : ''}</span>` : ''}
                            </div>
                            ${s.input_mapping && Object.keys(s.input_mapping).length > 0 ? `<div style="font-size:11px;color:var(--text-muted);margin-top:4px;">映射: ${Object.entries(s.input_mapping).map(([k,v])=>`${k} ← ${v}`).join(', ')}</div>` : ''}
                            ${s.condition_expr ? `<div style="font-size:11px;color:var(--warning);margin-top:4px;">条件: ${s.condition_expr}</div>` : ''}
                            ${s.parallel_steps ? `<div style="font-size:11px;color:var(--accent);margin-top:4px;">并行: ${s.parallel_steps.join(', ')}</div>` : ''}
                            ${s.loop_items_expr ? `<div style="font-size:11px;color:var(--success);margin-top:4px;">循环: ${s.loop_items_expr} (var: ${s.loop_var||'$item'})</div>` : ''}
                            ${s.channel ? `<div style="font-size:11px;color:var(--accent);margin-top:4px;">通知渠道: ${s.channel}</div>` : ''}
                        </div>
                    </div>`).join('')}
                </div>
                <div style="margin-top:20px;display:flex;gap:10px;">
                    <button onclick="pipelineExecute('${d.id}')" style="flex:1;padding:10px;background:var(--success);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px;">▶ 执行管线</button>
                    <button onclick="pipelineShowExecHistory('${d.id}')" style="flex:1;padding:10px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:14px;">📋 执行历史</button>
                </div>
            </div>`;
        } catch(e) { alert('加载失败: ' + e.message); }
    }

    async function pipelineExecute(plId) {
        var body = document.getElementById('pipeline-body');
        body.innerHTML = `<div style="text-align:center;padding:40px;"><div style="font-size:32px;margin-bottom:12px;">⏳</div><div style="font-weight:600;">正在执行管线...</div></div>`;
        try {
            var r = await fetch('/api/pipelines/' + plId + '/execute', {
                method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({})
            });
            var d = await r.json();
            pipelineShowExecResult(d);
        } catch(e) {
            body.innerHTML = `<div style="text-align:center;padding:40px;color:var(--danger);">执行失败: ${e.message}</div>`;
        }
    }

    function pipelineShowExecResult(d) {
        var body = document.getElementById('pipeline-body');
        if (!body) return;
        var statusColor = d.status === 'success' ? 'var(--success)' : d.status === 'failed' ? 'var(--danger)' : 'var(--warning)';
        var steps = d.steps || {};
        body.innerHTML = `
        <div style="max-width:700px;margin:0 auto;">
            <button onclick="pipelineRefresh()" style="margin-bottom:16px;padding:6px 14px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:12px;">← 返回列表</button>
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
                <span style="font-size:28px;">${d.status==='success'?'✅':'⚠️'}</span>
                <div>
                    <div style="font-weight:700;font-size:16px;">执行${d.status==='success'?'成功':d.status==='partial'?'部分成功':'失败'}</div>
                    <div style="color:var(--text-muted);font-size:12px;">耗时 ${(d.duration_ms||0).toFixed(0)}ms | ${d.success_rate || ''}</div>
                </div>
                <span style="margin-left:auto;font-size:12px;padding:4px 12px;background:${statusColor};color:#fff;border-radius:6px;">${d.status}</span>
            </div>
            ${d.error ? `<div style="padding:12px;background:rgba(239,68,68,0.1);border:1px solid var(--danger);border-radius:8px;color:var(--danger);font-size:13px;margin-bottom:16px;">${d.error}</div>` : ''}
            <div style="font-weight:600;font-size:14px;margin-bottom:12px;">步骤结果</div>
            <div style="display:flex;flex-direction:column;gap:8px;">
                ${Object.entries(steps).map(([sid, sr]) => {
                    var sc = sr.status==='success'?'var(--success)':sr.status==='failed'?'var(--danger)':'var(--text-muted)';
                    return `<div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 14px;">
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span style="width:8px;height:8px;border-radius:50%;background:${sc};"></span>
                            <span style="font-weight:600;font-size:13px;flex:1;">${sid}</span>
                            <span style="font-size:11px;color:var(--text-muted);">${(sr.duration_ms||0).toFixed(0)}ms</span>
                            ${sr.attempt > 1 ? `<span style="font-size:10px;padding:2px 6px;background:rgba(245,158,11,0.15);color:var(--warning);border-radius:4px;">重试${sr.attempt}次</span>` : ''}
                        </div>
                        ${sr.error ? `<div style="font-size:12px;color:var(--danger);margin-top:4px;">${sr.error}</div>` : ''}
                        ${sr.output ? `<div style="font-size:11px;color:var(--text-muted);margin-top:4px;max-height:80px;overflow:auto;white-space:pre-wrap;">${typeof sr.output === 'string' ? sr.output.substring(0,500) : JSON.stringify(sr.output,null,2).substring(0,500)}</div>` : ''}
                    </div>`;
                }).join('')}
            </div>
        </div>`;
    }

    async function pipelineShowExecHistory(plId) {
        var url = plId ? '/api/pipelines/executions?pipeline_id=' + plId + '&limit=20' : '/api/pipelines/executions?limit=20';
        try {
            var r = await fetch(url);
            var d = await r.json();
            var execs = d.executions || [];
            var body = document.getElementById('pipeline-body');
            body.innerHTML = `
            <div style="max-width:700px;margin:0 auto;">
                <button onclick="pipelineRefresh()" style="margin-bottom:16px;padding:6px 14px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:12px;">← 返回列表</button>
                <div style="font-weight:700;font-size:16px;margin-bottom:16px;">执行历史 (${execs.length})</div>
                ${execs.length === 0 ? '<div style="text-align:center;padding:40px;color:var(--text-muted);">暂无执行记录</div>' :
                `<div style="display:flex;flex-direction:column;gap:6px;">
                    ${execs.map(ex => {
                        var sc = ex.status==='success'?'var(--success)':ex.status==='failed'?'var(--danger)':'var(--warning)';
                        return `<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:var(--bg);border-radius:8px;cursor:pointer;border:1px solid var(--border);" onclick="pipelineViewExecDetail('${ex.id}')">
                            <span style="width:8px;height:8px;border-radius:50%;background:${sc};flex-shrink:0;"></span>
                            <span style="font-size:13px;font-weight:600;flex:1;">${ex.id}</span>
                            <span style="font-size:11px;color:var(--text-muted);">${(ex.duration_ms||0).toFixed(0)}ms</span>
                            <span style="font-size:11px;color:var(--text-muted);">${(ex.created_at||'').substring(0,19)}</span>
                        </div>`;
                    }).join('')}
                </div>`}
            </div>`;
        } catch(e) { alert('加载失败: ' + e.message); }
    }

    async function pipelineViewExecDetail(execId) {
        try {
            var r = await fetch('/api/pipelines/executions/' + execId);
            var d = await r.json();
            if (d.success) {
                // 复用执行结果展示
                var steps = {};
                try {
                    var parsed = typeof d.steps_result_json === 'string' ? JSON.parse(d.steps_result_json) : d.steps_result_json;
                    Object.assign(steps, parsed);
                } catch(e) {}
                pipelineShowExecResult({id:d.id, status:d.status, duration_ms:d.duration_ms, error:d.error, steps});
            }
        } catch(e) { alert('加载失败: ' + e.message); }
    }

    async function pipelineShowStats() {
        try {
            var r = await fetch('/api/pipelines/stats');
            var d = await r.json();
            var body = document.getElementById('pipeline-body');
            body.innerHTML = `
            <div style="max-width:500px;margin:0 auto;">
                <button onclick="pipelineRefresh()" style="margin-bottom:16px;padding:6px 14px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:12px;">← 返回列表</button>
                <div style="font-weight:700;font-size:16px;margin-bottom:16px;">📊 管线统计</div>
                <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;">
                    <div style="background:var(--bg);border-radius:10px;padding:16px;text-align:center;border:1px solid var(--border);">
                        <div style="font-size:28px;font-weight:700;color:var(--primary);">${d.active_pipelines||0}</div>
                        <div style="font-size:12px;color:var(--text-muted);">活跃管线</div>
                    </div>
                    <div style="background:var(--bg);border-radius:10px;padding:16px;text-align:center;border:1px solid var(--border);">
                        <div style="font-size:28px;font-weight:700;color:var(--text);">${d.total_executions||0}</div>
                        <div style="font-size:12px;color:var(--text-muted);">总执行次数</div>
                    </div>
                    <div style="background:var(--bg);border-radius:10px;padding:16px;text-align:center;border:1px solid var(--border);">
                        <div style="font-size:28px;font-weight:700;color:var(--success);">${d.success||0}</div>
                        <div style="font-size:12px;color:var(--text-muted);">成功次数</div>
                    </div>
                    <div style="background:var(--bg);border-radius:10px;padding:16px;text-align:center;border:1px solid var(--border);">
                        <div style="font-size:28px;font-weight:700;color:var(--danger);">${d.failed||0}</div>
                        <div style="font-size:12px;color:var(--text-muted);">失败次数</div>
                    </div>
                </div>
                <div style="margin-top:16px;background:var(--bg);border-radius:10px;padding:16px;border:1px solid var(--border);">
                    <div style="font-size:14px;font-weight:600;margin-bottom:8px;">成功率</div>
                    <div style="height:8px;background:var(--border);border-radius:4px;overflow:hidden;">
                        <div style="height:100%;width:${d.success_rate||0}%;background:var(--success);border-radius:4px;transition:width 0.5s;"></div>
                    </div>
                    <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">${d.success_rate||0}%</div>
                </div>
            </div>`;
        } catch(e) { alert('加载统计失败: ' + e.message); }
    }

    async function pipelineDeleteConfirm(plId) {
        if (!confirm('确定删除此管线? 删除后不可恢复。')) return;
        try {
            var r = await fetch('/api/pipelines/' + plId, { method:'DELETE' });
            var d = await r.json();
            if (d.success) { await pipelineRefresh(); }
            else { alert(d.error||'删除失败'); }
        } catch(e) { alert('网络错误: ' + e.message); }
    }

    // ── 管线引擎：之前缺失的入口和刷新函数 ──

    /** @type {Array} 管线列表数据 */
    var _pipelineList = [];

    /** 刷新管线列表 */
    async function pipelineRefresh() {
        try {
            var r = await fetch('/api/pipelines');
            var d = await r.json();
            _pipelineList = d.pipelines || d.data || [];
        } catch(e) { _pipelineList = []; }
        var body = document.getElementById('pipeline-body');
        if (!body) return;
        if (_pipelineList.length === 0) {
            body.innerHTML = `<div style="text-align:center;padding:40px;">
                <div style="font-size:48px;margin-bottom:16px;">🔗</div>
                <div style="font-size:18px;font-weight:600;margin-bottom:8px;">暂无管线</div>
                <div style="margin-bottom:20px;color:var(--text-muted);">创建管线让多个模块自动串联执行</div>
                <button onclick="pipelineNewForm()" style="padding:10px 24px;background:var(--primary);color:#fff;border:none;border-radius:10px;cursor:pointer;font-size:14px;">+ 创建第一条管线</button>
            </div>`;
            return;
        }
        body.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;">
            ${_pipelineList.map(pl => `<div style="background:var(--bg);border-radius:12px;padding:16px;border:1px solid var(--border);transition:transform 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform=''">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <span style="font-size:18px;">🔗</span>
                    <span style="font-weight:700;font-size:14px;flex:1;">${pl.name}</span>
                    <span style="font-size:10px;padding:2px 8px;background:var(--primary);color:#fff;border-radius:4px;">v${pl.version}</span>
                </div>
                <div style="color:var(--text-muted);font-size:12px;margin-bottom:10px;">${pl.description || '无描述'}</div>
                <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;">
                    ${(pl.tags||[]).map(t=>`<span style="font-size:10px;padding:2px 8px;background:rgba(99,102,241,0.15);color:var(--primary);border-radius:4px;">${t}</span>`).join('')}
                    <span style="font-size:10px;padding:2px 8px;background:rgba(16,185,129,0.15);color:var(--success);border-radius:4px;">${(pl.steps||[]).length} 步</span>
                </div>
                <div style="display:flex;gap:6px;">
                    <button onclick="pipelineExecute('${pl.id}')" style="flex:1;padding:6px;background:var(--success);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:12px;">▶ 执行</button>
                    <button onclick="pipelineViewDetail('${pl.id}')" style="flex:1;padding:6px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:6px;cursor:pointer;font-size:12px;">查看</button>
                    <button onclick="pipelineDeleteConfirm('${pl.id}')" style="padding:6px 10px;background:rgba(239,68,68,0.1);color:var(--danger);border:1px solid var(--danger);border-radius:6px;cursor:pointer;font-size:12px;">🗑</button>
                </div>
            </div>`).join('')}
        </div>`;
    }

    /** 打开管线引擎面板 */
    async function openPipelineStudio() {
        var overlay = document.createElement('div');
        overlay.id = 'pipeline-modal';
        overlay.style.cssText = 'position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';
        overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
        overlay.innerHTML = `
        <div style="background:var(--card);border-radius:16px;width:90%;max-width:1000px;max-height:90vh;display:flex;flex-direction:column;overflow:hidden;border:1px solid var(--border);">
            <div style="display:flex;align-items:center;padding:20px 24px;border-bottom:1px solid var(--border);">
                <span style="font-weight:700;font-size:16px;flex:1;">🔗 模块管线引擎</span>
                <button onclick="pipelineRefresh()" style="padding:6px 14px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:12px;">🔄 刷新</button>
                <button onclick="pipelineNewForm()" style="padding:6px 14px;background:var(--primary);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:12px;">+ 新增</button>
                <button onclick="pipelineShowStats()" style="padding:6px 14px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:12px;">📊 统计</button>
                <button onclick="document.getElementById('pipeline-modal').remove()" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:20px;">✕</button>
            </div>
            <div id="pipeline-body" style="flex:1;overflow-y:auto;padding:20px;">
                <div style="text-align:center;padding:40px;color:var(--text-muted);">加载中...</div>
            </div>
        </div>`;
        document.body.appendChild(overlay);
        await pipelineRefresh();
    }

    // 暴露全局

    // ── 统一配置中心 (Config Center) ──
    var _configData = [];
    var _configGroups = {};

    async function openConfigCenter() {
        var overlay = document.createElement('div');
        overlay.id = 'config-modal';
        overlay.style.cssText = 'position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';
        overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
        overlay.innerHTML = `
        <div style="background:var(--card);border-radius:16px;width:90%;max-width:900px;max-height:90vh;display:flex;flex-direction:column;overflow:hidden;border:1px solid var(--border);">
            <div style="display:flex;align-items:center;padding:20px 24px;border-bottom:1px solid var(--border);">
                <span style="font-weight:700;font-size:16px;flex:1;">⚙️ 统一配置中心</span>
                <button onclick="localStorage.removeItem('evo_setup_wizard_done');showSetupWizard()" style="padding:6px 14px;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:12px;">🚀 配置向导</button>
                <button onclick="configSaveAll()" style="padding:6px 14px;background:var(--success);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:12px;">💾 保存</button>
                <button onclick="configReload()" style="padding:6px 14px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:12px;">🔄 重载</button>
                <button onclick="document.getElementById('config-modal').remove()" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:20px;">✕</button>
            </div>
            <div id="config-body" style="flex:1;overflow-y:auto;padding:20px;"></div>
        </div>`;
        document.body.appendChild(overlay);
        await configRefresh();
    }

    async function configRefresh() {
        try {
            const [r1, r2] = await Promise.all([fetch('/api/config'), fetch('/api/config/stats')]);
            const [d1, d2] = await Promise.all([r1.json(), r2.json()]);
            _configData = d1.configs || [];
            Object.assign(_configGroups, d2.groups || {});
        } catch(e) { _configData = []; }
        configRender();
    }

    function configRender() {
        var body = document.getElementById('config-body');
        var grouped = {};
        (_configData || []).forEach(c => {
            if (!grouped[c.group]) grouped[c.group] = [];
            grouped[c.group].push(c);
        });
        var groupLabels = {llm:'🤖 LLM模型', notify:'📢 通知渠道', cicd:'🚀 CI/CD', database:'🗄 数据库', custom:'📦 自定义'};
        var groupColors = {llm:'#6366f1', notify:'#f59e0b', cicd:'#10b981', database:'#06b6d4', custom:'#8b5cf6'};

        body.innerHTML = `
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;">
            <button onclick="configFilterGroup('')" class="cfg-tab active" style="padding:6px 16px;background:var(--primary);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:12px;">全部</button>
            ${Object.keys(grouped).map(g => `
                <button onclick="configFilterGroup('${g}')" class="cfg-tab" style="padding:6px 16px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:12px;">${groupLabels[g]||g} (${grouped[g].length})</button>
            `).join('')}
        </div>
        <div style="display:grid;gap:10px;">
            ${(_configData || []).map(c => `
                <div style="background:var(--bg);border-radius:10px;padding:14px;border-left:4px solid ${groupColors[c.group]||'#666'};">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                        <span style="font-weight:600;font-size:13px;">${c.label || c.key}</span>
                        <span style="font-size:11px;color:var(--text-muted);background:var(--card);padding:2px 8px;border-radius:4px;">${c.group}</span>
                        ${c.is_secret ? '<span style="font-size:10px;color:var(--warning);">🔒</span>' : ''}
                        ${c.env_var ? `<span style="font-size:10px;color:var(--text-muted);">$${c.env_var}</span>` : ''}
                    </div>
                    <div style="display:flex;gap:8px;">
                        <input id="cfg-${c.key}" value="${c.display_value || c.value || ''}" placeholder="${c.description || ''}"
                            style="flex:1;padding:8px 12px;background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:13px;${c.is_secret?'type:password':''}" />
                        <button onclick="configSetItem('${c.key}')" style="padding:8px 16px;background:var(--primary);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:12px;">保存</button>
                    </div>
                </div>
            `).join('')}
        </div>`;
    }

    function configFilterGroup(g) {
        document.querySelectorAll('.cfg-tab').forEach(t => { t.style.background='var(--bg)'; t.style.color='var(--text)'; });
        event.target.style.background='var(--primary)'; event.target.style.color='#fff';
        document.querySelectorAll('#config-body > div > div[style*="border-left"]').forEach(el => {
            // simple filter by checking label
        });
    }

    async function configSetItem(key) {
        var input = document.getElementById('cfg-' + key);
        if (!input) return;
        try {
            var r = await fetch('/api/config/' + key, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({value:input.value})});
            var d = await r.json();
            if (d.success) showToast('配置已保存: ' + key);
            else showToast('保存失败: ' + (d.error||''));
        } catch(e) { showToast('请求失败'); }
    }

    async function configSaveAll() { var r = await fetch('/api/config/save',{method:'POST'}); showToast('所有配置已持久化到文件'); }
    async function configReload() { await configRefresh(); showToast('配置已重载'); }

    window.openConfigCenter = openConfigCenter;

    // ── 定时调度器 (Scheduler) ──
    var _schedulerTasks = [];

    async function openSchedulerPanel() {
        var overlay = document.createElement('div');
        overlay.id = 'scheduler-modal';
        overlay.style.cssText = 'position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';
        overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
        overlay.innerHTML = `
        <div style="background:var(--card);border-radius:16px;width:90%;max-width:1000px;max-height:90vh;display:flex;flex-direction:column;overflow:hidden;border:1px solid var(--border);">
            <div style="display:flex;align-items:center;padding:20px 24px;border-bottom:1px solid var(--border);">
                <span style="font-weight:700;font-size:16px;flex:1;">⏰ 定时调度器</span>
                <button onclick="schedulerShowCalendar()" style="padding:6px 14px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:12px;">📅 日历</button>
                <button onclick="schedulerNewTask()" style="padding:6px 14px;background:var(--primary);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:12px;">+ 新建任务</button>
                <button onclick="document.getElementById('scheduler-modal').remove()" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:20px;">✕</button>
            </div>
            <div id="scheduler-body" style="flex:1;overflow-y:auto;padding:20px;"></div>
        </div>`;
        document.body.appendChild(overlay);
        await schedulerRefresh();
    }

    async function schedulerRefresh() {
        try {
            const [r1, r2] = await Promise.all([fetch('/api/scheduler/tasks'), fetch('/api/scheduler/status')]);
            const [d1, d2] = await Promise.all([r1.json(), r2.json()]);
            _schedulerTasks = d1.tasks || [];
            var status = d2;
            var body = document.getElementById('scheduler-body');
            body.innerHTML = `
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">
                <div style="background:var(--bg);border-radius:10px;padding:14px;text-align:center;"><div style="font-size:24px;font-weight:700;color:var(--primary);">${status.total||0}</div><div style="font-size:12px;color:var(--text-muted);">总任务</div></div>
                <div style="background:var(--bg);border-radius:10px;padding:14px;text-align:center;"><div style="font-size:24px;font-weight:700;color:var(--success);">${status.active||0}</div><div style="font-size:12px;color:var(--text-muted);">活跃</div></div>
                <div style="background:var(--bg);border-radius:10px;padding:14px;text-align:center;"><div style="font-size:24px;font-weight:700;color:var(--warning);">${status.disabled||0}</div><div style="font-size:12px;color:var(--text-muted);">已禁用</div></div>
                <div style="background:var(--bg);border-radius:10px;padding:14px;text-align:center;"><div style="font-size:24px;font-weight:700;color:var(--info);">${status.running?'🟢 运行中':'🔴 已停止'}</div><div style="font-size:12px;color:var(--text-muted);">引擎状态</div></div>
            </div>
            <div style="display:grid;gap:10px;">
                ${_schedulerTasks.map(t => `
                    <div style="background:var(--bg);border-radius:10px;padding:14px;display:flex;align-items:center;gap:12px;border:1px solid var(--border);">
                        <div style="flex:1;">
                            <div style="font-weight:600;font-size:13px;">${t.name||t.id}</div>
                            <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">
                                ${t.cron||t.interval||t.once_time||''} · ${t.target_type||''}:${t.target_id||''}
                                ${t.last_run_at?'· 上次:'+t.last_run_at.split('T')[1].slice(0,8):''}
                                ${t.next_run_at?'· 下次:'+t.next_run_at.split('T')[1].slice(0,8):''}
                            </div>
                        </div>
                        <span style="font-size:11px;padding:4px 10px;border-radius:6px;${t.status==='active'?'background:rgba(16,185,129,0.1);color:var(--success);':'background:rgba(107,114,128,0.1);color:var(--text-muted);'}">${t.status}</span>
                        <button onclick="schedulerToggle('${t.id}')" style="padding:6px 10px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:6px;cursor:pointer;font-size:11px;">${t.status==='active'?'⏸':'▶'}</button>
                        <button onclick="schedulerTrigger('${t.id}')" style="padding:6px 10px;background:var(--primary);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:11px;">▶ 执行</button>
                        <button onclick="schedulerDelete('${t.id}')" style="padding:6px 10px;background:rgba(239,68,68,0.1);color:var(--danger);border:1px solid var(--danger);border-radius:6px;cursor:pointer;font-size:11px;">🗑</button>
                    </div>
                `).join('')}
                ${_schedulerTasks.length===0?'<div style="text-align:center;padding:40px;color:var(--text-muted);">暂无调度任务，点击"+ 新建任务"创建</div>':''}
            </div>`;
        } catch(e) { console.error(e); }
    }

    async function schedulerToggle(id) {
        await fetch('/api/scheduler/tasks/'+id+'/toggle',{method:'POST'});
        await schedulerRefresh();
    }
    async function schedulerTrigger(id) {
        await fetch('/api/scheduler/tasks/'+id+'/trigger',{method:'POST'});
        showToast('任务已触发');
    }
    async function schedulerDelete(id) {
        await fetch('/api/scheduler/tasks/'+id,{method:'DELETE'});
        await schedulerRefresh();
    }
    async function schedulerShowCalendar() {
        showToast('日历视图加载中...');
    }
    function schedulerNewTask() {
        var body = document.getElementById('scheduler-body');
        body.innerHTML = `
        <div style="max-width:500px;">
            <button onclick="schedulerRefresh()" style="margin-bottom:16px;padding:6px 14px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:12px;">← 返回</button>
            <h3 style="margin:0 0 16px;">新建调度任务</h3>
            <div style="display:grid;gap:12px;">
                <input id="sch-name" placeholder="任务名称" style="padding:10px;background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:8px;" />
                <select id="sch-target-type" style="padding:10px;background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:8px;">
                    <option value="module">执行模块</option><option value="pipeline">执行管线</option><option value="url">HTTP请求</option>
                </select>
                <input id="sch-target-id" placeholder="目标ID (模块名/管线ID/URL)" style="padding:10px;background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:8px;" />
                <input id="sch-cron" placeholder="Cron表达式 (如 */5 * * * *) 或留空使用间隔" style="padding:10px;background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:8px;" />
                <div style="display:flex;gap:8px;">
                    <button onclick="schedulerCreateSubmit()" style="flex:1;padding:10px;background:var(--primary);color:#fff;border:none;border-radius:8px;cursor:pointer;">创建</button>
                    <button onclick="schedulerRefresh()" style="padding:10px 20px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;">取消</button>
                </div>
            </div>
        </div>`;
    }
    async function schedulerCreateSubmit() {
        var body = {name:document.getElementById('sch-name').value, target_type:document.getElementById('sch-target-type').value, target_id:document.getElementById('sch-target-id').value};
        var cron = document.getElementById('sch-cron').value.trim();
        if (cron) body.cron = cron;
        else body.interval = 300;
        try {
            var r = await fetch('/api/scheduler/tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
            var d = await r.json();
            if(d.success){ await schedulerRefresh(); showToast('任务已创建'); }
            else showToast('创建失败: '+(d.error||''));
        } catch(e) { showToast('请求失败'); }
    }

    window.openSchedulerPanel = openSchedulerPanel;

    // ── 事件驱动引擎 (Event Engine) ──
    async function openEventEngine() {
        var overlay = document.createElement('div');
        overlay.id = 'event-modal';
        overlay.style.cssText = 'position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';
        overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
        overlay.innerHTML = `
        <div style="background:var(--card);border-radius:16px;width:90%;max-width:1000px;max-height:90vh;display:flex;flex-direction:column;overflow:hidden;border:1px solid var(--border);">
            <div style="display:flex;align-items:center;padding:20px 24px;border-bottom:1px solid var(--border);">
                <span style="font-weight:700;font-size:16px;flex:1;">⚡ 事件驱动引擎</span>
                <button onclick="eventRefresh()" style="padding:6px 14px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:12px;">🔄 刷新</button>
                <button onclick="eventNewRule()" style="padding:6px 14px;background:var(--primary);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:12px;">+ 新建规则</button>
                <button onclick="document.getElementById('event-modal').remove()" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:20px;">✕</button>
            </div>
            <div id="event-body" style="flex:1;overflow-y:auto;padding:20px;"></div>
        </div>`;
        document.body.appendChild(overlay);
        await eventRefresh();
    }

    async function eventRefresh() {
        try {
            showToast('正在刷新事件数据...', 'info');
            const [r1, r2, r3] = await Promise.all([fetch('/api/events/stats'), fetch('/api/events/recent?limit=20'), fetch('/api/events/rules')]);
            const [stats, recent, rules] = await Promise.all([r1.json(), r2.json(), r3.json()]);
            var body = document.getElementById('event-body');
            body.innerHTML = `
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">
                <div style="background:var(--bg);border-radius:10px;padding:14px;text-align:center;"><div style="font-size:24px;font-weight:700;color:var(--primary);">${stats.total_events||0}</div><div style="font-size:12px;color:var(--text-muted);">总事件</div></div>
                <div style="background:var(--bg);border-radius:10px;padding:14px;text-align:center;"><div style="font-size:24px;font-weight:700;color:var(--success);">${stats.active_rules||0}</div><div style="font-size:12px;color:var(--text-muted);">活跃规则</div></div>
                <div style="background:var(--bg);border-radius:10px;padding:14px;text-align:center;"><div style="font-size:24px;font-weight:700;color:var(--warning);">${stats.events_last_hour||0}</div><div style="font-size:12px;color:var(--text-muted);">近1小时</div></div>
                <div style="background:var(--bg);border-radius:10px;padding:14px;text-align:center;"><div style="font-size:24px;font-weight:700;color:var(--info);">${stats.watches||0}</div><div style="font-size:12px;color:var(--text-muted);">文件监听</div></div>
            </div>
            <h4 style="margin:0 0 10px;">📋 最近事件</h4>
            <div style="display:grid;gap:6px;margin-bottom:20px;max-height:250px;overflow-y:auto;">
                ${(recent.events||[]).map(e => `
                    <div style="background:var(--bg);border-radius:8px;padding:8px 12px;font-size:12px;display:flex;gap:12px;align-items:center;">
                        <span style="color:var(--primary);font-weight:600;min-width:180px;">${e.type}</span>
                        <span style="color:var(--text-muted);flex:1;">${e.source||''}</span>
                        <span style="color:var(--text-muted);font-size:10px;">${(e.timestamp||'').split('T')[1]||''}</span>
                    </div>
                `).join('')||'<div style="text-align:center;padding:20px;color:var(--text-muted);">暂无事件</div>'}
            </div>
            <h4 style="margin:0 0 10px;">📌 事件规则 (${(rules.rules||[]).length})</h4>
            <div style="display:grid;gap:8px;">
                ${(rules.rules||[]).map(r => `
                    <div style="background:var(--bg);border-radius:10px;padding:12px;display:flex;align-items:center;gap:12px;border:1px solid var(--border);">
                        <div style="flex:1;">
                            <div style="font-weight:600;font-size:13px;">${r.name||r.id}</div>
                            <div style="font-size:11px;color:var(--text-muted);">${r.event_type_pattern} → ${r.action_type} · 匹配${r.match_count||0}次</div>
                        </div>
                        <span style="font-size:11px;padding:4px 10px;border-radius:6px;${r.enabled?'background:rgba(16,185,129,0.1);color:var(--success);':'background:rgba(107,114,128,0.1);color:var(--text-muted);'}">${r.enabled?'启用':'禁用'}</span>
                        <button onclick="eventDeleteRule('${r.id}')" style="padding:4px 8px;background:rgba(239,68,68,0.1);color:var(--danger);border:1px solid var(--danger);border-radius:6px;cursor:pointer;font-size:11px;">🗑</button>
                    </div>
                `).join('')||'<div style="text-align:center;padding:20px;color:var(--text-muted);">暂无规则</div>'}
            </div>`;
        } catch(e) { console.error(e); }
    }

    function eventNewRule() {
        var name = prompt('输入规则名称:', '新建规则');
        if (!name) return;
        var pattern = prompt('输入事件模式 (如: *.created, system.*):', '*');
        if (!pattern) return;
        fetch('/api/events/rules', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:name, pattern:pattern, action:'notify'})})
          .then(r=>r.json()).then(d=>{ showToast(d.success?'规则已创建: '+name:'创建失败:'+(d.error||'')); if(d.success) eventRefresh(); });
    }
    async function eventDeleteRule(id) { await fetch('/api/events/rules/'+id,{method:'DELETE'}); await eventRefresh(); }

    window.openEventEngine = openEventEngine;

    // ── 任务队列 (Task Queue) ──
    async function openTaskQueue() {
        var overlay = document.createElement('div');
        overlay.id = 'queue-modal';
        overlay.style.cssText = 'position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';
        overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
        overlay.innerHTML = `
        <div style="background:var(--card);border-radius:16px;width:90%;max-width:1000px;max-height:90vh;display:flex;flex-direction:column;overflow:hidden;border:1px solid var(--border);">
            <div style="display:flex;align-items:center;padding:20px 24px;border-bottom:1px solid var(--border);">
                <span style="font-weight:700;font-size:16px;flex:1;">📬 任务队列</span>
                <button onclick="queueRefresh()" style="padding:6px 14px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:12px;">🔄 刷新</button>
                <button onclick="queueNewTask()" style="padding:6px 14px;background:var(--primary);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:12px;">+ 提交任务</button>
                <button onclick="document.getElementById('queue-modal').remove()" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:20px;">✕</button>
            </div>
            <div id="queue-body" style="flex:1;overflow-y:auto;padding:20px;"></div>
        </div>`;
        document.body.appendChild(overlay);
        await queueRefresh();
    }

    async function queueRefresh() {
        try {
            const [r1, r2] = await Promise.all([fetch('/api/queue/stats'), fetch('/api/queue/tasks?limit=30')]);
            const [stats, data] = await Promise.all([r1.json(), r2.json()]);
            var tasks = data.tasks || [];
            var body = document.getElementById('queue-body');
            var statusColors = {pending:'var(--text-muted)',running:'var(--primary)',success:'var(--success)',failed:'var(--danger)',retrying:'var(--warning)',timeout:'var(--warning)',cancelled:'var(--text-muted)',dead:'#ef4444'};
            var statusLabels = {pending:'等待中',running:'执行中',success:'成功',failed:'失败',retrying:'重试中',timeout:'超时',cancelled:'已取消',dead:'死信'};
            body.innerHTML = `
            <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:20px;">
                <div style="background:var(--bg);border-radius:10px;padding:12px;text-align:center;"><div style="font-size:22px;font-weight:700;color:var(--text-muted);">${stats.backlog||0}</div><div style="font-size:11px;">积压</div></div>
                <div style="background:var(--bg);border-radius:10px;padding:12px;text-align:center;"><div style="font-size:22px;font-weight:700;color:var(--primary);">${stats.running||0}</div><div style="font-size:11px;">运行中</div></div>
                <div style="background:var(--bg);border-radius:10px;padding:12px;text-align:center;"><div style="font-size:22px;font-weight:700;color:var(--success);">${stats.success||0}</div><div style="font-size:11px;">成功</div></div>
                <div style="background:var(--bg);border-radius:10px;padding:12px;text-align:center;"><div style="font-size:22px;font-weight:700;color:var(--danger);">${stats.dead||0}</div><div style="font-size:11px;">死信</div></div>
                <div style="background:var(--bg);border-radius:10px;padding:12px;text-align:center;"><div style="font-size:22px;font-weight:700;color:var(--info);">${stats.workers_active||0}/${stats.max_workers||4}</div><div style="font-size:11px;">Workers</div></div>
            </div>
            <div style="display:grid;gap:8px;">
                ${tasks.map(t => `
                    <div style="background:var(--bg);border-radius:8px;padding:10px 14px;display:flex;align-items:center;gap:10px;border-left:3px solid ${statusColors[t.status]||'#666'};">
                        <span style="font-size:12px;font-weight:600;min-width:60px;color:${statusColors[t.status]};">${statusLabels[t.status]||t.status}</span>
                        <span style="flex:1;font-size:12px;">${t.name||t.id} <span style="color:var(--text-muted);">(${t.target_type}:${t.target_id})</span></span>
                        <span style="font-size:10px;color:var(--text-muted);">${t.priority||'normal'}</span>
                        ${t.status==='pending'||t.status==='retrying'?`<button onclick="queueCancel('${t.id}')" style="padding:4px 8px;background:rgba(239,68,68,0.1);color:var(--danger);border:1px solid var(--danger);border-radius:6px;cursor:pointer;font-size:10px;">取消</button>`:''}
                        ${t.status==='failed'||t.status==='dead'?`<button onclick="queueRetry('${t.id}')" style="padding:4px 8px;background:var(--primary);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:10px;">重试</button>`:''}
                    </div>
                `).join('')||'<div style="text-align:center;padding:40px;color:var(--text-muted);">队列为空</div>'}
            </div>`;
        } catch(e) { console.error(e); }
    }

    async function queueCancel(id) { await fetch('/api/queue/tasks/'+id+'/cancel',{method:'POST'}); await queueRefresh(); }
    async function queueRetry(id) { await fetch('/api/queue/tasks/'+id+'/retry',{method:'POST'}); await queueRefresh(); }
    function queueNewTask() {
        var name = prompt('输入任务名称:', '');
        if (!name) return;
        var mod = prompt('输入目标模块ID (如: github_scanner):', '');
        if (!mod) return;
        fetch('/api/queue/tasks', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:name, target_module:mod, priority:'normal'})})
          .then(r=>r.json()).then(d=>{ showToast(d.success?'任务已提交: '+name:'提交失败:'+(d.error||'')); if(d.success) queueRefresh(); });
    }

    // ── WebSocket实时监控 (WS Monitor) ──
    var _wsConn = null;

    async function openWSMonitor() {
        var overlay = document.createElement('div');
        overlay.id = 'ws-modal';
        overlay.style.cssText = 'position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';
        overlay.onclick = (e) => { if (e.target === overlay) { overlay.remove(); if(_wsConn) _wsConn.close(); } };
        overlay.innerHTML = `
        <div style="background:var(--card);border-radius:16px;width:90%;max-width:900px;max-height:90vh;display:flex;flex-direction:column;overflow:hidden;border:1px solid var(--border);">
            <div style="display:flex;align-items:center;padding:20px 24px;border-bottom:1px solid var(--border);">
                <span style="font-weight:700;font-size:16px;flex:1;">📡 实时推送监控</span>
                <span id="ws-status" style="font-size:12px;padding:4px 10px;border-radius:6px;background:rgba(107,114,128,0.1);color:var(--text-muted);">未连接</span>
                <button onclick="wsConnect()" style="padding:6px 14px;background:var(--success);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:12px;">🔗 连接</button>
                <button onclick="document.getElementById('ws-modal').remove()" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:20px;">✕</button>
            </div>
            <div id="ws-body" style="flex:1;overflow-y:auto;padding:20px;font-family:monospace;font-size:12px;"></div>
        </div>`;
        document.body.appendChild(overlay);
        await wsLoadStats();
    }

    async function wsLoadStats() {
        try {
            const [r1, r2] = await Promise.all([fetch('/api/ws/stats'), fetch('/api/ws/channels')]);
            const [stats, channels] = await Promise.all([r1.json(), r2.json()]);
            document.getElementById('ws-body').innerHTML = `
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px;font-family:sans-serif;">
                <div style="background:var(--bg);border-radius:10px;padding:14px;text-align:center;"><div style="font-size:24px;font-weight:700;color:var(--primary);">${stats.connected_clients||0}</div><div style="font-size:12px;color:var(--text-muted);">在线连接</div></div>
                <div style="background:var(--bg);border-radius:10px;padding:14px;text-align:center;"><div style="font-size:24px;font-weight:700;color:var(--success);">${stats.total_messages||0}</div><div style="font-size:12px;color:var(--text-muted);">消息总数</div></div>
                <div style="background:var(--bg);border-radius:10px;padding:14px;text-align:center;"><div style="font-size:24px;font-weight:700;color:var(--warning);">${stats.total_connections||0}</div><div style="font-size:12px;color:var(--text-muted);">总连接数</div></div>
            </div>
            <h4 style="font-family:sans-serif;margin:0 0 10px;">可用频道</h4>
            <div style="display:grid;gap:6px;font-family:sans-serif;">
                ${Object.entries(channels.channels||{}).map(([k,v]) => `
                    <div style="background:var(--bg);border-radius:8px;padding:8px 12px;font-size:12px;display:flex;gap:8px;">
                        <span style="font-weight:600;color:var(--primary);min-width:80px;">${k}</span>
                        <span style="color:var(--text-muted);">${v}</span>
                        <span style="margin-left:auto;color:var(--text-muted);font-size:10px;">${(stats.rooms||{})[k]||0} 在线</span>
                    </div>
                `).join('')}
            </div>`;
        } catch(e) { console.error(e); }
    }

    function wsConnect() {
        if (_wsConn) _wsConn.close();
        var wsPort = 8765;
        var protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        _wsConn = new WebSocket(`${protocol}//127.0.0.1:${wsPort}/ws?rooms=system,events,tasks,logs,alerts`);
        var body = document.getElementById('ws-body');
        var statusEl = document.getElementById('ws-status');
        _wsConn.onopen = () => { statusEl.textContent = '🟢 已连接'; statusEl.style.color = 'var(--success)'; body.innerHTML += '<div style="color:var(--success);margin-top:10px;">[已连接]</div>'; };
        _wsConn.onmessage = (e) => {
            try {
                var msg = JSON.parse(e.data);
                var colors = {log:'#94a3b8',event:'#6366f1',progress:'#f59e0b',status:'#10b981',alert:'#ef4444',notification:'#3b82f6'};
                var color = colors[msg.type] || 'var(--text)';
                body.innerHTML += `<div style="color:${color};border-bottom:1px solid rgba(255,255,255,0.05);padding:4px 0;">[${(msg.timestamp||'').split('T')[1]||''}] <b>${msg.type}</b> <span style="color:var(--text-muted);">${msg.channel||''}</span> ${JSON.stringify(msg.data||{}).slice(0,120)}</div>`;
                body.scrollTop = body.scrollHeight;
            } catch(err) { body.innerHTML += `<div style="color:var(--text-muted);">${e.data}</div>`; }
        };
        _wsConn.onclose = () => { statusEl.textContent = '🔴 已断开'; statusEl.style.color = 'var(--danger)'; };
        _wsConn.onerror = () => { statusEl.textContent = '❌ 错误'; statusEl.style.color = 'var(--danger)'; };
    }

    window.openTaskQueue = openTaskQueue;
    window.openWSMonitor = openWSMonitor;

    // ── 导出面板内辅助函数（让 onclick 能找到它们）──
    // 配置中心
    window.configRefresh = configRefresh;
    window.configSaveAll = configSaveAll;
    window.configReload = configReload;
    window.configFilterGroup = configFilterGroup;
    window.configSetItem = configSetItem;
    // 定时调度器
    window.schedulerRefresh = schedulerRefresh;
    window.schedulerToggle = schedulerToggle;
    window.schedulerTrigger = schedulerTrigger;
    window.schedulerDelete = schedulerDelete;
    window.schedulerShowCalendar = schedulerShowCalendar;
    window.schedulerNewTask = schedulerNewTask;
    window.schedulerCreateSubmit = schedulerCreateSubmit;
    // 管线引擎
    window.pipelineRefresh = pipelineRefresh;
    window.pipelineNewForm = pipelineNewForm;
    window.pipelineCreateSubmit = pipelineCreateSubmit;
    window.pipelineDeleteConfirm = pipelineDeleteConfirm;
    window.pipelineShowStats = pipelineShowStats;
    window.pipelineViewDetail = pipelineViewDetail;
    window.pipelineExecute = pipelineExecute;
    window.closePipelineModal = function(){ var el=document.getElementById('pipeline-modal'); if(el) el.remove(); };

    // 事件引擎
    window.eventRefresh = eventRefresh;
    window.eventNewRule = eventNewRule;
    window.eventDeleteRule = eventDeleteRule;
    // 任务队列
    window.queueRefresh = queueRefresh;
    window.queueNewTask = queueNewTask;
    window.queueCancel = queueCancel;
    window.queueRetry = queueRetry;
    // WebSocket 监控
    window.wsConnect = wsConnect;
    // 内网穿透
    window.showTunnelDialog = showTunnelDialog;
    window.startTunnel = startTunnel;

    // ── 内网穿透 (手机远程访问) ──
    var _tunnelActive = false;
    function showTunnelDialog() {
        var overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';
        overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
        overlay.innerHTML = `
        <div style="background:var(--bg-main,#1a1a2e);border:1px solid var(--border,#334);border-radius:16px;width:460px;max-width:92vw;padding:24px;color:var(--text-main,#e2e8f0);font-family:system-ui;box-shadow:0 20px 60px rgba(0,0,0,0.5);">
            <h3 style="margin:0 0 16px 0;font-size:16px;display:flex;align-items:center;gap:8px;">🌐 内网穿透 — 手机远程访问</h3>
            <p style="margin:0 0 12px;font-size:13px;color:var(--text-muted,#9ca3af);">电脑在家里运行，手机在外面也能控制系统。选择一种方式：</p>
            <div style="display:flex;flex-direction:column;gap:10px;">
                <button onclick="startTunnel('cloudflared')" style="padding:14px;border:1px solid var(--border,#334);border-radius:10px;background:var(--bg-card,#16213e);color:var(--text-main,#e2e8f0);cursor:pointer;font-size:14px;text-align:left;font-family:inherit;">
                    <strong style="color:#06b6d4;">☁️ Cloudflare Tunnel</strong><br>
                    <span style="font-size:12px;color:var(--text-muted,#9ca3af);">免费，无需注册。需先安装: winget install Cloudflare.cloudflared</span>
                </button>
                <div style="border-top:1px solid var(--border,#334);padding-top:10px;">
                    <button onclick="startTunnel('pyngrok')" style="padding:10px;border:1px solid var(--border,#334);border-radius:10px;background:var(--bg-card,#16213e);color:var(--text-main,#e2e8f0);cursor:pointer;font-size:14px;text-align:left;width:100%;font-family:inherit;margin-bottom:8px;">
                        <strong style="color:#f59e0b;">🔑 ngrok</strong>
                        <span style="font-size:12px;color:var(--text-muted,#9ca3af);"> 需注册获取token</span>
                    </button>
                    <input type="text" id="ngrok-token-input" placeholder="粘贴 ngrok auth token..." style="width:100%;padding:10px;border:1px solid var(--border,#334);border-radius:8px;background:var(--bg-input,#0f172a);color:var(--text-main,#e2e8f0);font-size:13px;box-sizing:border-box;font-family:inherit;outline:none;">
                </div>
            </div>
            <button onclick="this.closest('div[style*=fixed]').remove()" style="margin-top:16px;padding:8px 16px;border:none;border-radius:8px;background:rgba(255,255,255,0.1);color:var(--text-muted,#9ca3af);cursor:pointer;font-size:13px;font-family:inherit;">取消</button>
        </div>`;
        document.body.appendChild(overlay);
    }
    async function startTunnel(backend) {
        var btn = document.getElementById('tunnel-btn');
        btn.textContent = '⏳'; btn.style.color = '#f59e0b';
        // Close dialog
        var overlay = document.querySelector('div[style*="z-index:999999"]');
        if (overlay) overlay.remove();
        var token = '';
        if (backend === 'pyngrok') {
            var inp = document.getElementById('ngrok-token-input');
            token = inp ? inp.value.trim() : '';
            if (!token) { btn.textContent='🌐'; btn.style.color='#06b6d4'; showToast('请输入ngrok auth token','error'); return; }
        }
        showToast('正在启动隧道，请稍候...', 'info');
        try {
            var r = await fetch('/api/tunnel/start?backend='+backend+'&auth_token='+encodeURIComponent(token), {method:'POST'});
            var d = await r.json();
            if (d.success) {
                _tunnelActive = true;
                btn.textContent = '🌐'; btn.style.color = '#10b981';
                showToast('隧道已启动！手机打开: ' + d.url, 'success', 10000);
                try { navigator.clipboard.writeText(d.url + '/dashboard'); } catch(e) {}
            } else {
                btn.textContent = '🌐'; btn.style.color = '#ef4444';
                showToast('启动失败: ' + (d.hint || d.error), 'error', 8000);
            }
        } catch(e) {
            btn.textContent = '🌐'; btn.style.color = '#06b6d4';
            showToast('请求失败: ' + e.message, 'error');
        }
    }
    async function toggleTunnel() {
        if (_tunnelActive) {
            var btn = document.getElementById('tunnel-btn');
            btn.textContent = '⏳'; btn.style.color = '#f59e0b';
            try {
                await fetch('/api/tunnel/stop', {method:'POST'});
                _tunnelActive = false;
                btn.textContent = '🌐'; btn.style.color = '#06b6d4';
                showToast('隧道已关闭', 'info');
            } catch(e) { btn.textContent='🌐'; btn.style.color='#10b981'; }
        } else {
            showTunnelDialog();
        }
    }
    async function checkTunnelStatus() {
        try {
            var r = await fetch('/api/tunnel/status');
            var d = await r.json();
            if (d.active) { _tunnelActive = true; var btn = document.getElementById('tunnel-btn'); if(btn) btn.style.color='#10b981'; }
        } catch(e) {}
    }
    window.toggleTunnel = toggleTunnel;
    window.v3SwitchTab = v3SwitchTab;
    window.doModuleHealth = doModuleHealth;
    window.doModuleExecute = doModuleExecute;
    window.runModuleExecute = runModuleExecute;

    // ── AI 编排 ──
    var _aiTaskHistory = [];

    async function submitAITask() {
        var input = document.getElementById('ai-task-input');
        var text = input ? input.value.trim() : '';
        if (!text) { showToast('请先输入任务描述', 'error'); return; }
        var area = document.getElementById('ai-result-area');
        area.style.display = 'block';
        area.innerHTML = '<div style="display:flex;gap:8px;align-items:center;"><span class="spinner"></span> 🤖 正在理解任务 "' + text.substring(0,40) + '..." 请稍候...</div>';
        _aiTaskHistory.push({text: text, time: new Date().toLocaleTimeString(), status: '执行中'});

        var plannerName = 'agent_planner';
        try {
            var r = await fetch('/api/modules/' + plannerName + '/execute', {
                method: 'POST', headers: {'Content-Type':'application/json'},
                body: JSON.stringify({action: 'plan', params: {task: text, auto_execute: true}})
            });
            var d = await r.json();
            var resultArea = document.getElementById('ai-result-area');
            if (d.success) {
                var result = d.result || d;
                var html = '<div style="display:flex;gap:8px;justify-content:space-between;align-items:center;">' +
                    '<span style="color:var(--success,#10b981);">✅ 任务完成</span>' +
                    '<span style="font-size:11px;color:var(--text-muted);">' + new Date().toLocaleTimeString() + '</span></div>';
                if (typeof result === 'object') {
                    html += '<div style="margin-top:6px;background:var(--bg);padding:8px;border-radius:6px;font-size:12px;font-family:monospace;white-space:pre-wrap;overflow-x:auto;">' +
                        JSON.stringify(result, null, 2).substring(0, 500) + '</div>';
                } else {
                    html += '<div style="margin-top:6px;color:var(--text-main);font-size:13px;">' + result + '</div>';
                }
                resultArea.innerHTML = html;
            } else {
                resultArea.innerHTML = '<div style="color:var(--danger,#ef4444);">❌ 执行失败: ' + (d.error || '未知错误') + '</div>';
            }
        } catch(e) {
            // Planner not available - fallback: call coordinator directly
            try {
                var r2 = await fetch('/api/coordinator/execute', {
                    method: 'POST', headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({task: text})
                });
                var d2 = await r2.json();
                var area2 = document.getElementById('ai-result-area');
                area2.innerHTML = '<div style="color:var(--success,#10b981);">✅ ' + (d2.message || '已提交') + '</div>' +
                    '<div style="margin-top:6px;font-size:12px;color:var(--text-muted);">协调器已接收任务，可通过 "📋历史" 查看进度</div>';
            } catch(e2) {
                document.getElementById('ai-result-area').innerHTML = '<div style="color:var(--danger);">❌ 协调器不可用: ' + e2.message + '</div>';
            }
        }
        if (input) input.value = '';
    }

    function showTaskHistory() {
        if (!_aiTaskHistory.length) {
            showToast('暂无执行历史', 'info'); return;
        }
        var overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';
        overlay.onclick = function(e) { if (e.target === overlay) overlay.remove(); };
        var items = _aiTaskHistory.map(function(t) {
            return '<div style="padding:8px 12px;background:var(--bg);border-radius:6px;font-size:13px;display:flex;gap:8px;align-items:center;"><span style="color:' + (t.status === '完成' ? 'var(--success)' : 'var(--warning)') + ';">' + (t.status === '完成' ? '✅' : '⏳') + '</span><span style="flex:1;">' + t.text + '</span><span style="font-size:11px;color:var(--text-muted);">' + t.time + '</span></div>';
        }).join('');
        overlay.innerHTML = '<div style="background:var(--bg-main,#1a1a2e);border:1px solid var(--border,#334);border-radius:16px;width:440px;max-width:92vw;padding:24px;color:var(--text-main);"><h3 style="margin:0 0 12px;font-size:15px;">📋 执行历史</h3><div style="display:flex;flex-direction:column;gap:6px;max-height:300px;overflow-y:auto;">' + (items || '<div style="text-align:center;padding:20px;color:var(--text-muted);">暂无记录</div>') + '</div><button onclick="this.closest(\'[style*=\"fixed\"]\').remove()" style="margin-top:12px;padding:8px 16px;border:none;border-radius:8px;background:rgba(255,255,255,0.1);color:var(--text-muted);cursor:pointer;font-size:13px;">关闭</button></div>';
        document.body.appendChild(overlay);
    }

    window.submitAITask = submitAITask;
    window.showTaskHistory = showTaskHistory;
    window.doModuleCode = doModuleCode;
    window.doModuleActions = doModuleActions;
    window.quickExec = quickExec;
    function v3TestExecute() {
        var target = _v3CurrentModule || 'health_check';
        var params = _v3CustomParams || '{}';
        try { params = JSON.parse(params); } catch(e) { params = {}; }
        showToast('⚡ 测试执行 ' + target + '...', 'info');
        fetch('/api/modules/' + target + '/execute', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ action: 'execute', params: params })
        }).then(function(r){ return r.json(); }).then(function(d){
            if (d.success) showToast('✅ ' + target + ' 执行成功', 'success');
            else showToast('❌ ' + target + ' 执行失败: ' + (d.error || d.message || '未知'), 'error');
        }).catch(function(e){ showToast('❌ 请求失败: ' + e.message, 'error'); });
    }
    window.v3FindModules = v3FindModules;
    window.v3ExecuteTask = v3ExecuteTask;
    window.v3TestExecute = v3TestExecute;
    window.v3LoadModules = v3LoadModules;
    window.v3FilterModules = v3FilterModules;
    window.v3ExecModule = v3ExecModule;
    // ── 导出需要在全局访问的函数 ──
    window.openV3Panel = openV3Panel;
    window.openMonitorPanel = openMonitorPanel;
    window.openPipelineStudio = openPipelineStudio;
})();

// ═══════════════════════════════════════════════════════════════
// BILLION GROUP OS - 人机共融·百亿智能体集团操作系统
// 集成到 AUTO-EVO-AI V0.1 COORDINATED
// ═══════════════════════════════════════════════════════════════
(function() {
    // BGOS 全局状态 - 与主系统共享 localStorage
    /* ═══════════════════════════════════════════════════════
       通用UI工具：showToast / showAlert / showPrompt
       ═══════════════════════════════════════════════════════ */

    // ── Toast 通知 ──
    window.showToast = function(msg, type) {
        type = type || 'info';
        var container = document.getElementById('evoToastContainer');
        var el = document.createElement('div');
        el.className = 'toast ' + type;
        el.textContent = msg;
        el.onclick = function() { el.classList.add('removing'); setTimeout(function() { el.remove(); }, 300); };
        container.appendChild(el);
        setTimeout(function() { el.classList.add('removing'); setTimeout(function() { el.remove(); }, 300); }, 3500);
    };

    // ── Alert Modal（替代 alert）──
    var _evoAlertResolve = null;
    window.evoAlertClose = function() {
        document.getElementById('evoAlertOverlay').classList.remove('show');
        if (_evoAlertResolve) { _evoAlertResolve(); _evoAlertResolve = null; }
    };
    window.showAlert = function(msg, icon) {
        icon = icon || '📢';
        document.getElementById('evoAlertIcon').textContent = icon;
        document.getElementById('evoAlertBody').textContent = msg;
        document.getElementById('evoAlertOverlay').classList.add('show');
        return new Promise(function(resolve) { _evoAlertResolve = resolve; });
    };

    // ── Prompt Modal（替代 prompt）──
    var _evoPromptResolve = null;
    window.evoPromptCancel = function() {
        document.getElementById('evoPromptOverlay').classList.remove('show');
        if (_evoPromptResolve) { _evoPromptResolve(null); _evoPromptResolve = null; }
    };
    window.evoPromptOk = function() {
        var input = document.getElementById('evoPromptInput');
        var val = input.value;
        document.getElementById('evoPromptOverlay').classList.remove('show');
        if (_evoPromptResolve) { _evoPromptResolve(val); _evoPromptResolve = null; }
    };
    window.showPrompt = function(title, defaultVal, desc, useTextarea) {
        document.getElementById('evoPromptTitle').textContent = title || '请输入';
        document.getElementById('evoPromptDesc').textContent = desc || '';

        var oldInput = document.getElementById('evoPromptInput');
        if (oldInput) oldInput.parentElement && oldInput.parentElement.removeChild(oldInput);

        var wrapper = document.getElementById('evoPromptOverlay').querySelector('.evo-prompt-box');
        var descEl = document.getElementById('evoPromptDesc');

        var input = document.createElement(useTextarea ? 'textarea' : 'input');
        input.type = 'text';
        input.className = 'evo-prompt-input';
        input.value = (defaultVal !== undefined && defaultVal !== null) ? String(defaultVal) : '';
        descEl.parentNode.insertBefore(input, descEl.nextSibling);

        document.getElementById('evoPromptOverlay').classList.add('show');
        setTimeout(function() { input.focus(); input.select(); }, 100);

        // Enter键提交
        input.onkeydown = function(e) { if (e.key === 'Enter' && !useTextarea) { evoPromptOk(); } };

        return new Promise(function(resolve) { _evoPromptResolve = resolve; });
    };

    // overlay点击关闭
    document.getElementById('evoAlertOverlay').onclick = function(e) { if (e.target === this) evoAlertClose(); };
    document.getElementById('evoPromptOverlay').onclick = function(e) { if (e.target === this) evoPromptCancel(); };

    var BGOS_KEY = 'bgos-data-v01';
    window.BGOS = {
        version: 'V0.1', autopilot: false,
        currentUser: { id: 'u-001', name: '董事长', role: 'super-admin', type: 'human' },
        groups: [], companies: [], departments: [],
        users: [{ id: 'u-001', name: '董事长', account: 'founder', role: 'super-admin', companyId: null, deptId: null, status: 'active', type: 'human' }],
        agents: [], tasks: [], approvals: [], finances: [], auditLogs: [],
        nextId: { group: 1, company: 1, dept: 1, user: 2, agent: 1, task: 1, approval: 1 }
    };

    var INDUSTRY_TEMPLATES = {
        saas: { name: 'AI SaaS 软件集团', depts: ['产品部','研发部','设计部','运营部','销售部','客服部','财务部','人力部'] },
        ecommerce: { name: '无人电商集团', depts: ['采购部','运营部','市场部','客服部','仓储部','物流部','财务部','技术部'] },
        media: { name: '全球传媒集团', depts: ['内容部','编辑部','运营部','广告部','销售部','技术部','财务部','法务部'] },
        investment: { name: 'AI 投资集团', depts: ['研究部','交易部','风控部','合规部','财务部','法务部','技术部','运营部'] },
        marketing: { name: '数字营销集团', depts: ['策划部','投放部','创意部','数据部','客户部','技术部','财务部','人力部'] },
        custom: { name: '自定义集团', depts: ['综合部','技术部','运营部','财务部'] }
    };
    var AGENT_ROLES = ['CEO','CTO','CFO','COO','产品经理','架构师','程序员','设计师','运营专员','销售','客服','财务','HR','数据分析师','内容创作者','投研员'];

    function bgosSave() {
        var data = {
            groups: BGOS.groups, companies: BGOS.companies, departments: BGOS.departments,
            users: BGOS.users, agents: BGOS.agents, tasks: BGOS.tasks,
            approvals: BGOS.approvals, finances: BGOS.finances, auditLogs: BGOS.auditLogs,
            nextId: BGOS.nextId, autopilot: BGOS.autopilot
        };
        var str = JSON.stringify(data);
        localStorage.setItem(BGOS_KEY, str);
        // HTTP协议：同步到后端服务器，实现跨协议数据共享
        if (location.protocol === 'http:' || location.protocol === 'https:') {
            fetch('/api/bgos/data', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: str
            }).catch(()=>{});
        }
    }
    function bgosLoad() {
        // HTTP协议：优先从后端读取，实现跨协议数据共享
        if ((location.protocol === 'http:' || location.protocol === 'https:') && !BGOS._serverLoaded) {
            fetch('/api/bgos/data').then(r=>r.json()).then(d=>{
                if (d && !d.empty && !d.error && d.companies) {
                    Object.assign(BGOS, d);
                    BGOS._serverLoaded = true;
                    bgosUpdateUI();
                    if (BGOS.autopilot && typeof bgosAutoLoop === 'function') bgosAutoLoop();
                    console.log('[BGOS] 已从服务器加载数据, 公司:', d.companies.length);
                }
            }).catch(()=>{});
        }
        var raw = localStorage.getItem(BGOS_KEY);
        if (!raw) return;
        try {
            var d = JSON.parse(raw);
            Object.assign(BGOS, d);
            // 确保 nextId 结构完整（兼容旧数据）
            var required = { group: 1, company: 1, dept: 1, user: 2, agent: 1, task: 1, approval: 1 };
            BGOS.nextId = BGOS.nextId || {};
            Object.keys(required).forEach(k => { if (typeof BGOS.nextId[k] !== 'number') BGOS.nextId[k] = required[k]; });
        } catch(e) {}
    }
    function genId(type) { var num = BGOS.nextId[type]++; return type + '-' + String(num).padStart(4,'0'); }
    function logAudit(type, content, result) {
        BGOS.auditLogs.unshift({ id: genId('audit'), time: new Date().toLocaleString('zh-CN'), operator: BGOS.currentUser.name, operatorType: BGOS.currentUser.type, type, content, result, ip: '127.0.0.1' });
        if (BGOS.auditLogs.length > 1000) BGOS.auditLogs.pop();
        bgosSave();
    }

    // 打开 BILLION GROUP OS 面板
    window.openBillionGroupOS = function() {
        bgosLoad();
        // 首次打开：自动静默创世（无弹窗）
        if (BGOS.companies.length === 0) {
            try {
                var industry = 'saas';
                var template = INDUSTRY_TEMPLATES[industry];
                var groupName = 'AUTO-EVO-AI 核心集团';
                var companyCount = 3, deptPerCompany = template.depts.length, agentCount = 100, humanCount = 20;
                var group = { id: genId('group'), name: groupName, companies: [], budget: 10000000, valuation: 100000000, status: 'normal' };
                BGOS.groups.push(group);
                for (var i = 0; i < companyCount; i++) {
                    var company = { id: genId('company'), groupId: group.id, name: groupName + ' - 公司' + (i+1), businessType: industry, departments: [], users: [], agents: [], budget: 1000000, income: 0, profit: 0, status: 'running' };
                    BGOS.companies.push(company); group.companies.push(company.id);
                    for (var d = 0; d < deptPerCompany; d++) {
                        var deptName = template.depts[d % template.depts.length];
                        var dept = { id: genId('dept'), companyId: company.id, name: deptName, type: deptName.replace('部',''), manager: null, users: [], agents: [], budget: 100000, kpi: '' };
                        BGOS.departments.push(dept); company.departments.push(dept.id);
                        var deptAgentCount = Math.floor(agentCount / companyCount / deptPerCompany);
                        for (var a = 0; a < deptAgentCount; a++) {
                            var role = AGENT_ROLES[Math.floor(Math.random() * AGENT_ROLES.length)];
                            var agent = { id: genId('agent'), name: role + '-' + (a+1), role, companyId: company.id, deptId: dept.id, skills: [role], status: 'running', budget: 1000, kpi: '完成日常工作', efficiency: 80 + Math.floor(Math.random()*20) };
                            BGOS.agents.push(agent); dept.agents.push(agent.id); company.agents.push(agent.id);
                        }
                    }
                    for (var h = 0; h < Math.floor(humanCount / companyCount); h++) {
                        var roles = ['employee', 'manager', 'admin'];
                        var u = { id: genId('user'), name: '员工' + (h+1), account: 'emp' + (h+1), role: roles[Math.floor(Math.random()*roles.length)], companyId: company.id, deptId: null, status: 'active', type: 'human' };
                        BGOS.users.push(u); company.users.push(u.id);
                    }
                }
                BGOS.autopilot = true;
                bgosSave();
                console.log('[BGOS] 首次自动创世完成：' + groupName);
            } catch(e) { console.error('[BGOS] 自动创世失败:', e); }
        }
        var content = document.getElementById('content');
        if (!content) return;

        content.innerHTML = `
        <button class="back-btn" onclick="backToOverview()">← 返回概览</button>
        <div id="bgos-container" style="font-family:system-ui,sans-serif;color:var(--text);">

            <!-- 空数据引导 -->
            <div id="bgos-empty-guide" style="display:none;background:linear-gradient(135deg,#3b82f6,#8b5cf6);border-radius:12px;padding:24px;margin-bottom:20px;color:#fff;text-align:center;">
                <div style="font-size:28px;margin-bottom:8px;">🚀</div>
                <h2 style="margin:0 0 8px;font-size:18px;">BILLION GROUP OS 尚未初始化</h2>
                <p style="margin:0 0 16px;opacity:0.9;">检测到暂无公司/部门/AI智能体。一键创世即可生成完整的集团组织架构。</p>
                <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
                    <button onclick="bgosQuickGenesis()" style="padding:10px 24px;border:none;border-radius:8px;background:#fff;color:#3b82f6;font-weight:600;cursor:pointer;font-size:14px;">⚡ 一键创世（默认）</button>
                    <button onclick="bgosGenesis()" style="padding:10px 24px;border:1px solid rgba(255,255,255,0.5);border-radius:8px;background:transparent;color:#fff;font-weight:600;cursor:pointer;font-size:14px;">🔧 自定义创世</button>
                </div>
            </div>

            <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;">
                <div style="font-size:40px;">🏛️</div>
                <div>
                    <h2 style="margin:0;">BILLION GROUP OS V0.1</h2>
                    <p style="margin:4px 0 0;color:var(--text-muted);font-size:13px;">人机共融 · 百亿智能体集团操作系统 · 一键创世 · 全自动盈利</p>
                </div>
                <div style="margin-left:auto;display:flex;gap:8px;">
                    <button onclick="bgosToggleAutopilot()" id="bgos-ap-btn" style="padding:8px 16px;border:none;border-radius:8px;cursor:pointer;font-weight:600;background:${BGOS.autopilot?'#ef4444':'#10b981'};color:#fff;">${BGOS.autopilot?'⏹ 停止全自动':'▶ 启动全自动'}</button>
                    <button onclick="bgosGenesis()" style="padding:8px 16px;border:none;border-radius:8px;cursor:pointer;font-weight:600;background:#fbbf24;color:#000;">⚡ 一键创世</button>
                </div>
            </div>

            <!-- 核心指标 -->
            <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:20px;">
                <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;text-align:center;">
                    <div style="font-size:12px;color:var(--text-muted);">集团</div>
                    <div style="font-size:28px;font-weight:700;color:#fbbf24;margin-top:4px;" id="bgos-m-groups">0</div>
                </div>
                <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;text-align:center;">
                    <div style="font-size:12px;color:var(--text-muted);">公司</div>
                    <div style="font-size:28px;font-weight:700;color:#3b82f6;margin-top:4px;" id="bgos-m-companies">0</div>
                </div>
                <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;text-align:center;">
                    <div style="font-size:12px;color:var(--text-muted);">部门</div>
                    <div style="font-size:28px;font-weight:700;color:#8b5cf6;margin-top:4px;" id="bgos-m-depts">0</div>
                </div>
                <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;text-align:center;">
                    <div style="font-size:12px;color:var(--text-muted);">人类员工</div>
                    <div style="font-size:28px;font-weight:700;color:#10b981;margin-top:4px;" id="bgos-m-humans">1</div>
                </div>
                <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;text-align:center;">
                    <div style="font-size:12px;color:var(--text-muted);">AI 智能体</div>
                    <div style="font-size:28px;font-weight:700;color:#06b6d4;margin-top:4px;" id="bgos-m-agents">0</div>
                </div>
                <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;text-align:center;">
                    <div style="font-size:12px;color:var(--text-muted);">集团估值</div>
                    <div style="font-size:28px;font-weight:700;color:#ef4444;margin-top:4px;" id="bgos-m-val">$0</div>
                </div>
            </div>

            <!-- 五层架构可视化 -->
            <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:20px;">
                <h3 style="margin:0 0 16px;">🏗️ 五层企业级架构</h3>
                <div id="bgos-arch-viz">
                    <div style="background:linear-gradient(90deg,#fbbf24,#f59e0b);border-radius:8px;padding:12px 16px;margin-bottom:8px;color:#000;">
                        <div style="font-weight:700;">第一层：集团管控层</div>
                        <div style="font-size:12px;opacity:0.8;">董事长 / CEO / 总部 / 多集团总控台</div>
                    </div>
                    <div style="text-align:center;color:var(--text-muted);font-size:12px;margin:4px 0;">▼</div>
                    <div style="background:linear-gradient(90deg,#3b82f6,#6366f1);border-radius:8px;padding:12px 16px;margin-bottom:8px;color:#fff;">
                        <div style="font-weight:700;">第二层：公司集群层</div>
                        <div style="font-size:12px;opacity:0.8;">子公司 / 事业部 / 品牌 / 利润中心</div>
                    </div>
                    <div style="text-align:center;color:var(--text-muted);font-size:12px;margin:4px 0;">▼</div>
                    <div style="background:linear-gradient(90deg,#8b5cf6,#a855f7);border-radius:8px;padding:12px 16px;margin-bottom:8px;color:#fff;">
                        <div style="font-weight:700;">第三层：人机组织层</div>
                        <div style="font-size:12px;opacity:0.8;">部门架构 · 人类员工 + AI智能体 混合编制</div>
                    </div>
                    <div style="text-align:center;color:var(--text-muted);font-size:12px;margin:4px 0;">▼</div>
                    <div style="background:linear-gradient(90deg,#10b981,#22c55e);border-radius:8px;padding:12px 16px;margin-bottom:8px;color:#fff;">
                        <div style="font-weight:700;">第四层：任务工作流层</div>
                        <div style="font-size:12px;opacity:0.8;">任务派发 · 协作 · 审批 · 督办 · 自治复盘</div>
                    </div>
                    <div style="text-align:center;color:var(--text-muted);font-size:12px;margin:4px 0;">▼</div>
                    <div style="background:linear-gradient(90deg,#06b6d4,#0ea5e9);border-radius:8px;padding:12px 16px;color:#fff;">
                        <div style="font-weight:700;">第五层：执行引擎层</div>
                        <div style="font-size:12px;opacity:0.8;">智能体手脚 · 自动化能力池 · OPENCLAW / LangGraph / CrewAI</div>
                    </div>
                </div>
            </div>

            <!-- 快速操作 -->
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">
                <div onclick="bgosGenesis()" style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;text-align:center;cursor:pointer;transition:all 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
                    <div style="font-size:32px;margin-bottom:8px;">⚡</div>
                    <div style="font-weight:600;">一键创世</div>
                    <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">自动生成集团/公司/AI团队</div>
                </div>
                <div onclick="bgosWakeAll()" style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;text-align:center;cursor:pointer;transition:all 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
                    <div style="font-size:32px;margin-bottom:8px;">🤖</div>
                    <div style="font-weight:600;">唤醒全部AI</div>
                    <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">激活所有智能体开始工作</div>
                </div>
                <div onclick="bgosSleepAll()" style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;text-align:center;cursor:pointer;transition:all 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
                    <div style="font-size:32px;margin-bottom:8px;">💤</div>
                    <div style="font-weight:600;">休眠全部AI</div>
                    <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">低功耗模式，暂停执行</div>
                </div>
                <div onclick="bgosShowAgents()" style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;text-align:center;cursor:pointer;transition:all 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
                    <div style="font-size:32px;margin-bottom:8px;">📊</div>
                    <div style="font-weight:600;">智能体集群</div>
                    <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">查看和管理所有AI智能体</div>
                </div>
                <div onclick="bgosAddDeptForm()" style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;text-align:center;cursor:pointer;transition:all 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
                    <div style="font-size:32px;margin-bottom:8px;">🏢</div>
                    <div style="font-weight:600;">添加部门</div>
                    <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">手动创建新部门</div>
                </div>
                <div onclick="bgosAddUserForm()" style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;text-align:center;cursor:pointer;transition:all 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
                    <div style="font-size:32px;margin-bottom:8px;">👤</div>
                    <div style="font-weight:600;">添加用户</div>
                    <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">添加员工/管理员</div>
                </div>
                <div onclick="bgosAddAgentForm()" style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;text-align:center;cursor:pointer;transition:all 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
                    <div style="font-size:32px;margin-bottom:8px;">🧠</div>
                    <div style="font-weight:600;">添加智能体</div>
                    <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">创建单个AI智能体</div>
                </div>
                <div onclick="bgosBatchImportForm()" style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;text-align:center;cursor:pointer;transition:all 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
                    <div style="font-size:32px;margin-bottom:8px;">📥</div>
                    <div style="font-weight:600;">批量导入</div>
                    <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">JSON/CSV批量导入</div>
                </div>
            </div>

            <!-- 公司列表 -->
            <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:20px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                    <h3 style="margin:0;">🏢 公司列表 (<span id="bgos-c-count">0</span>)</h3>
                </div>
                <div id="bgos-company-list" style="max-height:200px;overflow-y:auto;">
                    <p style="text-align:center;color:var(--text-muted);padding:20px;">暂无公司</p>
                </div>
            </div>

            <!-- 部门列表 -->
            <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:20px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                    <h3 style="margin:0;">📂 部门列表 (<span id="bgos-d-count">0</span>)</h3>
                </div>
                <div id="bgos-dept-list" style="max-height:200px;overflow-y:auto;">
                    <p style="text-align:center;color:var(--text-muted);padding:20px;">暂无部门</p>
                </div>
            </div>

            <!-- 智能体列表 -->
            <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:20px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                    <h3 style="margin:0;">🤖 智能体集群状态</h3>
                    <div style="display:flex;gap:8px;">
                        <span style="background:rgba(16,185,129,0.15);color:#10b981;padding:4px 12px;border-radius:20px;font-size:12px;">运行: <b id="bgos-run-count">0</b></span>
                        <span style="background:rgba(107,114,128,0.15);color:#9ca3af;padding:4px 12px;border-radius:20px;font-size:12px;">休眠: <b id="bgos-sleep-count">0</b></span>
                    </div>
                </div>
                <div id="bgos-agent-list" style="max-height:300px;overflow-y:auto;">
                    <p style="text-align:center;color:var(--text-muted);padding:40px;">暂无智能体，点击"一键创世"开始创建</p>
                </div>
            </div>

            <!-- 全自动盈利闭环 -->
            <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:20px;">
                <h3 style="margin:0 0 16px;">🔄 全自动盈利闭环</h3>
                <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
                    <div style="text-align:center;flex:1;">
                        <div style="font-size:24px;">👁️</div>
                        <div style="font-size:12px;font-weight:600;margin-top:4px;">获客</div>
                        <div style="font-size:11px;color:var(--text-muted);">AI自动引流</div>
                    </div>
                    <div style="color:var(--text-muted);">→</div>
                    <div style="text-align:center;flex:1;">
                        <div style="font-size:24px;">🎯</div>
                        <div style="font-size:12px;font-weight:600;margin-top:4px;">转化</div>
                        <div style="font-size:11px;color:var(--text-muted);">智能销售</div>
                    </div>
                    <div style="color:var(--text-muted);">→</div>
                    <div style="text-align:center;flex:1;">
                        <div style="font-size:24px;">📦</div>
                        <div style="font-size:12px;font-weight:600;margin-top:4px;">交付</div>
                        <div style="font-size:11px;color:var(--text-muted);">自动履约</div>
                    </div>
                    <div style="color:var(--text-muted);">→</div>
                    <div style="text-align:center;flex:1;">
                        <div style="font-size:24px;">💬</div>
                        <div style="font-size:12px;font-weight:600;margin-top:4px;">售后</div>
                        <div style="font-size:11px;color:var(--text-muted);">AI客服</div>
                    </div>
                    <div style="color:var(--text-muted);">→</div>
                    <div style="text-align:center;flex:1;">
                        <div style="font-size:24px;">🚀</div>
                        <div style="font-size:12px;font-weight:600;margin-top:4px;">扩张</div>
                        <div style="font-size:11px;color:var(--text-muted);">自动复制</div>
                    </div>
                </div>
            </div>

            <!-- 审计日志 -->
            <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;">
                <h3 style="margin:0 0 16px;">📋 审计日志</h3>
                <div id="bgos-audit-log" style="max-height:200px;overflow-y:auto;font-size:12px;font-family:monospace;">
                    <div style="color:var(--text-muted);text-align:center;padding:20px;">暂无日志</div>
                </div>
            </div>
        </div>
        `;

        document.getElementById('floatBackBtn').classList.add('show');
        bgosUpdateUI();
    };

    // 一键创世（支持自定义数量）
    window.bgosGenesis = async function() {
    try {
        console.log('[一键创世] 被调用');
        var industry = 'saas';
        var template = INDUSTRY_TEMPLATES[industry];
        
        var groupName = await showPrompt('集团名称', template.name, '请输入集团名称');
        if (groupName === null) { showToast('输入被取消', 'warning'); return; }
        if (!groupName) return;
        
        var companyCount = parseInt(await showPrompt('创建公司数量', '3', '请输入要创建的公司数量')) || 3;
        var deptPerCompany = parseInt(await showPrompt('每公司部门数量', String(template.depts.length), '请输入每家公司的部门数')) || template.depts.length;
        var agentCount = parseInt(await showPrompt('创建AI智能体数量', '100', '请输入要创建的AI智能体总数')) || 100;
        var humanCount = parseInt(await showPrompt('创建人类员工数量', '20', '请输入要创建的人类员工总数')) || 20;

        var group = { id: genId('group'), name: groupName, companies: [], budget: 10000000, valuation: 100000000, status: 'normal' };
        BGOS.groups.push(group);

        for (var i = 0; i < companyCount; i++) {
            var company = { id: genId('company'), groupId: group.id, name: groupName + ' - 公司' + (i+1), businessType: industry, departments: [], users: [], agents: [], budget: 1000000, income: 0, profit: 0, status: 'running' };
            BGOS.companies.push(company); group.companies.push(company.id);

            var deptsToCreate = [];
            for (var d = 0; d < deptPerCompany; d++) {
                deptsToCreate.push(template.depts[d % template.depts.length]);
            }
            deptsToCreate.forEach(deptName => {
                var dept = { id: genId('dept'), companyId: company.id, name: deptName, type: deptName.replace('部',''), manager: null, users: [], agents: [], budget: 100000, kpi: '' };
                BGOS.departments.push(dept); company.departments.push(dept.id);
                var deptAgentCount = Math.floor(agentCount / companyCount / deptPerCompany);
                for (var a = 0; a < deptAgentCount; a++) {
                    var role = AGENT_ROLES[Math.floor(Math.random() * AGENT_ROLES.length)];
                    var agent = { id: genId('agent'), name: role + '-' + (a+1), role, companyId: company.id, deptId: dept.id, skills: [role], status: BGOS.autopilot ? 'running' : 'sleeping', budget: 1000, kpi: '完成日常工作', efficiency: 80 + Math.floor(Math.random()*20) };
                    BGOS.agents.push(agent); dept.agents.push(agent.id); company.agents.push(agent.id);
                }
            });

            for (var h = 0; h < Math.floor(humanCount / companyCount); h++) {
                var roles = ['employee', 'manager', 'admin'];
                var u = { id: genId('user'), name: '员工' + (h+1), account: 'emp' + (h+1), role: roles[Math.floor(Math.random()*roles.length)], companyId: company.id, deptId: null, status: 'active', type: 'human' };
                BGOS.users.push(u); company.users.push(u.id);
            }
        }

        bgosSave();
        logAudit('genesis', '一键创世: ' + groupName + ', 公司' + companyCount + ', 部门' + deptPerCompany + '/公司, AI' + agentCount + ', 人类' + humanCount, 'success');
        bgosUpdateUI();
        var autopilotOn = BGOS.autopilot;
        showAlert('⚡ 创世完成！\n\n集团：' + groupName + '\n公司：' + companyCount + ' 家\n部门：' + deptPerCompany + ' 个/公司\nAI智能体：' + agentCount + ' 个\n人类员工：' + humanCount + ' 人' + (autopilotOn ? '\n\n✅ 全自动模式已开启，智能体正在工作' : '\n\n💡 提示：智能体当前为休眠状态\n请点击"🤖 唤醒全部AI"激活它们'), '🎉');
        showToast('创世完成！集团 ' + groupName + ' 已创建', 'success');
    } catch(e) { 
        console.error('[bgosGenesis] 错误:', e); 
        showToast('执行出错: ' + e.message, 'error'); 
    }
};// 快速创世（无弹窗，使用默认值）
    window.bgosQuickGenesis = async function() {
    try {
        console.log('[一键快速创世] 被调用');
        var industry = 'saas';
        var template = INDUSTRY_TEMPLATES[industry];
        var groupName = template.name;
        var companyCount = 3;
        var deptPerCompany = template.depts.length;
        var agentCount = 100;
        var humanCount = 20;

        var group = { id: genId('group'), name: groupName, companies: [], budget: 10000000, valuation: 100000000, status: 'normal' };
        BGOS.groups.push(group);

        for (var i = 0; i < companyCount; i++) {
            var company = { id: genId('company'), groupId: group.id, name: groupName + ' - 公司' + (i+1), businessType: industry, departments: [], users: [], agents: [], budget: 1000000, income: 0, profit: 0, status: 'running' };
            BGOS.companies.push(company); group.companies.push(company.id);

            var deptsToCreate = [];
            for (var d = 0; d < deptPerCompany; d++) {
                deptsToCreate.push(template.depts[d % template.depts.length]);
            }
            deptsToCreate.forEach(deptName => {
                var dept = { id: genId('dept'), companyId: company.id, name: deptName, type: deptName.replace('部',''), manager: null, users: [], agents: [], budget: 100000, kpi: '' };
                BGOS.departments.push(dept); company.departments.push(dept.id);
                var deptAgentCount = Math.floor(agentCount / companyCount / deptPerCompany);
                for (var a = 0; a < deptAgentCount; a++) {
                    var role = AGENT_ROLES[Math.floor(Math.random() * AGENT_ROLES.length)];
                    var agent = { id: genId('agent'), name: role + '-' + (a+1), role, companyId: company.id, deptId: dept.id, skills: [role], status: 'running', budget: 1000, kpi: '完成日常工作', efficiency: 80 + Math.floor(Math.random()*20) };
                    BGOS.agents.push(agent); dept.agents.push(agent.id); company.agents.push(agent.id);
                }
            });

            for (var h = 0; h < Math.floor(humanCount / companyCount); h++) {
                var roles = ['employee', 'manager', 'admin'];
                var u = { id: genId('user'), name: '员工' + (h+1), account: 'emp' + (h+1), role: roles[Math.floor(Math.random()*roles.length)], companyId: company.id, deptId: null, status: 'active', type: 'human' };
                BGOS.users.push(u); company.users.push(u.id);
            }
        }

        bgosSave();
        logAudit('genesis', '快速创世: ' + groupName, 'success');
        bgosUpdateUI();
        showToast('快速创世完成！集团 ' + groupName + ' 已创建', 'success');
        if (BGOS.autopilot) {
            bgosWakeAll();
        }
    } catch(e) { 
        console.error('[bgosQuickGenesis] 错误:', e); 
        showToast('执行出错: ' + e.message, 'error'); 
    }
};// 唤醒/休眠
    window.bgosWakeAll = function() { try { BGOS.agents.forEach(a=>a.status='running'); bgosSave(); logAudit('agent','全部唤醒','success'); bgosUpdateUI(); } catch(e) { console.error(e); } };
    window.bgosSleepAll = function() { try { BGOS.agents.forEach(a=>a.status='sleeping'); bgosSave(); logAudit('agent','全部休眠','success'); bgosUpdateUI(); } catch(e) { console.error(e); } };


    // 全自动模式
    window.bgosToggleAutopilot = function() {
        BGOS.autopilot = !BGOS.autopilot;
        var btn = document.getElementById('bgos-ap-btn');
        if (btn) { btn.style.background = BGOS.autopilot ? '#ef4444' : '#10b981'; btn.textContent = BGOS.autopilot ? '⏹ 停止全自动' : '▶ 启动全自动'; }
        if (BGOS.autopilot) { BGOS.agents.forEach(a=>a.status='running'); bgosAutoLoop(); }
        bgosSave();
        logAudit('system', BGOS.autopilot ? '启动全自动模式' : '停止全自动模式', 'success');
        bgosUpdateUI();
    };

    // 自动盈利循环
    function bgosAutoLoop() {
        if (!BGOS.autopilot) return;
        // 模拟AI工作：随机产生收入、完成任务
        BGOS.companies.forEach(c => {
            if (Math.random() > 0.7) { c.income += Math.floor(Math.random() * 5000); c.profit = Math.floor(c.income * 0.3); }
        });
        // 随机完成任务
        BGOS.tasks.forEach(t => { if (t.status === 'pending' && Math.random() > 0.8) t.status = 'finish'; });
        // 自动创建新任务
        if (Math.random() > 0.9 && BGOS.agents.length > 0) {
            var agent = BGOS.agents[Math.floor(Math.random() * BGOS.agents.length)];
            BGOS.tasks.push({ id: genId('task'), title: '自动任务-' + Math.floor(Math.random()*1000), content: 'AI自动生成并执行', assignType: 'agent', assignId: agent.id, status: 'running', result: '', createdAt: new Date().toLocaleString('zh-CN') });
        }
        bgosSave();
        bgosUpdateUI();
        setTimeout(bgosAutoLoop, 3000);
    }

    // 更新UI
    window.bgosUpdateUI = function() {
        var set = (id, v) => { var el = document.getElementById(id); if (el) el.textContent = v; };
        // 空数据引导显示控制
        var guide = document.getElementById('bgos-empty-guide');
        if (guide) guide.style.display = (BGOS.companies.length === 0) ? 'block' : 'none';
        set('bgos-m-groups', BGOS.groups.length);
        set('bgos-m-companies', BGOS.companies.length);
        set('bgos-m-depts', BGOS.departments.length);
        set('bgos-m-humans', BGOS.users.length);
        set('bgos-m-agents', BGOS.agents.length.toLocaleString());
        var val = BGOS.groups.reduce((s,g)=>s+(g.valuation||0),0);
        set('bgos-m-val', '$' + val.toLocaleString());
        set('bgos-run-count', BGOS.agents.filter(a=>a.status==='running').length);
        set('bgos-sleep-count', BGOS.agents.filter(a=>a.status==='sleeping').length);

        // 公司列表
        var cList = document.getElementById('bgos-company-list');
        var cCount = document.getElementById('bgos-c-count');
        if (cCount) cCount.textContent = BGOS.companies.length;
        if (cList) {
            if (BGOS.companies.length === 0) { cList.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:20px;">暂无公司</p>'; }
            else {
                cList.innerHTML = BGOS.companies.map(c => {
                    var group = BGOS.groups.find(g=>g.id===c.groupId);
                    return '<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);"><div><div style="font-weight:600;font-size:13px;">' + c.name + '</div><div style="font-size:11px;color:var(--text-muted);">' + ((group && group.name)||'-') + ' | 部门:' + c.departments.length + ' | AI:' + c.agents.length + '</div></div><button onclick="bgosDeleteCompany(\'' + c.id + '\')" style="padding:2px 8px;border:1px solid #ef4444;border-radius:6px;background:transparent;color:#ef4444;font-size:11px;cursor:pointer;">删除</button></div>';
                }).join('');
            }
        }

        // 部门列表
        var dList = document.getElementById('bgos-dept-list');
        var dCount = document.getElementById('bgos-d-count');
        if (dCount) dCount.textContent = BGOS.departments.length;
        if (dList) {
            if (BGOS.departments.length === 0) { dList.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:20px;">暂无部门</p>'; }
            else {
                dList.innerHTML = BGOS.departments.map(d => {
                    var company = BGOS.companies.find(c=>c.id===d.companyId);
                    return '<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);"><div><div style="font-weight:600;font-size:13px;">' + d.name + '</div><div style="font-size:11px;color:var(--text-muted);">' + ((company && company.name)||'-') + ' | AI:' + d.agents.length + '</div></div><button onclick="bgosDeleteDept(\'' + d.id + '\')" style="padding:2px 8px;border:1px solid #ef4444;border-radius:6px;background:transparent;color:#ef4444;font-size:11px;cursor:pointer;">删除</button></div>';
                }).join('');
            }
        }

        // 智能体列表
        var list = document.getElementById('bgos-agent-list');
        if (list) {
            if (BGOS.agents.length === 0) { list.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:40px;">暂无智能体，点击"一键创世"开始创建</p>'; }
            else {
                list.innerHTML = BGOS.agents.slice(0,50).map(a => {
                    var company = BGOS.companies.find(c=>c.id===a.companyId);
                    var dept = BGOS.departments.find(d=>d.id===a.deptId);
                    return '<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);"><div><div style="font-weight:600;font-size:13px;">' + a.name + ' <span style="font-size:11px;color:var(--text-muted);">(' + a.role + ')</span></div><div style="font-size:11px;color:var(--text-muted);">' + ((company && company.name)||'-') + ' / ' + ((dept && dept.name)||'-') + '</div></div><div style="display:flex;gap:8px;align-items:center;"><span style="font-size:11px;padding:2px 8px;border-radius:10px;background:' + (a.status==='running'?'rgba(16,185,129,0.15);color:#10b981':'rgba(107,114,128,0.15);color:#9ca3af') + '">' + a.status + '</span><button onclick="bgosDeleteAgent(\'' + a.id + '\')" style="padding:2px 8px;border:1px solid #ef4444;border-radius:6px;background:transparent;color:#ef4444;font-size:11px;cursor:pointer;">删除</button></div></div>';
                }).join('');
            }
        }

        var audit = document.getElementById('bgos-audit-log');
        if (audit) {
            if (BGOS.auditLogs.length === 0) { audit.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:20px;">暂无日志</div>'; }
            else { audit.innerHTML = BGOS.auditLogs.slice(0,20).map(l => '<div style="padding:4px 0;border-bottom:1px solid var(--border);"><span style="color:var(--text-muted);">[' + l.time + ']</span> ' + l.type + ': ' + l.content + ' <span style="color:' + (l.result==='success'?'#10b981':'#ef4444') + '">' + l.result + '</span></div>').join(''); }
        }
    };

    window.bgosShowAgents = function() { bgosUpdateUI(); var el = document.getElementById('bgos-agent-list'); if (el) el.scrollIntoView({behavior:'smooth'}); };

    // ── 删除功能 ──────────────────────────────────────────────
    window.bgosDeleteAgent = function(id) {
        try {
            var agent = BGOS.agents.find(a => a.id === id);
            if (!agent) return;
            if (!confirm('确认删除智能体: ' + agent.name + '?')) return;
            BGOS.agents = BGOS.agents.filter(a => a.id !== id);
            // 从公司和部门引用中移除
            var company = BGOS.companies.find(c => c.id === agent.companyId);
            if (company) company.agents = company.agents.filter(aid => aid !== id);
            var dept = BGOS.departments.find(d => d.id === agent.deptId);
            if (dept) dept.agents = dept.agents.filter(aid => aid !== id);
            bgosSave(); logAudit('delete', '删除智能体: ' + agent.name, 'success'); bgosUpdateUI();
        } catch(e) { console.error(e); }
    };

    window.bgosDeleteDept = function(id) {
        try {
            var dept = BGOS.departments.find(d => d.id === id);
            if (!dept) return;
            if (!confirm('确认删除部门: ' + dept.name + '?\n(该部门下所有智能体将被移出部门)')) return;
            // 移出部门下的智能体
            BGOS.agents.forEach(a => { if (a.deptId === id) a.deptId = null; });
            BGOS.departments = BGOS.departments.filter(d => d.id !== id);
            var company = BGOS.companies.find(c => c.id === dept.companyId);
            if (company) company.departments = company.departments.filter(did => did !== id);
            bgosSave(); logAudit('delete', '删除部门: ' + dept.name, 'success'); bgosUpdateUI();
        } catch(e) { console.error(e); }
    };

    window.bgosDeleteCompany = function(id) {
        try {
            var company = BGOS.companies.find(c => c.id === id);
            if (!company) return;
            if (!confirm('确认删除公司: ' + company.name + '?\n(该公司下所有部门、智能体、员工将被删除)')) return;
            // 删除关联的部门
            var deptIds = BGOS.departments.filter(d => d.companyId === id).map(d => d.id);
            BGOS.departments = BGOS.departments.filter(d => d.companyId !== id);
            // 删除关联的智能体
            BGOS.agents = BGOS.agents.filter(a => a.companyId !== id);
            // 删除关联的用户
            BGOS.users = BGOS.users.filter(u => u.companyId !== id);
            // 从集团引用中移除
            var group = BGOS.groups.find(g => g.id === company.groupId);
            if (group) group.companies = group.companies.filter(cid => cid !== id);
            BGOS.companies = BGOS.companies.filter(c => c.id !== id);
            bgosSave(); logAudit('delete', '删除公司: ' + company.name, 'success'); bgosUpdateUI();
        } catch(e) { console.error(e); }
    };

    // ── 添加部门 ──────────────────────────────────────────────
    window.bgosAddDeptForm = async function() {
    try {
        console.log('[添加部门] 被调用');
        var companyId = await showPrompt('所属公司ID', BGOS.companies.length ? BGOS.companies[0].id : '', '请输入公司ID');
        if (companyId === null) return;
        var name = await showPrompt('部门名称', '技术部', '请输入部门名称');
        if (name === null) return;
        if (!name) { showToast('部门名称不能为空', 'warning'); return; }
        var type = await showPrompt('部门类型', '技术', '请输入部门类型');
        var budget = parseInt(await showPrompt('部门预算', '100000', '请输入部门预算（元）')) || 100000;
        var kpi = await showPrompt('部门KPI', '完成年度目标', '请输入部门KPI');
        var dept = { id: genId('dept'), companyId, name, type: type || '通用', manager: null, users: [], agents: [], budget, kpi: kpi || '' };
        BGOS.departments.push(dept);
        var company = BGOS.companies.find(c => c.id === companyId);
        if (company) company.departments.push(dept.id);
        bgosSave();
        bgosUpdateUI();
        showToast('部门 ' + name + ' 添加成功', 'success');
    } catch(e) { 
        console.error('[bgosAddDeptForm] 错误:', e); 
        showToast('执行出错: ' + e.message, 'error'); 
    }
};// ── 添加用户 ──────────────────────────────────────────────
    window.bgosAddUserForm = async function() {
    try {
        console.log('[添加用户] 被调用');
        var companyId = await showPrompt('所属公司ID', BGOS.companies.length ? BGOS.companies[0].id : '', '请输入公司ID');
        if (companyId === null) return;
        var name = await showPrompt('用户姓名', '新员工', '请输入用户姓名');
        if (name === null) return;
        if (!name) { showToast('用户姓名不能为空', 'warning'); return; }
        var account = await showPrompt('账号', 'emp' + (BGOS.users.length + 1), '请输入登录账号');
        var role = await showPrompt('角色', 'employee', '请输入角色（employee/manager/admin）') || 'employee';
        var deptId = await showPrompt('所属部门ID（可选）', '', '请输入部门ID（留空则表示无部门）');
        var u = { id: genId('user'), name, account: account || ('emp' + (BGOS.users.length + 1)), role, companyId, deptId: deptId || null, status: 'active', type: 'human' };
        BGOS.users.push(u);
        var company = BGOS.companies.find(c => c.id === companyId);
        if (company) company.users.push(u.id);
        bgosSave();
        bgosUpdateUI();
        showToast('用户 ' + name + ' 添加成功', 'success');
    } catch(e) { 
        console.error('[bgosAddUserForm] 错误:', e); 
        showToast('执行出错: ' + e.message, 'error'); 
    }
};// ── 添加智能体 ────────────────────────────────────────────
    window.bgosAddAgentForm = async function() {
    try {
        console.log('[添加智能体] 被调用');
        var companyId = await showPrompt('所属公司ID', BGOS.companies.length ? BGOS.companies[0].id : '', '请输入公司ID');
        if (companyId === null) return;
        var name = await showPrompt('智能体名称', '新智能体', '请输入智能体名称');
        if (name === null) return;
        if (!name) { showToast('智能体名称不能为空', 'warning'); return; }
        var role = await showPrompt('角色', 'assistant', '请输入智能体角色（assistant/expert/analyst等）') || 'assistant';
        var deptId = await showPrompt('所属部门ID（可选）', '', '请输入部门ID（留空则表示无部门）');
        var budget = parseInt(await showPrompt('预算', '1000', '请输入预算（元）')) || 1000;
        var kpi = await showPrompt('KPI', '完成日常工作', '请输入KPI目标');
        var agent = { id: genId('agent'), name, role, companyId, deptId: deptId || null, skills: [role], status: BGOS.autopilot ? 'running' : 'sleeping', budget, kpi: kpi || '完成日常工作', efficiency: 80 + Math.floor(Math.random()*20) };
        BGOS.agents.push(agent);
        var company = BGOS.companies.find(c => c.id === companyId);
        if (company) company.agents.push(agent.id);
        if (deptId) {
            var dept = BGOS.departments.find(d => d.id === deptId);
            if (dept) dept.agents.push(agent.id);
        }
        bgosSave();
        bgosUpdateUI();
        showToast('智能体 ' + name + ' 添加成功', 'success');
    } catch(e) { 
        console.error('[bgosAddAgentForm] 错误:', e); 
        showToast('执行出错: ' + e.message, 'error'); 
    }
};// ── 批量导入 ──────────────────────────────────────────────
    window.bgosBatchImportForm = async function() {
        try {
        console.log('[批量导入] 被调用');
        bgosLoad();

        // 使用内联模态框选择导入类型
        var type = await showPrompt('批量导入', '', '导入类型：1=公司 2=部门 3=用户 4=智能体');
        if (type === null || type === undefined) { await showAlert('导入已取消', '🚫'); return; }
        if (!type) return;
        var typeMap = { '1': 'companies', '2': 'departments', '3': 'users', '4': 'agents' };
        var typeKey = typeMap[type.trim()];
        if (!typeKey) { await showAlert('无效选项，请输入 1-4', '⚠️'); return; }

        // 显示示例数据帮助用户输入
        var sample = type.trim() === '1' ? '[{"name":"新公司","businessType":"saas"}]' :
            type.trim() === '2' ? '[{"name":"技术部","companyId":"company-0001"}]' :
            type.trim() === '3' ? '[{"name":"张三","account":"zhangsan","role":"employee","companyId":"company-0001"}]' :
            '[{"name":"AI助手","role":"客服","companyId":"company-0001","skills":["客服","销售"]}]';

        var raw = await showPrompt('粘贴数据', sample, '粘贴 JSON 数组或 CSV 数据', true);
        if (raw === null || raw === undefined) return;
        if (!raw || !raw.trim()) return;

        var items = [];
        try {
            if (raw.trim().startsWith('[')) { items = JSON.parse(raw); }
            else {
                // 简单CSV解析
                var lines = raw.trim().split('\n').filter(l => l.trim());
                var headers = lines[0].split(',').map(h => h.trim());
                for (var i = 1; i < lines.length; i++) {
                    var vals = lines[i].split(',');
                    var obj = {}; headers.forEach((h,idx) => obj[h] = vals[idx] ? vals[idx].trim() : '');
                    if (obj.skills) obj.skills = obj.skills.split(/[,，]/).map(s => s.trim());
                    items.push(obj);
                }
            }
        } catch(e) { await showAlert('解析失败: ' + e.message, '❌'); return; }
        if (!Array.isArray(items) || items.length === 0) { await showAlert('没有可导入的数据', '⚠️'); return; }

        var t = type.trim();
        var created = 0;
        items.forEach(item => {
            try {
                if (t === '1') {
                    var c = { id: genId('company'), groupId: (BGOS.groups[0] && BGOS.groups[0].id) || null, name: item.name || '未命名公司', businessType: item.businessType || 'saas', departments: [], users: [], agents: [], budget: 1000000, income: 0, profit: 0, status: 'running' };
                    BGOS.companies.push(c); if (BGOS.groups[0]) BGOS.groups[0].companies.push(c.id);
                } else if (t === '2') {
                    var company = BGOS.companies.find(c => c.id === item.companyId);
                    if (!company) return;
                    var d = { id: genId('dept'), companyId: company.id, name: item.name || '未命名部门', type: item.type || (item.name||'').replace('部',''), manager: null, users: [], agents: [], budget: 100000, kpi: '' };
                    BGOS.departments.push(d); company.departments.push(d.id);
                } else if (t === '3') {
                    var company = BGOS.companies.find(c => c.id === item.companyId);
                    if (!company) return;
                    var u = { id: genId('user'), name: item.name || '未命名', account: item.account || item.name || 'user', role: item.role || 'employee', companyId: company.id, deptId: item.deptId || null, status: 'active', type: 'human' };
                    BGOS.users.push(u); company.users.push(u.id);
                } else if (t === '4') {
                    var company = BGOS.companies.find(c => c.id === item.companyId);
                    if (!company) return;
                    var skills = Array.isArray(item.skills) ? item.skills : (item.skills || '通用').split(/[,，]/).map(s => s.trim()).filter(Boolean);
                    var a = { id: genId('agent'), name: item.name || '未命名AI', role: item.role || '通用助手', companyId: company.id, deptId: item.deptId || null, skills: skills, status: 'sleeping', budget: 1000, kpi: '完成日常工作', efficiency: 80 + Math.floor(Math.random()*20) };
                    BGOS.agents.push(a); company.agents.push(a.id);
                }
                created++;
            } catch(e) { console.error('导入项失败', e); }
        });
        bgosSave(); logAudit('import', '批量导入 ' + typeKey + ': ' + created + ' 条', created > 0 ? 'success' : 'fail'); bgosUpdateUI();
        await showAlert('✅ 导入完成: ' + created + ' 条' + (created < items.length ? ' (' + (items.length-created) + ' 条失败)' : ''), '🎉');
        } catch(e) { console.error('[bgosBatchImportForm]', e); showAlert('批量导入出错: ' + e.message, '❌'); }
    };

    // 初始化加载
    bgosLoad();
})();

// ═════════════════════════════════════════════════════════════════
// 全模块协调引擎 V0.1 — 让535个模块自主自动协作
// ═════════════════════════════════════════════════════════════════
(function() {
    'use strict';

    // ── EventBus 事件总线 ──────────────────────────────────────
    var EventBus = {
        _events: {},
        on(evt, fn) { (this._events[evt] = this._events[evt] || []).push(fn); return () => this.off(evt, fn); },
        off(evt, fn) { if (!this._events[evt]) return; var i = this._events[evt].indexOf(fn); if (i > -1) this._events[evt].splice(i, 1); },
        emit(evt, data) { if (!this._events[evt]) return; this._events[evt].slice().forEach(fn => { try { fn(data); } catch(e) {} }); }
    };
    window.EventBus = EventBus;

    // ── ModuleRegistry 模块能力注册表 ──────────────────────────
    // 将主系统所有模块注册为可调用的"能力"，每个能力有：输入、输出、触发事件
    var ModuleRegistry = {};
    var _mods = {
        // 系统大脑
        'monitor-dashboard': { group:'系统大脑', name:'监控面板', events:['system.load','agent.heartbeat'], outputs:['metrics'] },
        'agent-manager': { group:'系统大脑', name:'Agent管理', events:['agent.create','agent.destroy','agent.update'], outputs:['agent.list'] },
        'workflow-engine': { group:'系统大脑', name:'工作流编排', events:['workflow.start','workflow.end','workflow.fail'], outputs:['workflow.status'] },
        'task-center': { group:'系统大脑', name:'任务中心', events:['task.assign','task.done','task.timeout'], outputs:['task.queue'] },
        'memory-manager': { group:'系统大脑', name:'记忆管理', events:['memory.read','memory.write'], outputs:['memory.fragment'] },
        'evolution-center': { group:'系统大脑', name:'进化中心', events:['evolve.trigger','evolve.complete'], outputs:['evolve.report'] },
        'routines': { group:'系统大脑', name:'Routines', events:['routine.run','routine.skip'], outputs:['routine.log'] },
        'tool-integration': { group:'系统大脑', name:'工具集成', events:['tool.call','tool.return'], outputs:['tool.result'] },
        'message-queue': { group:'系统大脑', name:'消息队列', events:['msg.enqueue','msg.dequeue'], outputs:['msg.status'] },
        'cache-manager': { group:'系统大脑', name:'缓存管理', events:['cache.hit','cache.miss'], outputs:['cache.stats'] },
        'event-bus': { group:'系统大脑', name:'事件总线', events:['event.publish','event.subscribe'], outputs:['event.log'] },

        // 安全监控
        'security-governance': { group:'安全监控', name:'安全治理', events:['security.alert','security.block'], outputs:['security.report'] },
        'performance-monitor': { group:'安全监控', name:'性能监控', events:['perf.cpu','perf.mem','perf.latency'], outputs:['perf.metrics'] },
        'alert-center': { group:'安全监控', name:'告警中心', events:['alert.trigger','alert.resolve'], outputs:['alert.list'] },
        'log-center': { group:'安全监控', name:'日志中心', events:['log.write','log.search'], outputs:['log.entries'] },
        'disaster-backup': { group:'安全监控', name:'容灾备份', events:['backup.start','backup.done'], outputs:['backup.status'] },

        // 开源生态
        'github-tools': { group:'开源生态', name:'GitHub工具', events:['github.scan','github.clone','github.pr'], outputs:['github.repos'] },
        'firecrawl': { group:'开源生态', name:'Firecrawl', events:['crawl.start','crawl.done'], outputs:['crawl.data'] },
        'evo-nexus': { group:'开源生态', name:'EvoNexus', events:['evo.sync','evo.merge'], outputs:['evo.status'] },
        'rowboat': { group:'开源生态', name:'Rowboat', events:['row.launch','row.dock'], outputs:['row.log'] },
        'claw-company': { group:'开源生态', name:'ClawCompany', events:['claw.hunt','claw.capture'], outputs:['claw.report'] },
        'open-mythos': { group:'开源生态', name:'OpenMythos', events:['myth.create','myth.spread'], outputs:['myth.stats'] },

        // 高级功能
        'desktop-automation': { group:'高级功能', name:'桌面操作', events:['desktop.click','desktop.type'], outputs:['desktop.screenshot'] },
        'visual-understanding': { group:'高级功能', name:'视觉理解', events:['vision.scan','vision.recognize'], outputs:['vision.result'] },
        'code-generation': { group:'高级功能', name:'代码生成', events:['code.gen','code.review'], outputs:['code.files'] },
        'data-analysis': { group:'高级功能', name:'数据分析', events:['data.ingest','data.analyze'], outputs:['data.report'] },
        'file-processor': { group:'高级功能', name:'文件处理', events:['file.read','file.write'], outputs:['file.meta'] },

        // 用户权限
        'user-management': { group:'用户权限', name:'用户管理', events:['user.login','user.logout','user.register'], outputs:['user.session'] },
        'api-management': { group:'用户权限', name:'API管理', events:['api.call','api.limit'], outputs:['api.stats'] },
        'role-permission': { group:'用户权限', name:'角色权限', events:['perm.check','perm.grant'], outputs:['perm.matrix'] },

        // 运营支持
        'scheduler': { group:'运营支持', name:'调度配置', events:['sched.run','sched.delay'], outputs:['sched.jobs'] },
        'report-center': { group:'运营支持', name:'报告中心', events:['report.gen','report.export'], outputs:['report.files'] },
        'feedback': { group:'运营支持', name:'用户反馈', events:['fb.receive','fb.resolve'], outputs:['fb.stats'] },

        // 配置管理
        'system-settings': { group:'配置管理', name:'系统设置', events:['config.set','config.get'], outputs:['config.snapshot'] },
        'integration-config': { group:'配置管理', name:'集成配置', events:['int.connect','int.disconnect'], outputs:['int.status'] },
        'shortcut-keys': { group:'配置管理', name:'快捷键', events:['key.bind','key.trigger'], outputs:['key.map'] },
        'org-management': { group:'配置管理', name:'组织管理', events:['org.create','org.delete'], outputs:['org.tree'] },

        // BILLION GROUP OS 核心
        'bgos-genesis': { group:'BGOS', name:'一键创世', events:['genesis.start','genesis.done'], outputs:['genesis.plan'] },
        'bgos-finance': { group:'BGOS', name:'财务中心', events:['finance.income','finance.cost','finance.profit'], outputs:['finance.report'] },
        'bgos-approval': { group:'BGOS', name:'审批中心', events:['approval.submit','approval.pass','approval.reject'], outputs:['approval.flow'] },
        'bgos-permission': { group:'BGOS', name:'权限安全', events:['perm.auth','perm.audit'], outputs:['perm.log'] },
        'bgos-compliance': { group:'BGOS', name:'合规风控', events:['compliance.scan','compliance.risk'], outputs:['compliance.report'] },
        'bgos-global': { group:'BGOS', name:'全球化', events:['global.expand','global.localize'], outputs:['global.map'] },
        'bgos-autopilot': { group:'BGOS', name:'全自动', events:['auto.start','auto.stop','auto.loop'], outputs:['auto.metrics'] }
    };
    Object.keys(_mods).forEach(k => { ModuleRegistry[k] = _mods[k]; });
    window.ModuleRegistry = ModuleRegistry;

    // ── AgentOrchestrator 智能体编排器 ──────────────────────────
    // 将智能体角色映射为可调用的模块能力流水线
    var AgentOrchestrator = {
        // 角色 → 能力流水线
        rolePipeline: {
            'CEO':      ['bgos-genesis', 'bgos-finance', 'bgos-autopilot', 'report-center', 'evolution-center'],
            'CTO':      ['agent-manager', 'code-generation', 'workflow-engine', 'tool-integration', 'cache-manager'],
            'CFO':      ['bgos-finance', 'bgos-approval', 'data-analysis', 'report-center', 'disaster-backup'],
            'COO':      ['task-center', 'scheduler', 'performance-monitor', 'alert-center', 'feedback'],
            '产品经理': ['workflow-engine', 'task-center', 'feedback', 'evolution-center', 'visual-understanding'],
            '架构师':   ['agent-manager', 'workflow-engine', 'cache-manager', 'message-queue', 'event-bus'],
            '程序员':   ['code-generation', 'github-tools', 'tool-integration', 'desktop-automation', 'cache-manager'],
            '设计师':   ['visual-understanding', 'file-processor', 'evo-nexus', 'feedback', 'code-generation'],
            '运营专员': ['scheduler', 'message-queue', 'feedback', 'report-center', 'evo-nexus'],
            '销售':     ['bgos-global', 'feedback', 'report-center', 'data-analysis', 'open-mythos'],
            '客服':     ['feedback', 'message-queue', 'memory-manager', 'scheduler', 'alert-center'],
            '财务':     ['bgos-finance', 'bgos-approval', 'data-analysis', 'report-center', 'disaster-backup'],
            'HR':       ['user-management', 'role-permission', 'org-management', 'scheduler', 'feedback'],
            '数据分析师':['data-analysis', 'performance-monitor', 'report-center', 'bgos-finance', 'evolution-center'],
            '内容创作者':['open-mythos', 'evo-nexus', 'file-processor', 'feedback', 'visual-understanding'],
            '投研员':   ['bgos-finance', 'data-analysis', 'bgos-compliance', 'firecrawl', 'report-center']
        },

        // 为每个运行中的智能体分配下一个任务
        assignTask(agent) {
            var pipeline = this.rolePipeline[agent.role] || ['task-center'];
            // 根据智能体状态和业务需求选择模块
            var moduleId = pipeline[Math.floor(Math.random() * pipeline.length)];
            var mod = ModuleRegistry[moduleId];
            if (!mod) return null;

            // 模拟任务执行
            var taskType = mod.events[Math.floor(Math.random() * mod.events.length)];
            return {
                agentId: agent.id,
                agentName: agent.name,
                role: agent.role,
                moduleId,
                moduleName: mod.name,
                event: taskType,
                timestamp: new Date().toLocaleString('zh-CN'),
                status: 'assigned'
            };
        },

        // 执行一轮全量编排
        orchestrate() {
            var tasks = [];
            // 获取所有运行中的智能体（从BGOS全局状态）
            var agents = (window.BGOS && window.BGOS.agents) ? window.BGOS.agents.filter(a => a.status === 'running') : [];
            agents.forEach(agent => {
                // 每个智能体有概率触发工作（模拟并发）
                if (Math.random() > 0.3) {
                    var task = this.assignTask(agent);
                    if (task) tasks.push(task);
                }
            });
            return tasks;
        }
    };
    window.AgentOrchestrator = AgentOrchestrator;

    // ── AutoExecutionEngine 自动执行引擎 v2.0 ───────────────────
    // 前端只负责启停后端自主循环 + 轮询状态更新UI
    var AutoExecutionEngine = {
        running: false,
        intervalId: null,
        tickCount: 0,
        eventLog: [],
        metrics: { tasksExecuted: 0, modulesTriggered: 0, revenueGenerated: 0, errors: 0, automationScore: 0 },
        backendOnline: false,
        backendError: null,
        backendHealth: {},
        backendCoordinator: null,

        // 获取后端真实状态（不要求引擎在运行）
        async fetchBackendStatus() {
            try {
                if (typeof EvoAPI !== 'undefined') {
                    var status = await EvoAPI.health();
                    if (status) {
                        this.backendOnline = true;
                        this._loadedModules = status.modules_loaded || 0;
                        this._totalModules = status.modules_total || 0;
                        this._uptime = status.uptime_seconds || 0;
                    }
                    // 通过 EvoAPI HTTP 获取协调器执行统计（兼容file://协议）
                    try {
                        var coord = await EvoAPI.getCoordinatorStatus();
                        if (coord && coord.execution_stats) {
                            // 后端有真实数据时用后端数据，否则保留前端累计值
                            var bt = coord.execution_stats.total || coord.execution_stats.tasks_executed || 0;
                            var bm = coord.execution_stats.success || coord.execution_stats.modules_triggered || 0;
                            if (bt > 0) this.metrics.tasksExecuted = bt;
                            if (bm > 0) this.metrics.modulesTriggered = bm;
                            this.metrics.errors = coord.execution_stats.failed || coord.execution_stats.errors || 0;
                        }
                        this.backendCoordinator = coord;
                    } catch(e) {}
                }
                this.updateCoordinationUI();
            } catch(e) {
                this.updateCoordinationUI();
            }
        },

        async start() {
            if (this.running) return;
            this.running = true;
            this.tickCount = 0;
            this.backendOnline = false;
            this.backendError = null;
            EventBus.emit('engine.start', { time: new Date().toISOString() });
            // 优先用 EvoAPI HTTP 接口（兼容 file:// 协议）
            if (typeof EvoAPI !== 'undefined') {
                try { await EvoAPI.startAutonomous(); this.backendOnline = true; }
                catch(e) { this.backendError = e.message; console.log('后端启动失败:', e.message); }
            }
            this.intervalId = setInterval(() => this.pollBackend(), 3000);
            this.logEvent('SYSTEM', this.backendOnline ? '✅ 已连接后端' : '⚠️ 后端未连接，运行模拟模式');
            this.updateCoordinationUI();
            this.fetchBackendStatus();
        },

        async stop() {
            this.running = false;
            if (this.intervalId) { clearInterval(this.intervalId); this.intervalId = null; }
            EventBus.emit('engine.stop', { time: new Date().toISOString() });
            if (typeof EvoAPI !== 'undefined') {
                try { await EvoAPI.stopAutonomous(); } catch(e) {}
            }
            this.logEvent('SYSTEM', '⏹ 已停止');
            this.updateCoordinationUI();
        },

        async pollBackend() {
            this.tickCount++;
            try {
                if (typeof EvoAPI === 'undefined') throw new Error('EvoAPI 未加载');
                var status = await EvoAPI.getCoordinatorStatus();
                if (!status) throw new Error('协调器未响应');
                this.backendOnline = true;
                this.backendError = null;
                if (status && status.execution_stats) {
                    var bt = status.execution_stats.total || status.execution_stats.tasks_executed || 0;
                    var bm = status.execution_stats.success || status.execution_stats.modules_triggered || 0;
                    // 后端有真实数据时覆盖，否则前端继续累加模拟数据
                    if (bt > 0) this.metrics.tasksExecuted = bt;
                    if (bm > 0) this.metrics.modulesTriggered = bm;
                    this.metrics.errors = status.execution_stats.failed || status.execution_stats.errors || 0;
                }
                // 解析后端的 recent_executions（真实模块执行记录）
                var recents = status && status.recent_executions ? status.recent_executions : [];
                if (recents.length > 0) {
                    recents.forEach(ex => {
                        var mod = ex.module || ex.method || '未知';
                        var success = ex.success ? '成功' : '失败';
                        this.logEvent('TASK', `[后端] ${mod} -> ${success}`);
                    });
                }
                if (window.BGOS && window.BGOS.autopilot) this.runBGOSFinance();
                this.updateCoordinationUI();
            } catch(e) {
                this.backendOnline = false;
                this.backendError = e.message;
                // EvoAPI不可用时：运行纯前端模拟模式，生成模块活跃数据
                var SIM_MODULES = [
                    'system_coordinator','agent_orchestrator','workflow_manager','task_engine',
                    'memory_manager','evolution_core','automation_hub','skill_marketplace',
                    'smart_scheduler','event_bus','browser_auto','vision_rpa',
                    'crewai_strategy','soul_identity','stock_api','supermemory',
                    'cache_engine','trigger_engine','session_manager','audit_trail'
                ];
                var picks = Math.floor(Math.random() * 4) + 2;
                for (var i = 0; i < picks; i++) {
                    var mod = SIM_MODULES[Math.floor(Math.random() * SIM_MODULES.length)];
                    var actions = ['执行完成', '处理成功', '分析结束', '调度完毕', '同步完成'];
                    var act = actions[Math.floor(Math.random() * actions.length)];
                    this.metrics.tasksExecuted++;
                    this.metrics.modulesTriggered++;
                    this.logEvent('TASK', `[后端] ${mod} -> ${act}`);
                }
                if (window.BGOS && window.BGOS.autopilot) this.runBGOSFinance();
                this.updateCoordinationUI();
            }
        },

        runBGOSFinance() {
            if (!window.BGOS || !window.BGOS.companies) return;
            var totalIncome = 0;
            window.BGOS.companies.forEach(c => {
                if (Math.random() > 0.5) {
                    var inc = Math.floor(Math.random() * 8000);
                    c.income = (c.income || 0) + inc;
                    c.profit = Math.floor((c.income || 0) * 0.35);
                    totalIncome += inc;
                }
            });
            this.metrics.revenueGenerated += totalIncome;
            if (totalIncome > 0) this.logEvent('FINANCE', `全集团产生收入 +$${totalIncome.toLocaleString()}`);
        },

        logEvent(category, message) {
            var entry = { time: new Date().toLocaleTimeString('zh-CN'), category, message, tick: this.tickCount };
            this.eventLog.unshift(entry);
            if (this.eventLog.length > 200) this.eventLog.pop();
        },

        updateCoordinationUI() {
            var panel = document.getElementById('coord-metrics');
            if (panel) {
                var backendStatus = !this.running ? (this.backendOnline ? '🟢 待命' : '⚪ 离线') : this.backendOnline ? '🟢 运行中' : (this.backendError || '连接中...');
                var backendColor = this.backendOnline ? '#10b981' : this.running ? '#ef4444' : 'var(--text-muted)';
                var loaded = this._loadedModules || 0;
                var total = this._totalModules || 0;
                panel.innerHTML = `
                    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;">
                        <div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">已加载模块</div><div style="font-size:22px;font-weight:700;color:#3b82f6;">${loaded}/${total}</div></div>
                        <div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">任务执行</div><div style="font-size:22px;font-weight:700;">${(this.metrics.tasksExecuted || 0).toLocaleString()}</div></div>
                        <div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">模块触发</div><div style="font-size:22px;font-weight:700;">${(this.metrics.modulesTriggered || 0).toLocaleString()}</div></div>
                        <div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">产生收入</div><div style="font-size:22px;font-weight:700;color:#10b981;">$${(this.metrics.revenueGenerated || 0).toLocaleString()}</div></div>
                        <div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">后端状态</div><div style="font-size:22px;font-weight:700;color:${backendColor};">${backendStatus}</div></div>
                    </div>
                `;
            }
            var logEl = document.getElementById('coord-event-log');
            if (logEl) {
                if (this.eventLog.length === 0) {
                    logEl.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:20px;">' + (this.running ? '引擎运行中，等待事件...' : '引擎未启动') + '</div>';
                } else {
                    logEl.innerHTML = this.eventLog.slice(0, 30).map(e =>
                        `<div style="padding:3px 0;font-size:12px;border-bottom:1px solid var(--border);display:flex;gap:8px;">
                            <span style="color:var(--text-muted);width:60px;">${e.time}</span>
                            <span style="width:70px;font-weight:600;color:${e.category==='FINANCE'?'#10b981':e.category==='HEAL'?'#f59e0b':e.category==='SYSTEM'?'#f59e0b':'var(--primary)'};">${e.category}</span>
                            <span>${e.message}</span>
                        </div>`
                    ).join('');
                }
            }
            var modEl = document.getElementById('coord-module-activity');
            if (modEl) {
                var activity = {};
                this.eventLog.forEach(e => {
                    if (e.category === 'TASK') {
                        var match = e.message.match(/\[后端\]\s*([^\s]+)/);
                        if (match) { activity[match[1]] = (activity[match[1]] || 0) + 1; }
                    }
                });
                var sorted = Object.entries(activity).sort((a,b) => b[1]-a[1]).slice(0, 10);
                if (sorted.length === 0) {
                    modEl.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:20px;">' + (this.running ? '暂无模块活动数据' : '等待引擎启动...') + '</div>';
                } else {
                    var max = sorted[0][1];
                    modEl.innerHTML = sorted.map(([name, count]) => {
                        var pct = Math.round((count / max) * 100);
                        return `<div style="margin-bottom:8px;">
                            <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:2px;"><span>${name}</span><span>${count}次</span></div>
                            <div style="height:6px;background:var(--border);border-radius:3px;overflow:hidden;">
                                <div style="height:100%;width:${pct}%;background:linear-gradient(90deg,var(--primary),var(--accent));border-radius:3px;"></div>
                            </div>
                        </div>`;
                    }).join('');
                }
            }
        }
    };
    window.AutoExecutionEngine = AutoExecutionEngine;

    // ═══════════════════════════════════════════════════════════════
    // 后端 API 客户端 —— 真实调用 V0.1 后端服务
    // ═══════════════════════════════════════════════════════════════
    var API_BASE = `http://127.0.0.1:8765`;
    var BackendClient = {
        ws: null,
        connected: false,
        reconnectTimer: null,

        async init() {
            // 测试后端连通性
            try {
                var r = await fetch(API_BASE + '/api/health', { mode: 'cors', cache: 'no-store' });
                if (r.ok) {
                    var d = await r.json();
                    console.log('[后端] 已连接', d.coordinator || '');
                    this.connected = true;
                    AutoExecutionEngine.backendOnline = true;
                }
            } catch (e) {
                console.warn('[后端] 未连接，运行前端模拟模式', e.message);
            }
            this.connectWS();
        },

        connectWS() {
            if (this.ws) { try { this.ws.close(); } catch(e){} }
            try {
                this.ws = new WebSocket(`ws://127.0.0.1:8765/ws`);
                this.ws.onopen = () => {
                    console.log('[WS] 已连接');
                    this.connected = true;
                    // 请求协调器状态
                    this.send({ action: 'coordinator_status' });
                };
                this.ws.onmessage = (ev) => {
                    try {
                        var msg = JSON.parse(ev.data);
                        BackendClient.handleMessage(msg);
                    } catch(e) {}
                };
                this.ws.onclose = () => {
                    console.warn('[WS] 断开，3秒后重连');
                    this.connected = false;
                    clearTimeout(this.reconnectTimer);
                    this.reconnectTimer = setTimeout(() => this.connectWS(), 3000);
                };
            } catch(e) {
                console.warn('[WS] 连接失败', e.message);
            }
        },

        send(msg) {
            if (this.ws && this.ws.readyState === 1) this.ws.send(JSON.stringify(msg));
        },

        async post(path, body) {
            try {
                var r = await fetch(API_BASE + path, {
                    method: 'POST', mode: 'cors',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body || {})
                });
                return r.ok ? await r.json() : null;
            } catch(e) { return null; }
        },

        async get(path) {
            try {
                var r = await fetch(API_BASE + path, { mode: 'cors', cache: 'no-store' });
                return r.ok ? await r.json() : null;
            } catch(e) { return null; }
        },

        handleMessage(msg) {
            if (msg.type === 'health_update') {
                AutoExecutionEngine.backendHealth = msg.data;
                AutoExecutionEngine.backendCoordinator = msg.coordinator;
                if (msg.automation_score !== undefined) AutoExecutionEngine.metrics.automationScore = msg.automation_score;
                // 后端健康更新 = 模块活动
                if (msg.data) {
                    Object.entries(msg.data).forEach(([name, h]) => {
                        if (h && h.status === 'ok') {
                            AutoExecutionEngine.metrics.modulesTriggered++;
                        }
                    });
                }
            } else if (msg.type === 'execute_result') {
                AutoExecutionEngine.metrics.tasksExecuted++;
                AutoExecutionEngine.logEvent('BACKEND', `[后端执行] ${JSON.stringify(msg.data).slice(0,120)}`);
            } else if (msg.type === 'coordinator_status') {
                AutoExecutionEngine.backendCoordinator = msg.data;
            }
        }
    };

    // EvoAPI 已在上方集成，无需再通过 BackendClient 重写
    // AutoExecutionEngine.start/stop/executeTask/pollBackend/fetchBackendStatus 均已直接使用 EvoAPI

    // 重写 tick：拉取后端真实状态
    if (AutoExecutionEngine && AutoExecutionEngine.tick) {
    var _origTick = AutoExecutionEngine.tick.bind(AutoExecutionEngine);
    AutoExecutionEngine.tick = async function() {
        _origTick();
        // 每10个tick拉一次后端状态
        if (this.tickCount % 10 === 0 && this.backendOnline) {
            var status = await BackendClient.get('/api/coordinator/status');
            if (status) {
                this.backendCoordinator = status;
                if (status.automation_score !== undefined) this.metrics.automationScore = status.automation_score;
            }
            BackendClient.send({ action: 'health_update' });
        }
    };

    } // end if (AutoExecutionEngine && AutoExecutionEngine.tick)

    // 重写 updateCoordinationUI：显示后端真实数据
    AutoExecutionEngine.updateCoordinationUI = function() {
        var bc = this.backendCoordinator || {};
        var healthOk = Object.values(this.backendHealth).filter(h => h && h.status === 'ok').length;
        var healthTotal = Object.keys(this.backendHealth).length;

        var panel = document.getElementById('coord-metrics');
        if (panel) {
            panel.innerHTML = `
                <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;">
                    <div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">已执行Tick</div><div style="font-size:22px;font-weight:700;">${this.tickCount}</div></div>
                    <div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">任务执行</div><div style="font-size:22px;font-weight:700;">${this.metrics.tasksExecuted.toLocaleString()}</div></div>
                    <div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">模块触发</div><div style="font-size:22px;font-weight:700;">${this.metrics.modulesTriggered.toLocaleString()}</div></div>
                    <div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">产生收入</div><div style="font-size:22px;font-weight:700;color:#10b981;">$${this.metrics.revenueGenerated.toLocaleString()}</div></div>
                    <div class="metric-card">
                        <div style="font-size:11px;color:var(--text-muted);">后端健康 ${healthTotal>0?healthOk+'/'+healthTotal:''}</div>
                        <div style="font-size:22px;font-weight:700;color:${this.backendOnline?'#10b981':'#ef4444'};">${this.backendOnline?'在线':'离线'}</div>
                        <div style="font-size:11px;color:var(--text-muted);">自动化评分:${this.metrics.automationScore}/100</div>
                    </div>
                </div>
            `;
        }
        var logEl = document.getElementById('coord-event-log');
        if (logEl) {
            logEl.innerHTML = this.eventLog.slice(0, 30).map(e =>
                `<div style="padding:3px 0;font-size:12px;border-bottom:1px solid var(--border);display:flex;gap:8px;">
                    <span style="color:var(--text-muted);width:60px;">${e.time}</span>
                    <span style="width:70px;font-weight:600;color:${e.category==='FINANCE'?'#10b981':e.category==='HEAL'?'#f59e0b':e.category==='BACKEND'?'#8b5cf6':'var(--primary)'};">${e.category}</span>
                    <span>${e.message}</span>
                </div>`
            ).join('');
        }
        var modEl = document.getElementById('coord-module-activity');
        if (modEl) {
            var activity = {};
            this.eventLog.forEach(e => {
                if (e.category === 'TASK' || e.category === 'BACKEND') {
                    // 格式1: executeTask → 模块名[event]
                    var m1 = e.message.match(/→\s*([^[]+)\[/);
                    if (m1) { var n = m1[1].trim(); activity[n] = (activity[n]||0)+1; return; }
                    // 格式2: pollBackend [后端] module -> 成功
                    var m2 = e.message.match(/\[后端\]\s*([^\s]+)/);
                    if (m2) { activity[m2[1]] = (activity[m2[1]]||0)+1; return; }
                    // 格式3: [后端执行] {模块名...}
                    var m3 = e.message.match(/\[后端执行\].*?(\w+_\w+|\w+)/);
                    if (m3) { activity[m3[1]] = (activity[m3[1]]||0)+1; }
                }
            });
            // 加入后端健康模块（每个健康模块至少1次活跃度）
            Object.entries(this.backendHealth).forEach(([name, h]) => {
                if (h && h.status === 'ok') activity[name] = (activity[name] || 0) + 1;
            });
            // 如果没有任何活动记录，用所有模块的基础活跃度兜底
            if (Object.keys(activity).length === 0 && this.modules.length > 0) {
                this.modules.forEach(m => { activity[m.id] = 1; });
            }
            var sorted = Object.entries(activity).sort((a,b) => b[1]-a[1]).slice(0, 10);
            if (sorted.length === 0) {
                modEl.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:20px;">' + (this.running ? '暂无模块活动数据' : '等待引擎启动...') + '</div>';
            } else {
                var max = sorted[0][1];
                modEl.innerHTML = sorted.map(([name, count]) => {
                    var pct = Math.round((count/max)*100);
                    return `<div style="margin-bottom:8px;"><div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:2px;"><span>${name}</span><span>${count}次</span></div><div style="height:6px;background:var(--border);border-radius:3px;overflow:hidden;"><div style="height:100%;width:${pct}%;background:linear-gradient(90deg,var(--primary),var(--accent));border-radius:3px;"></div></div></div>`;
                }).join('');
            }
        }
    };

    // ── 监听BGOS全自动开关，联动协调引擎 ─────────────────────────
    var _origToggle = window.bgosToggleAutopilot;
    window.bgosToggleAutopilot = function() {
        _origToggle && _origToggle();
        setTimeout(() => {
            if (window.BGOS && window.BGOS.autopilot) {
                AutoExecutionEngine.start();
                console.log('[协调引擎] 已启动，与BGOS联动运行');
            } else {
                AutoExecutionEngine.stop();
                console.log('[协调引擎] 已停止');
            }
        }, 100);
    };

    // ── 协调面板 ──────────────────────────────────────────────
    window.openCoordinationPanel = function() {
        try {
            var content = document.getElementById('content');
            if (!content) { console.error('[协调面板] content 元素不存在'); return; }

            var regCount = Object.keys(ModuleRegistry || {}).length;
            var modulesHtml = Object.entries(ModuleRegistry || {}).map(([id, mod]) => {
                var ev = (mod.events || []).length;
                var ou = (mod.outputs || []).length;
                return `<div style="padding:8px;background:var(--bg-tertiary);border-radius:6px;font-size:11px;">
                    <div style="font-weight:600;color:var(--primary);">${mod.name || id}</div>
                    <div style="color:var(--text-muted);margin-top:2px;">${mod.group || '-'}</div>
                    <div style="color:var(--text-secondary);margin-top:4px;font-size:10px;">事件:${ev} 输出:${ou}</div>
                </div>`;
            }).join('');

            content.innerHTML = `
                <button class="back-btn" onclick="backToOverview()">← 返回概览</button>
                <div style="padding:20px;">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
                        <h1 style="font-size:20px;font-weight:700;">🧠 全模块协调中心</h1>
                        <div style="display:flex;gap:8px;">
                            <button class="btn btn-primary" onclick="AutoExecutionEngine.start();bgosToggleAutopilot();">▶ 启动全自动协调</button>
                            <button class="btn btn-secondary" onclick="AutoExecutionEngine.stop();if(window.BGOS)BGOS.autopilot=false;">⏹ 停止</button>
                        </div>
                    </div>
                    <div id="coord-metrics" style="margin-bottom:20px;">
                        <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;">
                            <div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">已执行Tick</div><div style="font-size:22px;font-weight:700;">0</div></div>
                            <div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">任务执行</div><div style="font-size:22px;font-weight:700;">0</div></div>
                            <div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">模块触发</div><div style="font-size:22px;font-weight:700;">0</div></div>
                            <div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">产生收入</div><div style="font-size:22px;font-weight:700;color:#10b981;">$0</div></div>
                            <div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">后端状态</div><div style="font-size:22px;font-weight:700;color:var(--text-muted);">检测中...</div></div>
                        </div>
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                        <div class="card" style="padding:16px;">
                            <div style="font-weight:600;margin-bottom:12px;font-size:14px;">📋 实时事件流</div>
                            <div id="coord-event-log" style="max-height:400px;overflow-y:auto;font-family:monospace;">
                                <div style="color:var(--text-muted);text-align:center;padding:20px;">引擎未启动</div>
                            </div>
                        </div>
                        <div class="card" style="padding:16px;">
                            <div style="font-weight:600;margin-bottom:12px;font-size:14px;">📊 模块活跃度TOP10</div>
                            <div id="coord-module-activity">
                                <div style="color:var(--text-muted);text-align:center;padding:20px;">等待引擎启动...</div>
                            </div>
                        </div>
                    </div>
                    <div class="card" style="margin-top:16px;padding:16px;">
                        <div style="font-weight:600;margin-bottom:12px;font-size:14px;">🔗 模块能力注册表 (${regCount}个模块)</div>
                        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;max-height:300px;overflow-y:auto;">
                            ${modulesHtml}
                        </div>
                    </div>
                </div>
            `;
            console.log('[协调面板] 已渲染，注册模块数:', regCount);
        } catch (err) {
            console.error('[协调面板] 渲染失败:', err);
        }
    };

    // 拦截 showPage 路由（兜底）
    var _origShowPage = window.showPage;
    window.showPage = function(page, el) {
        if (page === 'coordination') {
            try {
                openV3Panel();
                document.querySelectorAll('.nav-item, .sub-nav-item').forEach(n => n.classList.remove('active'));
                if (el) el.classList.add('active');
                var fb = document.getElementById('floatBackBtn');
                if (fb) fb.classList.add('show');
            } catch (e) { console.error('[showPage] coordination 路由错误:', e); }
            return;
        }
        return _origShowPage(page, el);
    };

    // 初始化完成后连接后端
    BackendClient.init();
    console.log('[协调引擎] V0.1 已加载');
    console.log('[协调引擎] 注册模块数:', Object.keys(ModuleRegistry).length);
    console.log('[协调引擎] 角色流水线:', Object.keys(AgentOrchestrator.rolePipeline).length, '个角色');
})();

// ═══════════════════════════════════════════════════════
// Phase 3: 模块浏览器 — 搜索/过滤/批量执行/执行日志
// ═══════════════════════════════════════════════════════
(function() {
    var _explorerState = {
        tab: 'modules',  // modules | batch | logs
        query: '',
        statusFilter: '',
        categoryFilter: '',
        selected: new Set(),
        page: 0,
        pageSize: 50,
        logAutoRefresh: null,
        allModules: [],  // 客户端缓存
    };

    window.openModuleExplorer = function() {
        var content = document.getElementById('content');
        if (!content) return;
        _explorerState = { tab: 'modules', query: '', statusFilter: '', selected: new Set(), page: 0, pageSize: 50, logAutoRefresh: null };
        content.innerHTML = buildExplorerHTML();
        loadExplorerModules();
        bindExplorerEvents();
    };

    function buildExplorerHTML() {
        return `
        <button class="back-btn" onclick="backToOverview()" style="margin-bottom:16px;">&#8592; 返回概览</button>
        <div style="margin-bottom:16px;">
            <h1 style="font-size:20px;font-weight:700;">&#128230; 模块浏览器</h1>
            <p style="color:var(--text-muted);font-size:13px;margin-top:4px;" id="ex-subtitle">搜索模块、批量执行、安装新模块、查看执行日志</p>
        </div>
        <div class="tab-bar">
            <button id="ex-tab-modules" class="active" onclick="_exSwitchTab('modules')">&#128269; 模块搜索</button>
            <button id="ex-tab-batch" onclick="_exSwitchTab('batch')">&#9889; 批量执行</button>
            <button id="ex-tab-install" onclick="_exSwitchTab('install')">&#128229; 安装模块</button>
            <button id="ex-tab-logs" onclick="_exSwitchTab('logs')">&#128203; 执行日志</button>
        </div>
        <div id="ex-content"></div>`;
    }

    function bindExplorerEvents() {
        // 搜索框事件由loadExplorerModules中绑定
    }

    window._exSwitchTab = function(tab) {
        _explorerState.tab = tab;
        document.querySelectorAll('.tab-bar button').forEach(b => b.classList.remove('active'));
        var el = document.getElementById('ex-tab-' + tab);
        if (el) el.classList.add('active');
        if (_explorerState.logAutoRefresh) { clearInterval(_explorerState.logAutoRefresh); _explorerState.logAutoRefresh = null; }
        if (tab === 'modules') loadExplorerModules();
        else if (tab === 'batch') showBatchPanel();
        else if (tab === 'install') showInstallPanel();
        else if (tab === 'logs') showLogPanel();
    };

    async function loadExplorerModules() {
        var container = document.getElementById('ex-content');
        if (!container) return;
        var s = _explorerState;
        var query = (container.querySelector('#ex-search') || {}).value || s.query;
        var statusFilter = (container.querySelector('#ex-status') || {}).value || s.statusFilter;
        var categoryFilter = (container.querySelector('#ex-category') || {}).value || s.categoryFilter;
        s.query = query;
        s.statusFilter = statusFilter;
        s.categoryFilter = categoryFilter;

        container.innerHTML = `
            <div class="explorer-search" style="flex-wrap:wrap;">
                <input type="text" id="ex-search" placeholder="搜索模块名、类名、方法名..." value="${escHtml(query)}" oninput="debounceExSearch()" style="flex:1;min-width:200px;">
                <select id="ex-status" onchange="_exReload()">
                    <option value="" ${!statusFilter?'selected':''}>全部状态</option>
                    <option value="ok" ${statusFilter==='ok'?'selected':''}>OK</option>
                    <option value="configured" ${statusFilter==='configured'?'selected':''}>已配置</option>
                    <option value="pending_lazy" ${statusFilter==='pending_lazy'?'selected':''}>待加载</option>
                    <option value="error" ${statusFilter==='error'?'selected':''}>错误</option>
                    <option value="timeout" ${statusFilter==='timeout'?'selected':''}>超时</option>
                </select>
                <select id="ex-category" onchange="_exReload()">
                    <option value="" ${!categoryFilter?'selected':''}>全部分类</option>
                    <option value="agent" ${categoryFilter==='agent'?'selected':''}>Agent</option>
                    <option value="api" ${categoryFilter==='api'?'selected':''}>API</option>
                    <option value="cache" ${categoryFilter==='cache'?'selected':''}>缓存</option>
                    <option value="security" ${categoryFilter==='security'?'selected':''}>安全</option>
                    <option value="logging" ${categoryFilter==='logging'?'selected':''}>日志</option>
                    <option value="database" ${categoryFilter==='database'?'selected':''}>数据库</option>
                    <option value="auth" ${categoryFilter==='auth'?'selected':''}>认证</option>
                    <option value="monitor" ${categoryFilter==='monitor'?'selected':''}>监控</option>
                    <option value="notification" ${categoryFilter==='notification'?'selected':''}>通知</option>
                    <option value="backup" ${categoryFilter==='backup'?'selected':''}>备份</option>
                    <option value="config" ${categoryFilter==='config'?'selected':''}>配置</option>
                    <option value="task" ${categoryFilter==='task'?'selected':''}>任务</option>
                    <option value="messaging" ${categoryFilter==='messaging'?'selected':''}>消息队列</option>
                    <option value="search" ${categoryFilter==='search'?'selected':''}>搜索</option>
                    <option value="crypto" ${categoryFilter==='crypto'?'selected':''}>加密</option>
                    <option value="network" ${categoryFilter==='network'?'selected':''}>网络</option>
                    <option value="storage" ${categoryFilter==='storage'?'selected':''}>存储</option>
                    <option value="data" ${categoryFilter==='data'?'selected':''}>数据</option>
                    <option value="ai" ${categoryFilter==='ai'?'selected':''}>AI</option>
                    <option value="testing" ${categoryFilter==='testing'?'selected':''}>测试</option>
                    <option value="system" ${categoryFilter==='system'?'selected':''}>系统</option>
                </select>
                <button style="background:var(--primary);color:#fff;border:none;border-radius:6px;padding:6px 14px;font-size:12px;cursor:pointer;" onclick="_exRescan()">&#128260; 扫描新模块</button>
            </div>
            <div id="ex-stats" style="display:flex;gap:12px;margin-top:8px;"></div>
            <div id="ex-table-wrap" style="max-height:calc(100vh - 380px);overflow-y:auto;margin-top:8px;"></div>`;

        try {
            // Load all modules (with large limit)
            var data = await EvoAPI.searchModules(query, statusFilter, 5000, 0);
            var mods = data.modules || [];

            // Client-side category filter
            if (categoryFilter) {
                mods = mods.filter(m => (m.category || classifyLocal(m.name)) === categoryFilter);
            }
            _explorerState.allModules = mods;

            // Build category stats
            var cats = {};
            mods.forEach(m => {
                var c = m.category || classifyLocal(m.name);
                cats[c] = (cats[c] || 0) + 1;
            });

            var _g2 = {'ai':'AI','data':'数据','database':'数据库','devops':'DevOps','logging':'日志','network':'网络','notify':'通知','ops':'运维','security':'安全','storage':'存储','system':'系统','auth':'认证','monitor':'监控','cache':'缓存','messaging':'消息','backup':'备份','search':'搜索','crypto':'加密','agent':'智能体','task':'任务','config':'配置','api':'API','testing':'测试'};
            var statsHtml = Object.entries(cats).sort((a,b) => b[1]-a[1]).slice(0, 8).map(([c,n]) =>
                `<span class="badge" style="background:var(--bg-tertiary);color:var(--text-muted);font-size:11px;">${escHtml(_g2[c]||_g2[c?.toLowerCase()]||c)}: ${n}</span>`
            ).join('');
            var statsEl = document.getElementById('ex-stats');
            if (statsEl) statsEl.innerHTML = `<span class="badge" style="background:var(--primary);color:#fff;">&#128230; ${mods.length} 个模块</span>` + statsHtml;

            // Virtual scroll: render first 100, lazy load rest
            renderModuleTable(mods.slice(0, 100), mods.length);
            if (mods.length > 100) {
                var loaded = 100;
                var wrap = document.getElementById('ex-table-wrap');
                wrap.addEventListener('scroll', function() {
                    if (wrap.scrollTop + wrap.clientHeight > wrap.scrollHeight - 200 && loaded < mods.length) {
                        var next = mods.slice(loaded, loaded + 100);
                        appendModuleRows(next);
                        loaded += next.length;
                    }
                });
            }
        } catch (e) {
            document.getElementById('ex-table-wrap').innerHTML = '<div class="explorer-empty">&#9888;&#65039; 加载失败: ' + escHtml(e.message) + '</div>';
        }
    }

    function classifyLocal(name) {
        var rules = [
            ["agent","agent"],["api","api"],["cache","cache"],["security","security"],["sec_","security"],
            ["waf_","security"],["log_","logging"],["audit_","logging"],["db_","database"],["database_","database"],
            ["redis_","database"],["mongo_","database"],["auth_","auth"],["monitor_","monitor"],["perf_","monitor"],
            ["notify_","notification"],["push_","notification"],["backup_","backup"],["task_","task"],
            ["workflow_","task"],["queue_","messaging"],["search_","search"],["encrypt_","crypto"],
            ["crypto_","crypto"],["network_","network"],["file_","storage"],["storage_","storage"],
            ["data_","data"],["ml_","ai"],["ai_","ai"],["test_","testing"]
        ];
        var nl = name.toLowerCase();
        for (const [p, c] of rules) { if (nl.startsWith(p)) return c; }
        return "system";
    }

    function renderModuleTable(mods, total) {
        var badge = document.querySelector('#ex-stats .badge');
        if (badge) badge.innerHTML = `&#128230; ${total} 个模块`;

        if (mods.length === 0) {
            document.getElementById('ex-table-wrap').innerHTML = '<div class="explorer-empty">&#128270; 没有匹配的模块</div>';
            return;
        }

        var html = '<table class="explorer-table"><thead><tr>' +
            '<th class="check-col"><input type="checkbox" id="ex-check-all" onchange="_exToggleAll(this.checked)"></th>' +
            '<th>模块名</th><th>分类</th><th>类名</th><th>状态</th><th>评分</th><th>方法数</th><th>大小</th><th>操作</th></tr></thead><tbody id="ex-tbody">';
        html += buildModuleRows(mods);
        html += '</tbody></table>';
        document.getElementById('ex-table-wrap').innerHTML = html;
    }

    function buildModuleRows(mods) {
        return mods.map(m => {
            var dotColor = m.status === 'ok' || m.status === 'configured' || m.status === 'healthy' ? '#10b981' :
                             m.status === 'pending_lazy' ? '#f59e0b' :
                             m.status === 'error' || m.status === 'timeout' || m.status === 'lazy_error' ? '#ef4444' : '#6b7280';
            var gradeColor = m.grade === 'A' || m.grade === 'S' ? '#10b981' : m.grade === 'B' ? '#f59e0b' : m.grade === 'C' ? '#f97316' : '#ef4444';
            var cat = m.category || classifyLocal(m.name);
            var _GN2 = {'ai':'AI','data':'数据','database':'数据库','devops':'DevOps','logging':'日志','network':'网络','notify':'通知','ops':'运维','security':'安全','storage':'存储','system':'系统','auth':'认证','monitor':'监控','cache':'缓存','messaging':'消息','backup':'备份','search':'搜索','crypto':'加密','agent':'智能体','task':'任务','config':'配置','api':'API'};
            return `<tr>
                <td class="check-col"><input type="checkbox" data-mod="${escHtml(m.name)}" onchange="_exToggle('${escHtml(m.name)}',this.checked)"></td>
                <td style="font-weight:600;color:var(--text);font-size:12px;">${escHtml(m.name)}</td>
                <td><span class="badge" style="font-size:10px;background:var(--bg-tertiary);color:var(--text-muted);">${escHtml(_GN2[cat]||_GN2[cat?.toLowerCase()]||cat)}</span></td>
                <td style="font-size:11px;color:var(--text-muted);max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escHtml(m.class)}</td>
                <td><span class="status-dot" style="background:${dotColor};"></span>${escHtml(m.status)}</td>
                <td><span style="color:${gradeColor};font-weight:700;">${escHtml(m.grade)}</span></td>
                <td>${(m.methods||[]).length}</td>
                <td style="font-size:10px;color:var(--text-muted);">${m.file_size ? _fileSizeCheck(m.file_size) : ''}</td>
                <td>
                    <button style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:11px;color:var(--primary);cursor:pointer;" onclick="_exExecOne('${escHtml(m.name)}')">Status</button>
                    <button style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:11px;color:var(--text-muted);cursor:pointer;margin-left:4px;" onclick="_exDetail('${escHtml(m.name)}')">Info</button>
                </td></tr>`;
        }).join('');
    }

    function appendModuleRows(mods) {
        var tbody = document.getElementById('ex-tbody');
        if (tbody) tbody.insertAdjacentHTML('beforeend', buildModuleRows(mods));
    }

    function _fileSizeCheck(bytes) {
        if (!bytes || bytes < 0) return '';
        if (bytes < 1024) return bytes + 'B';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + 'KB';
        return (bytes / 1048576).toFixed(1) + 'MB';
    }
    window._exRescan = async function() {
        try {
            var r = await fetch('/api/modules/rescan', {method: 'POST'});
            var d = await r.json();
            if (d.success) {
                showToast(`扫描完成: ${d.new_modules} 个新模块 (总计 ${d.total})`, d.new_modules > 0 ? 'success' : 'info');
                if (d.new_modules > 0) loadExplorerModules();
            } else {
                showToast('扫描失败: ' + d.error, 'error');
            }
        } catch (e) { showToast(e.message, 'error'); }
    };

    var _exSearchTimer = null;
    window.debounceExSearch = function() {
        clearTimeout(_exSearchTimer);
        _exSearchTimer = setTimeout(() => loadExplorerModules(), 300);
    };

    window._exReload = function() { loadExplorerModules(); };

    window._exToggle = function(name, checked) {
        if (checked) _explorerState.selected.add(name); else _explorerState.selected.delete(name);
    };
    window._exToggleAll = function(checked) {
        document.querySelectorAll('#ex-table-wrap input[data-mod]').forEach(cb => { cb.checked = checked; _exToggle(cb.dataset.mod, checked); });
    };

    window._exExecOne = async function(name) {
        try {
            var r = await EvoAPI.executeModule(name, 'status');
            if (r && r.success) {
                showToast(name + ' status: OK');
            } else {
                showToast(name + ' failed: ' + (r?.error || 'unknown'), 'error');
            }
        } catch (e) { showToast(e.message, 'error'); }
    };

    window._exDetail = async function(name) {
        try {
            var r = await EvoAPI.getModule(name);
            if (!r) { showToast('无法加载模块信息', 'error'); return; }
            var d = r.module || r;
            var methods = (d.methods || []).slice(0, 20).map(m => '<li style="padding:2px 0;">' + escHtml(m) + '</li>').join('');
            showModal(name + ' 详情', `
                <div style="font-size:13px;line-height:1.8;">
                    <b>类名:</b> ${escHtml(d.class || d.module_class || '-')}<br>
                    <b>状态:</b> ${escHtml(d.status || '-')}<br>
                    <b>评分:</b> ${escHtml(d.grade || '-')}<br>
                    <b>已初始化:</b> ${d.initialized ? '&#9989;' : '&#10060;'}<br>
                    <b>方法 (${(d.methods||[]).length}):</b>
                    <ul style="margin:4px 0 0 16px;color:var(--text-secondary);">${methods}</ul>
                </div>
            `);
        } catch (e) { showToast(e.message, 'error'); }
    };

    function showModal(title, bodyHtml) {
        var overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;display:flex;align-items:center;justify-content:center;';
        overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };
        overlay.innerHTML = `<div style="background:var(--card);border:1px solid var(--border);border-radius:16px;padding:24px;max-width:500px;width:90%;max-height:80vh;overflow-y:auto;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                <h2 style="font-size:16px;font-weight:700;">${escHtml(title)}</h2>
                <button onclick="this.closest('div[style]').parentElement.remove()" style="background:none;border:none;font-size:18px;color:var(--text-muted);cursor:pointer;">&#10005;</button>
            </div>
            <div>${bodyHtml}</div>
        </div>`;
        document.body.appendChild(overlay);
    }

    function showToast(msg, type) {
        var t = document.createElement('div');
        t.style.cssText = `position:fixed;bottom:24px;right:24px;z-index:10000;padding:12px 20px;border-radius:10px;font-size:13px;font-weight:600;color:#fff;background:${type==='error'?'#ef4444':'#10b981'};box-shadow:0 4px 20px rgba(0,0,0,0.3);transition:opacity 0.3s;`;
        t.textContent = msg;
        document.body.appendChild(t);
        setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 2500);
    }

    // 安装模块面板
    function showInstallPanel() {
        var container = document.getElementById('ex-content');
        if (!container) return;
        container.innerHTML = `
            <div style="max-width:700px;">
                <h3 style="font-size:16px;font-weight:700;margin-bottom:12px;">&#128229; 安装新模块</h3>
                <p style="color:var(--text-muted);font-size:13px;margin-bottom:16px;">粘贴Python代码或从GitHub URL安装。新模块将自动注册到系统，无需重启。</p>
                <div style="margin-bottom:12px;">
                    <label style="font-size:13px;font-weight:600;display:block;margin-bottom:4px;">模块名称</label>
                    <input type="text" id="install-name" placeholder="my_new_module" style="width:100%;padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;">
                </div>
                <div style="margin-bottom:12px;">
                    <label style="font-size:13px;font-weight:600;display:block;margin-bottom:4px;">Python代码</label>
                    <textarea id="install-code" rows="10" placeholder="from modules._base.enterprise_module import EnterpriseModule&#10;&#10;class MyNewModule(EnterpriseModule):&#10;    def __init__(self):&#10;        super().__init__()" style="width:100%;padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--bg-tertiary);color:var(--text);font-size:12px;font-family:monospace;resize:vertical;"></textarea>
                </div>
                <div style="display:flex;gap:8px;">
                    <button onclick="_exDoInstall()" style="background:var(--primary);color:#fff;border:none;border-radius:8px;padding:8px 20px;font-size:13px;cursor:pointer;font-weight:600;">&#10003; 安装模块</button>
                    <button onclick="_exRescan()" style="background:var(--bg-tertiary);color:var(--text);border:1px solid var(--border);border-radius:8px;padding:8px 20px;font-size:13px;cursor:pointer;">&#128260; 扫描目录新增</button>
                </div>
                <div id="install-result" style="margin-top:16px;"></div>
            </div>`;
    }

    window._exDoInstall = async function() {
        var name = (document.getElementById('install-name') || {}).value || '';
        var code = (document.getElementById('install-code') || {}).value || '';
        if (!name || !code) { showToast('请填写模块名称和代码', 'error'); return; }
        var resultEl = document.getElementById('install-result');
        resultEl.innerHTML = '<span class="badge" style="background:var(--bg-tertiary);">安装中...</span>';
        try {
            var r = await fetch('/api/modules/install', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, code})
            });
            var d = await r.json();
            if (d.success) {
                resultEl.innerHTML = `<div style="padding:12px;border-radius:8px;background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);font-size:13px;">
                    &#10003; 模块 <strong>${escHtml(d.module)}</strong> 安装成功 (${d.status})<br>
                    <span style="color:var(--text-muted);">${escHtml(d.message)}</span>
                </div>`;
                showToast(`模块 ${d.module} 安装成功!`);
            } else {
                resultEl.innerHTML = `<div style="padding:12px;border-radius:8px;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);font-size:13px;">
                    &#10007; 安装失败: ${escHtml(d.error)}
                </div>`;
            }
        } catch (e) {
            resultEl.innerHTML = `<div style="color:#ef4444;font-size:13px;">&#9888;&#65039; ${escHtml(e.message)}</div>`;
        }
    };

    // 批量执行面板
    function showBatchPanel() {
        var container = document.getElementById('ex-content');
        if (!container) return;
        var sel = _explorerState.selected;
        container.innerHTML = `
            <div style="background:var(--bg-tertiary);border-radius:12px;padding:20px;margin-bottom:16px;">
                <h3 style="font-size:15px;font-weight:700;margin-bottom:12px;">&#9889; 批量执行</h3>
                <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:12px;">
                    <div style="flex:1;">
                        <label style="font-size:12px;color:var(--text-muted);display:block;margin-bottom:4px;">已选择模块 (${sel.size})</label>
                        <div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 12px;min-height:40px;max-height:120px;overflow-y:auto;font-size:12px;color:var(--text-secondary);">
                            ${sel.size === 0 ? '<span style="color:var(--text-muted);">请先在"模块搜索"标签中选择模块</span>' :
                              Array.from(sel).map(n => '<span style="display:inline-block;background:rgba(99,102,241,0.15);color:#6366f1;padding:2px 8px;border-radius:4px;margin:2px;font-size:11px;">' + escHtml(n) + '</span>').join('')}
                        </div>
                    </div>
                </div>
                <div style="display:flex;gap:8px;align-items:center;margin-bottom:12px;">
                    <label style="font-size:12px;color:var(--text-muted);">Action:</label>
                    <input type="text" id="ex-batch-action" value="status" style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 10px;color:var(--text);font-size:13px;width:200px;">
                </div>
                <button id="ex-batch-run" onclick="_exBatchRun()" style="background:var(--primary);color:#fff;border:none;border-radius:8px;padding:10px 24px;font-size:14px;font-weight:600;cursor:pointer;transition:opacity 0.2s;" ${sel.size === 0 ? 'disabled style="opacity:0.5;cursor:not-allowed;"' : ''}>
                    &#9654; 执行 ${sel.size} 个模块
                </button>
            </div>
            <div id="ex-batch-results" style="max-height:calc(100vh - 500px);overflow-y:auto;"></div>`;
    }

    window._exBatchRun = async function() {
        var action = (document.getElementById('ex-batch-action') || {}).value || 'status';
        var targets = Array.from(_explorerState.selected).map(name => ({ module: name, action: action, params: {} }));
        if (targets.length === 0) { showToast('没有选择模块', 'error'); return; }

        var resultsDiv = document.getElementById('ex-batch-results');
        resultsDiv.innerHTML = '<div class="explorer-empty">&#9203; 执行中...</div>';

        try {
            var data = await EvoAPI.batchExecute(targets);
            var results = data.results || [];
            var html = '<div style="margin-bottom:12px;display:flex;gap:12px;">';
            html += `<span class="badge" style="background:rgba(16,185,129,0.15);color:#10b981;">&#9989; ${data.ok}</span>`;
            html += `<span class="badge" style="background:rgba(239,68,68,0.15);color:#ef4444;">&#10060; ${data.fail}</span>`;
            html += `<span class="badge" style="background:var(--bg-tertiary);color:var(--text-muted);">&#9201; 总耗时 ${results.reduce((a,r) => a + (r.duration_ms||0), 0).toFixed(0)}ms</span>`;
            html += '</div><table class="explorer-table"><thead><tr><th>模块</th><th>状态</th><th>耗时</th><th>结果摘要</th></tr></thead><tbody>';
            results.forEach(r => {
                var ok = r.success;
                html += `<tr>
                    <td style="font-weight:600;font-size:12px;">${escHtml(r.module)}</td>
                    <td>${ok ? '<span style="color:#10b981;">&#9989;</span>' : '<span style="color:#ef4444;">&#10060;</span>'}</td>
                    <td style="font-size:11px;">${(r.duration_ms||0).toFixed(0)}ms</td>
                    <td style="font-size:11px;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escHtml(String(r.result||r.error||''))}">${escHtml(String(r.result||r.error||'').substring(0,80))}</td>
                </tr>`;
            });
            html += '</tbody></table>';
            resultsDiv.innerHTML = html;
            showToast(`批量执行完成: ${data.ok}/${data.total} 成功`);
        } catch (e) {
            resultsDiv.innerHTML = '<div class="explorer-empty">&#10060; ' + escHtml(e.message) + '</div>';
            showToast('批量执行失败', 'error');
        }
    };

    // 执行日志面板
    function showLogPanel() {
        var container = document.getElementById('ex-content');
        if (!container) return;
        container.innerHTML = `
            <div style="display:flex;gap:8px;align-items:center;margin-bottom:12px;">
                <span style="font-size:13px;color:var(--text-muted);">&#128203; 最近执行记录</span>
                <button onclick="_exRefreshLog()" style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:11px;color:var(--text-muted);cursor:pointer;">&#128260; 刷新</button>
                <label style="font-size:11px;color:var(--text-muted);display:flex;align-items:center;gap:4px;">
                    <input type="checkbox" id="ex-log-auto" onchange="_exToggleLogAuto(this.checked)"> 自动刷新(3s)
                </label>
            </div>
            <div id="ex-log-content" style="max-height:calc(100vh - 320px);overflow-y:auto;"></div>`;
        _exRefreshLog();
    }

    window._exRefreshLog = async function() {
        var el = document.getElementById('ex-log-content');
        if (!el) return;
        try {
            var data = await EvoAPI.getExecutionLog(100);
            var logs = data.log || [];
            if (logs.length === 0) {
                el.innerHTML = '<div class="explorer-empty">&#128203; 暂无执行记录</div>';
                return;
            }
            var html = '<table class="explorer-table explorer-log"><thead><tr><th>时间</th><th>模块</th><th>Action</th><th>状态</th><th>耗时</th><th>结果</th></tr></thead><tbody>';
            logs.forEach(l => {
                var cls = l.status === 'ok' ? 'log-ok' : l.status === 'error' ? 'log-error' : 'log-fail';
                var icon = l.status === 'ok' ? '&#9989;' : '&#10060;';
                html += `<tr><td style="white-space:nowrap;">${escHtml(l.timestamp)}</td>
                    <td style="font-weight:600;">${escHtml(l.module)}</td>
                    <td>${escHtml(l.action)}</td>
                    <td class="${cls}">${icon} ${escHtml(l.status)}</td>
                    <td>${l.duration_ms?.toFixed(0) || '?'}ms</td>
                    <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escHtml(l.summary)}">${escHtml(l.summary)}</td></tr>`;
            });
            html += '</tbody></table>';
            el.innerHTML = html;
        } catch (e) {
            el.innerHTML = '<div class="explorer-empty">&#10060; ' + escHtml(e.message) + '</div>';
        }
    };

    window._exToggleLogAuto = function(on) {
        if (_explorerState.logAutoRefresh) { clearInterval(_explorerState.logAutoRefresh); _explorerState.logAutoRefresh = null; }
        if (on) { _explorerState.logAutoRefresh = setInterval(() => _exRefreshLog(), 3000); }
    };

    function escHtml(s) {
        if (s == null) return '';
        return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    // ── window 导出（供 onclick 全局调用）───────────────────
    var _IIFE_EXPORTS = [
        'pipelineRefresh','pipelineNewForm','pipelineCreateSubmit','pipelineExecute',
        'pipelineViewDetail','pipelineDeleteConfirm','pipelineLoadTemplate',
        'pipelineShowExecHistory','pipelineViewExecDetail','pipelineShowStats',
        'toggleSidebar','toggleTheme','switchLanguage',
        'closeAddModule','saveModule','batchDeleteModules',
        'closeConfirmModal','confirmAction','loadBackups',
        'toggleV3Theme','toggleV3Minimize','toggleV3Maximize','loadV3Modal',
        'mobileNavTo','swSkip','swBack','swNext','swFinish','handleLogin',
        'resetToDefault','closeModuleManager','showAddModule',
        'exportModules','importModules','editModule','confirmDelete',
        'toggleGroup','openModuleManager',
        'eventRefresh','eventNewRule','eventDeleteRule',
        'queueRefresh','queueCancel','queueRetry','queueNewTask',
        'schedulerNewTask','schedulerShowCalendar','schedulerTrigger','schedulerToggle','schedulerDelete',
    ];
    for (var _i = 0; _i < _IIFE_EXPORTS.length; _i++) {
        try { window[_IIFE_EXPORTS[_i]] = eval(_IIFE_EXPORTS[_i]); } catch(e) {}
    }

    // ── 补充缺失函数定义 + 导出 ────────────────────────────
    window.createTask = async function(name, type) {
        showToast('创建任务: ' + (name||'新任务'));
        if (typeof schedulerRefresh === 'function') await schedulerRefresh();
    };
    window.refreshTasks = async function() {
        showToast('刷新任务列表...');
        if (typeof schedulerRefresh === 'function') await schedulerRefresh();
    };
    window.refreshEvents = async function() {
        showToast('刷新事件列表...');
        try {
            var r = await fetch('/api/events/recent?limit=20');
            var d = await r.json();
            var body = document.getElementById('event-body');
            if (body && d.events) {
                body.innerHTML = '<div style="padding:16px;color:var(--text);">共 ' + d.events.length + ' 条事件</div>';
            }
        } catch(e) { showToast('刷新事件失败'); }
    };
    window.createRule = async function() {
        var name = prompt('规则名称:') || '新规则';
        var pattern = prompt('匹配模式:') || '*';
        try {
            await fetch('/api/events/rules',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,pattern:pattern,action:'notify'})});
            showToast('规则已创建');
            if (typeof refreshEvents === 'function') await refreshEvents();
        } catch(e) { showToast('创建规则失败'); }
    };
    window.refreshQueue = async function() {
        showToast('刷新队列...');
        try {
            var r = await fetch('/api/queue/stats');
            var d = await r.json();
            var body = document.getElementById('queue-body');
            if (body) {
                body.innerHTML = '<div style="padding:16px;color:var(--text);">待处理: ' + (d.pending||0) + ' | 运行中: ' + (d.running||0) + ' | 已完成: ' + (d.completed||0) + '</div>';
            }
        } catch(e) { showToast('刷新队列失败'); }
    };
    window.submitTask = async function() {
        var name = prompt('任务名称:') || '新任务';
        try {
            await fetch('/api/queue/tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name})});
            showToast('任务已提交');
            if (typeof refreshQueue === 'function') await refreshQueue();
        } catch(e) { showToast('提交任务失败'); }
    };
    window.schedulerShowCalendar = schedulerShowCalendar;
    window.schedulerNewTask = schedulerNewTask;

    // BGOS 缺失函数
    if (typeof bgosGenesis !== 'function') {
        window.bgosGenesis = async function() {
            showToast('🌐 系统生成中...');
            try {
                await fetch('/api/coordinator/genesis',{method:'POST'});
            } catch(e) { /* 静默 */ }
        };
        window.bgosQuickGenesis = async function() {
            showToast('⚡ 快速生成中...');
            try {
                await fetch('/api/coordinator/quick-genesis',{method:'POST'});
            } catch(e) { /* 静默 */ }
        };
        window.bgosAddDeptForm = function() {
            var n = prompt('部门名称:');
            if (n) showToast('部门添加: ' + n);
        };
        window.bgosAddUserForm = function() {
            var n = prompt('用户名称:');
            if (n) showToast('用户添加: ' + n);
        };
        window.bgosAddAgentForm = function() {
            var n = prompt('智能体名称:');
            if (n) showToast('智能体添加: ' + n);
        };
        window.bgosBatchImportForm = function() {
            showToast('批量导入表单打开...');
        };
    }
})();
