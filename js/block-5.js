
var EVO_I18N = {
    current: localStorage.getItem('evo-lang') || 'zh',
    zh: {
        "系统状态":"System Status","监控面板":"Dashboard","配置中心":"Config Center",
        "定时任务":"Scheduler","事件总线":"Event Bus","消息队列":"Message Queue",
        "备份恢复":"Backup & Restore","日志中心":"Log Center","安全治理":"Security",
        "性能监控":"Performance","告警中心":"Alerts","GitHub扫描":"GitHub Scan",
        "插件市场":"Plugin Market","关于系统":"About","系统设置":"Settings",
        "执行":"Execute","停止":"Stop","重启":"Restart","删除":"Delete",
        "保存":"Save","取消":"Cancel","确认":"Confirm","关闭":"Close",
        "运行中":"Running","已停止":"Stopped","异常":"Error","健康":"Healthy",
        "操作成功":"Success","操作失败":"Failed","加载中...":"Loading...",
        "暂无数据":"No data","确认删除":"Confirm Delete","名称":"Name",
        "状态":"Status","描述":"Description","操作":"Actions",
        "创建时间":"Created","更新时间":"Updated","类型":"Type",
        "搜索":"Search","刷新":"Refresh","导出":"Export","导入":"Import",
        "启用":"Enable","禁用":"Disable","编辑":"Edit","查看":"View",
        "全部":"All","成功":"Success","失败":"Fail","进行中":"In Progress",
        "等待中":"Pending","已取消":"Cancelled","返回":"Back",
        "下一步":"Next","上一步":"Previous","完成":"Done","开始":"Start",
        "手动触发":"Trigger","立即执行":"Run Now","查看详情":"Details",
        "模块管理":"Module Mgmt","任务队列":"Task Queue","WebSocket":"WebSocket",
        "管线引擎":"Pipeline Engine","任务中心":"Task Center","工作流编排":"Workflow",
        "记忆管理":"Memory","进化中心":"Evolution","缓存管理":"Cache",
        "用户管理":"Users","API管理":"API Keys","角色权限":"Roles",
        "会话管理":"Sessions","网络配置":"Network","存储配置":"Storage",
        "密钥管理":"Secrets","环境变量":"Env Vars","Routines":"Routines",
        "工具集成":"Integrations","代码生成":"Code Gen","数据分析":"Analytics",
        "文件处理":"Files","消息推送":"Notifications",
        "快速安装":"Quick Install","配置向导":"Setup Wizard",
    },
    en: {
        "System Status":"系统状态","Dashboard":"监控面板","Config Center":"配置中心",
        "Scheduler":"定时任务","Event Bus":"事件总线","Message Queue":"消息队列",
        "Backup & Restore":"备份恢复","Log Center":"日志中心","Security":"安全治理",
        "Performance":"性能监控","Alerts":"告警中心","GitHub Scan":"GitHub扫描",
        "Plugin Market":"插件市场","About":"关于系统","Settings":"系统设置",
        "Execute":"执行","Stop":"停止","Restart":"重启","Delete":"删除",
        "Save":"保存","Cancel":"取消","Confirm":"确认","Close":"关闭",
        "Running":"运行中","Stopped":"已停止","Error":"异常","Healthy":"健康",
        "Success":"操作成功","Failed":"操作失败","Loading...":"加载中...",
        "No data":"暂无数据","Confirm Delete":"确认删除","Name":"名称",
        "Status":"状态","Description":"描述","Actions":"操作",
        "Created":"创建时间","Updated":"更新时间","Type":"类型",
        "Search":"搜索","Refresh":"刷新","Export":"导出","Import":"导入",
        "Enable":"启用","Disable":"禁用","Edit":"编辑","View":"查看",
        "All":"全部","Success":"成功","Fail":"失败","In Progress":"进行中",
        "Pending":"等待中","Cancelled":"已取消","Back":"返回",
        "Next":"下一步","Previous":"上一步","Done":"完成","Start":"开始",
        "Trigger":"手动触发","Run Now":"立即执行","Details":"查看详情",
        "Module Mgmt":"模块管理","Task Queue":"任务队列","WebSocket":"WebSocket",
        "Pipeline Engine":"管线引擎","Task Center":"任务中心","Workflow":"工作流编排",
        "Memory":"记忆管理","Evolution":"进化中心","Cache":"缓存管理",
        "Users":"用户管理","API Keys":"API管理","Roles":"角色权限",
        "Sessions":"会话管理","Network":"网络配置","Storage":"存储配置",
        "Secrets":"密钥管理","Env Vars":"环境变量","Routines":"Routines",
        "Integrations":"工具集成","Code Gen":"代码生成","Analytics":"数据分析",
        "Files":"文件处理","Notifications":"消息推送",
        "Quick Install":"快速安装","Setup Wizard":"配置向导",
    },
    toggle() {
        var newLang = EVO_I18N.current === 'zh' ? 'en' : 'zh';
        localStorage.setItem('evo-lang', newLang);
        location.reload();
    },
    apply() {
        var dict = EVO_I18N[EVO_I18N.current];
        if (!dict) return;
        // Walk all visible text nodes and translate
        var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
        var nodesToReplace = [];
        while (walker.nextNode()) {
            var node = walker.currentNode;
            if (!node.parentElement) continue;
            var tag = node.parentElement.tagName;
            if (['SCRIPT','STYLE','NOSCRIPT','TEXTAREA','INPUT'].includes(tag)) continue;
            var text = node.textContent.trim();
            if (text && dict[text]) {
                nodesToReplace.push({node, from: text, to: dict[text]});
            }
        }
        nodesToReplace.forEach(({node, from, to}) => {
            node.textContent = node.textContent.replace(from, to);
        });
    }
};
function switchLanguage() { EVO_I18N.toggle(); }
// Auto-apply on load and after page transitions — only when language is NOT zh
var _origShowPage = (typeof showPage === 'function') ? showPage : null;
var _showPageOrig = window.showPage;
window.showPage = function(id) {
    if (_showPageOrig) _showPageOrig(id);
    if (EVO_I18N.current !== 'zh') setTimeout(() => EVO_I18N.apply(), 100);
};
document.addEventListener('DOMContentLoaded', () => {
    if (EVO_I18N.current === 'en') {
        EVO_I18N.apply();
    } else {
        localStorage.removeItem('evo-lang');
    }
    // HARD override: ensure no "SECURITY" in sidebar
    setTimeout(function() {
        document.querySelectorAll('.nav-group-title').forEach(function(el) {
            var txt = el.textContent;
            if (/SECURITY|security/i.test(txt) && !/安全/i.test(txt)) {
                el.textContent = txt.replace(/SECURITY|security/ig, '安全');
            }
        });
    }, 200);
    document.documentElement.lang = EVO_I18N.current;
});
