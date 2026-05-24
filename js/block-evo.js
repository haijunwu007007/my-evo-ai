// AUTO-EVO-AI 进化报告 & 系统洞察面板 (v0.1)
// 新增功能，不修改已有UI

(function(){
  // 面板添加在主内容区底部
  var style = document.createElement('style');
  style.textContent = `
    .evo-dashboard-panel { background:var(--card-bg,#1e293b); border:1px solid var(--border,#334155); border-radius:12px; margin:16px; padding:16px; }
    .evo-dashboard-panel h3 { font-size:14px; font-weight:600; color:var(--text,#e2e8f0); margin:0 0 12px; display:flex; align-items:center; gap:6px; }
    .evo-dashboard-panel .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:8px; }
    .evo-dashboard-panel .card { background:var(--hover-bg,#0f172a); border-radius:8px; padding:10px; }
    .evo-dashboard-panel .card .label { font-size:11px; color:var(--text-muted,#94a3b8); }
    .evo-dashboard-panel .card .value { font-size:18px; font-weight:700; color:var(--primary,#818cf8); margin:2px 0; }
    .evo-dashboard-panel .card .sub { font-size:11px; color:var(--text-secondary,#64748b); }
    .evo-dashboard-panel .task-item { display:flex; align-items:center; gap:8px; padding:6px 0; border-bottom:1px solid var(--border,#334155); font-size:12px; }
    .evo-dashboard-panel .task-item:last-child { border-bottom:none; }
    .evo-dashboard-panel .task-name { flex:1; color:var(--text,#e2e8f0); }
    .evo-dashboard-panel .task-status { font-size:10px; padding:1px 6px; border-radius:4px; }
    .evo-dashboard-panel .task-status.active { background:#065f46; color:#34d399; }
    .evo-dashboard-panel .error { color:#f87171; font-size:12px; padding:10px; text-align:center; }
  `;
  document.head.appendChild(style);

  // 创建面板容器
  var panel = document.createElement('div');
  panel.className = 'evo-dashboard-panel';
  panel.id = 'evoInsightPanel';
  panel.innerHTML = '<h3>系统洞察</h3><div id="evoInsightContent"><div class="error">加载中...</div></div>';
  document.querySelector('.main-content')?.appendChild(panel) ||
    document.querySelector('#app')?.appendChild(panel) ||
    document.body.appendChild(panel);

  // 加载数据
  function loadInsights(){
    var content = document.getElementById('evoInsightContent');
    if(!content) return;
    
    // 系统状态
    fetch('/api/status').then(r=>r.json()).then(function(data){
      // 调度任务
      return fetch('/api/scheduler/status').then(function(r2){ return r2.json(); }).then(function(sched){
        // 进化报告
        return fetch('/api/insights/evolution').then(function(r3){ return r3.json(); }).then(function(evo){
          var html = '<div class="grid">';
          html += '<div class="card"><div class="label">系统状态</div><div class="value" style="color:#34d399">运行中</div><div class="sub">'+data.system+'</div></div>';
          html += '<div class="card"><div class="label">功能模块</div><div class="value">'+data.modules_total+'</div><div class="sub">0 空壳</div></div>';
          html += '<div class="card"><div class="label">调度任务</div><div class="value">'+(sched.active_tasks||'?')+'</div><div class="sub">引擎: '+sched.engine+'</div></div>';
          html += '<div class="card"><div class="label">自动化评分</div><div class="value" style="color:#fbbf24">'+(data.coordinator?.automation_score||'?')+'</div><div class="sub">满分100</div></div>';
          html += '</div>';
          
          // 调度任务列表
          html += '<h3 style="margin-top:16px">活跃调度任务</h3>';
          html += '<div id="evoTaskList">加载中...</div>';
          content.innerHTML = html;
          
          fetch('/api/scheduler/tasks').then(function(r4){ return r4.json(); }).then(function(tasks){
            var list = document.getElementById('evoTaskList');
            if(!list) return;
            if(!tasks.tasks || tasks.tasks.length === 0){
              list.innerHTML = '<div class="error">暂无任务</div>'; return;
            }
            var html2 = '';
            var shown = tasks.tasks.slice(0,8);
            shown.forEach(function(t){
              var s = t.status || 'inactive';
              html2 += '<div class="task-item"><span class="task-status '+s+'">'+s+'</span><span class="task-name">'+t.name+'</span><span style="font-size:10px;color:#64748b">'+(t.last_run_at ? t.last_run_at.slice(5,16) : '')+'</span></div>';
            });
            if(tasks.tasks.length > 8) html2 += '<div style="text-align:center;padding:6px;font-size:11px;color:#64748b">还有 '+(tasks.tasks.length-8)+' 个任务...</div>';
            list.innerHTML = html2;
          }).catch(function(){
            var list = document.getElementById('evoTaskList');
            if(list) list.innerHTML = '<div class="error">加载失败</div>';
          });
          
        }).catch(function(){
          content.innerHTML += '<div class="error">进化报告API暂不可用</div>';
        });
      });
    }).catch(function(){
      content.innerHTML = '<div class="error">API连接失败，请确认服务已启动</div>';
    });
  }
  
  // 延迟加载（等页面其他内容初始化完）
  setTimeout(loadInsights, 1000);
})();
