// ═══════════════════════════════════════════════════════
// 统一国际化系统 — AUTO-EVO-AI V0.1
// 合并自 block-2.js / block-8.js / block-9.js
// 一套数据、一套API、一个localStorage键
// ═══════════════════════════════════════════════════════

var LANG_KEY = 'evo_lang';

// ── 统一翻译字典 ──
var ZH = {
    // 导航(block-8)
    'nav.dashboard':'监控面板','nav.agents':'Agent管理','nav.workflows':'工作流编排',
    'nav.tasks':'任务中心','nav.memory':'记忆管理','nav.evolution':'进化中心',
    'nav.routines':'Routines','nav.tools':'工具集成','nav.config':'配置中心',
    'nav.security':'安全治理','nav.perf':'性能监控','nav.alerts':'告警中心',
    'nav.logs':'日志中心','nav.backup':'容灾备份','nav.audit':'安全审计',
    'nav.users':'用户管理','nav.api':'API管理','nav.settings':'系统设置',
    'nav.github':'GitHub扫描','nav.scheduler':'调度配置','nav.reports':'报告中心',
    'nav.feedback':'用户反馈','nav.about':'关于系统',
    // 状态(block-8 + block-9)
    'status.online':'在线','status.offline':'离线','status.running':'运行中',
    'status.idle':'空闲','status.error':'异常','status.healthy':'正常',
    'status.running2':'运行中','status.stopped':'已停止',
    // 操作按钮(block-8 + block-9)
    'btn.execute':'执行','btn.stop':'停止','btn.restart':'重启',
    'btn.configure':'配置','btn.delete':'删除','btn.save':'保存',
    'btn.cancel':'取消','btn.refresh':'刷新','btn.export':'导出',
    'btn.import':'导入','btn.search':'搜索','btn.confirm':'确认',
    'btn.copy':'复制','btn.download':'下载','btn.upload':'上传',
    'btn.edit':'编辑','btn.close':'关闭',
    // 通用词(block-8 + block-9)
    'common.modules':'模块','common.engines':'引擎','common.tasks':'任务',
    'common.events':'事件','common.pipelines':'管线','common.schedules':'调度',
    'common.total':'总计','common.active':'活跃','common.inactive':'未激活',
    'common.loading':'加载中...','common.noData':'暂无数据',
    'common.success':'操作成功','common.failed':'操作失败',
    'common.warning':'警告','common.pending':'等待中','common.paused':'已暂停',
    // 面板标题(block-9)
    'panel.system':'系统概览','panel.metrics':'核心指标','panel.modules':'模块状态',
    'panel.recent':'最近活动','panel.actions':'快速操作',
    // 配置向导(block-9)
    'wizard.start':'开始配置','wizard.next':'下一步','wizard.prev':'上一步',
    'wizard.done':'完成','wizard.skip':'跳过','wizard.title':'配置向导',
    // 实时(block-8)
    'ws.connected':'实时连接已建立','ws.disconnected':'实时连接断开',
    'ws.reconnecting':'正在重新连接...','ws.moduleExecuted':'模块执行完成',
    'ws.taskCompleted':'任务完成','ws.alertTriggered':'告警触发',
    'ws.newEvent':'新事件',
    // 功能模块名(block-9)
    'feat.GitHub扫描':'GitHub扫描','feat.数据备份':'数据备份',
    'feat.插件市场':'插件市场','feat.数据库':'数据库',
    'feat.热门发现':'热门发现','feat.依赖检查':'依赖检查',
    'feat.实时状态':'实时状态',
};

var EN = {
    'nav.dashboard':'Dashboard','nav.agents':'Agents','nav.workflows':'Workflows',
    'nav.tasks':'Tasks','nav.memory':'Memory','nav.evolution':'Evolution',
    'nav.routines':'Routines','nav.tools':'Tools','nav.config':'Config Center',
    'nav.security':'Security','nav.perf':'Performance','nav.alerts':'Alerts',
    'nav.logs':'Logs','nav.backup':'Backup','nav.audit':'Audit',
    'nav.users':'Users','nav.api':'API','nav.settings':'Settings',
    'nav.github':'GitHub Scan','nav.scheduler':'Scheduler','nav.reports':'Reports',
    'nav.feedback':'Feedback','nav.about':'About',
    'status.online':'Online','status.offline':'Offline','status.running':'Running',
    'status.idle':'Idle','status.error':'Error','status.healthy':'Healthy',
    'status.running2':'Running','status.stopped':'Stopped',
    'btn.execute':'Execute','btn.stop':'Stop','btn.restart':'Restart',
    'btn.configure':'Configure','btn.delete':'Delete','btn.save':'Save',
    'btn.cancel':'Cancel','btn.refresh':'Refresh','btn.export':'Export',
    'btn.import':'Import','btn.search':'Search','btn.confirm':'Confirm',
    'btn.copy':'Copy','btn.download':'Download','btn.upload':'Upload',
    'btn.edit':'Edit','btn.close':'Close',
    'common.modules':'Modules','common.engines':'Engines','common.tasks':'Tasks',
    'common.events':'Events','common.pipelines':'Pipelines','common.schedules':'Schedules',
    'common.total':'Total','common.active':'Active','common.inactive':'Inactive',
    'common.loading':'Loading...','common.noData':'No Data',
    'common.success':'Success','common.failed':'Failed',
    'common.warning':'Warning','common.pending':'Pending','common.paused':'Paused',
    'panel.system':'System Overview','panel.metrics':'Key Metrics','panel.modules':'Module Status',
    'panel.recent':'Recent Activity','panel.actions':'Quick Actions',
    'wizard.start':'Start Setup','wizard.next':'Next','wizard.prev':'Previous',
    'wizard.done':'Done','wizard.skip':'Skip','wizard.title':'Setup Wizard',
    'ws.connected':'Realtime Connected','ws.disconnected':'Realtime Disconnected',
    'ws.reconnecting':'Reconnecting...','ws.moduleExecuted':'Module Executed',
    'ws.taskCompleted':'Task Completed','ws.alertTriggered':'Alert Triggered',
    'ws.newEvent':'New Event',
    'feat.GitHub扫描':'GitHub Scan','feat.数据备份':'Backup',
    'feat.插件市场':'Plugins','feat.数据库':'Database',
    'feat.热门发现':'Trending','feat.依赖检查':'Dependency Check',
    'feat.实时状态':'Realtime Status',
};

// ── 直接短文本映射（block-2 风格: 中文→英文） ──
var LOOKUP = {
    '监控面板':'Dashboard','Agent管理':'Agent Mgmt','工作流编排':'Workflow','任务中心':'Task Center',
    '记忆管理':'Memory','进化中心':'Evolution','工具集成':'Tools','安全治理':'Security','性能监控':'Performance',
    '告警中心':'Alerts','日志中心':'Logs','系统设置':'Settings','集成配置':'Integrations','用户管理':'Users',
    'API管理':'API Mgmt','配置中心':'Config Center','调度配置':'Scheduler','报告中心':'Reports',
    '用户反馈':'Feedback','关于系统':'About','GitHub扫描':'GitHub Scan','数据备份':'Backup',
    '插件市场':'Plugins','数据库':'Database','运行中':'Running','已停止':'Stopped','正常':'OK','异常':'Error',
    '在线':'Online','离线':'Offline','空闲':'Idle','执行中':'Executing','成功':'Success','失败':'Failed',
    '等待中':'Pending','已暂停':'Paused','执行':'Execute','停止':'Stop','重启':'Restart','删除':'Delete',
    '保存':'Save','取消':'Cancel','确认':'Confirm','返回概览':'Back','查看详情':'Details','刷新':'Refresh',
    '搜索':'Search','导出':'Export','导入':'Import','复制':'Copy','下载':'Download','上传':'Upload',
    '系统概览':'System Overview','核心指标':'Key Metrics','模块状态':'Module Status','最近活动':'Recent Activity',
    '快速操作':'Quick Actions','暂无数据':'No Data','加载中':'Loading...','操作成功':'Success','操作失败':'Failed',
    '配置向导':'Setup Wizard','开始配置':'Start Setup','下一步':'Next','上一步':'Previous','完成':'Done','跳过':'Skip',
    '登录':'Login','登出':'Logout','创建备份':'Create Backup','恢复':'Restore','备份列表':'Backup List',
    '安装':'Install','启用':'Enable','禁用':'Disable','卸载':'Uninstall','扫描':'Scan',
    '热门发现':'Trending','依赖检查':'Dep Check','实时状态':'Realtime Status','已连接':'Connected','已断开':'Disconnected',
    '数据统计':'DB Stats','压缩数据库':'Vacuum DB','迁移数据':'Migrate','清理过期':'Cleanup',
    // block-2 identity mapping
    'Dashboard':'Dashboard','Modules':'Modules','Coordinator':'Coordinator','Settings':'Settings',
    'Health Check':'Health Check','Execute':'Execute','View Code':'View Code','Actions':'Actions',
    'Search modules...':'Search modules...','All Modules':'All Modules','Execute Module':'Execute Module',
    'System Status':'System Status','Active':'Active','Healthy':'Healthy',
    'No results':'No results','Error':'Error',
    'Configuration':'Configuration','Monitoring':'Monitoring','Security':'Security',
    'Restore':'Restore','Plugins':'Plugins',
    'GitHub Scanner':'GitHub Scanner','WebSocket':'WebSocket',
    'Pipelines':'Pipelines','Events':'Events','Queue':'Queue','Logs':'Logs',
    'Authentication':'Authentication','Users':'Users','API Keys':'API Keys',
    'Language':'Language','English':'English','Chinese':'Chinese',
    'Notifications':'Notifications','Real-time':'Real-time','Connected':'Connected',
    'Disconnected':'Disconnected','Reconnecting':'Reconnecting',
    // block-evo.js 系统洞察
    '系统状态':'System Status','调度任务':'Scheduler','自动化评分':'Score',
};
// 生成反向映射 (英文→中文)
var LOOKUP_REV = {};
(function() {
    for (var k in LOOKUP) LOOKUP_REV[LOOKUP[k]] = k;
})();

// ── I18N 全局对象 ──
window.I18N = {
    current: localStorage.getItem(LANG_KEY) || 'zh',

    // 按key翻译 (block-8 风格)
    t: function(key) {
        var dict = this.current === 'en' ? EN : ZH;
        return dict[key] || key;
    },

    // 按短文本翻译 (block-2/block-9 风格: 传入中文或英文原文)
    tr: function(text) {
        if (!text) return text;
        if (this.current === 'zh') return text;
        return LOOKUP[text] || LOOKUP_REV[text] || text;
    },

    // 设置语言
    setLocale: function(lang) {
        this.current = lang;
        localStorage.setItem(LANG_KEY, lang);
        this.applyTranslations();
    },

    // 切换 (block-9 风格)
    toggle: function() {
        this.setLocale(this.current === 'zh' ? 'en' : 'zh');
    },

    // 应用到DOM
    applyTranslations: function() {
        // data-i18n 属性翻译 (key模式)
        document.querySelectorAll('[data-i18n]').forEach(function(el) {
            var key = el.getAttribute('data-i18n');
            if (!key) return;
            var text = window.I18N.t(key);
            if (text !== key) el.textContent = text;
        });
        // data-i18n-placeholder
        document.querySelectorAll('[data-i18n-placeholder]').forEach(function(el) {
            var key = el.getAttribute('data-i18n-placeholder');
            if (!key) return;
            var text = window.I18N.t(key);
            if (text !== key) el.placeholder = text;
        });
        // TreeWalker 全文替换: 遍历所有文本节点匹配LOOKUP
        if (this.current === 'en') {
            document.querySelectorAll('.nav-item .nav-text, .nav-item span:last-child, .sidebar a span, [class*="nav"] span:last-child').forEach(function(el) {
                var t = el.textContent.trim();
                if (t && LOOKUP[t]) el.textContent = LOOKUP[t];
            });
        }
        // 更新切换按钮文本
        var label = this.current === 'zh' ? 'EN / 中' : '中 / EN';
        var btn1 = document.getElementById('lang-toggle-btn');
        var btn2 = document.getElementById('lang-switch');
        if (btn1) btn1.textContent = label;
        if (btn2) btn2.textContent = label;
        document.title = 'AUTO-EVO-AI V0.1';
    },

    // 创建语言切换器DOM
    initLocaleUI: function() {
        if (document.getElementById('evo-i18n-switcher')) return;
        var c = document.createElement('div');
        c.id = 'evo-i18n-switcher';
        c.className = 'i18n-switcher';
        c.style.cssText = 'position:fixed;bottom:16px;right:16px;z-index:99999;display:flex;gap:4px;';
        c.innerHTML = '<button class="i18n-btn '+(this.current==='zh'?'active':'')+'" data-lang="zh" onclick="I18N.setLocale(\'zh\')" style="padding:4px 10px;border-radius:6px;border:1px solid #444;background:'+(this.current==='zh'?'#667eea':'transparent')+';color:#fff;cursor:pointer;font-size:12px;">中文</button>'+
                      '<button class="i18n-btn '+(this.current==='en'?'active':'')+'" data-lang="en" onclick="I18N.setLocale(\'en\')" style="padding:4px 10px;border-radius:6px;border:1px solid #444;background:'+(this.current==='en'?'#667eea':'transparent')+';color:#fff;cursor:pointer;font-size:12px;">EN</button>';
        document.body.appendChild(c);
    }
};

// 就绪后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        window.I18N.initLocaleUI();
        window.I18N.applyTranslations();
    });
} else {
    window.I18N.initLocaleUI();
    window.I18N.applyTranslations();
}
