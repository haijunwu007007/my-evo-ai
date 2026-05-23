
var TRANSLATIONS = {
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
};

var I18N = {
    lang: localStorage.getItem('evo_lang') || 'zh',
    t(text) { return this.lang === 'en' && TRANSLATIONS[text] ? TRANSLATIONS[text] : text; },
    toggle() { this.lang = this.lang === 'zh' ? 'en' : 'zh'; localStorage.setItem('evo_lang', this.lang); if(typeof applyTranslations==='function') applyTranslations(); }
};

