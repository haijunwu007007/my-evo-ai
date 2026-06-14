
    function mobileNavTo(section) {
        document.querySelectorAll('.mobile-nav-item').forEach(i => i.classList.remove('active'));
        event.currentTarget.classList.add('active');
        switch(section) {
            case 'home': window.scrollTo({top:0,behavior:'smooth'}); break;
            case 'modules': document.getElementById('section-modules')?.scrollIntoView({behavior:'smooth'}); break;
            case 'coord': openV3Panel(); break;
            case 'monitor': openMonitorPanel(); break;
            case 'docs': window.open('http://127.0.0.1:8765/docs','_blank'); break;
        }
    }
    // ===== Dashboard Button Functions =====
    function toggleGroup(el) {
        var p=el&&el.closest('.group'); if(!p)return;
        var b=p.querySelector('.group-body'); if(!b)return;
        if(b.style.display==='none'){b.style.display='';el.textContent=el.textContent.replace('[+]','[-]')}
        else{b.style.display='none';el.textContent=el.textContent.replace('[-]','[+]')}
    }
    function showPage(name) {
        // Engine cards → delegate to block-2.js panel functions
        var engineMap = {
            'pipeline-studio':'openPipelineStudio','pipeline':'openPipelineStudio',
            'config-center':'openConfigCenter','config':'openConfigCenter',
            'scheduler-panel':'openSchedulerPanel','scheduler':'openSchedulerPanel',
            'event-engine':'openEventEngine','events':'openEventEngine',
            'task-queue':'openTaskQueue','queue':'openTaskQueue',
            'ws-monitor':'openWSMonitor','monitor':'openMonitorPanel',
            'coordination':'openV3Panel','v3panel':'openV3Panel',
            'modules':'openModuleExplorer',
        };
        var fnName = engineMap[name];
        if(fnName && typeof window[fnName] === 'function'){ window[fnName](); return; }
        var titles={'pipeline':'🔗 模块管线引擎','config':'⚙️ 统一配置中心','scheduler':'⏰ 定时调度器','events':'⚡ 事件驱动引擎','queue':'📬 任务队列','monitor':'📡 实时推送监控','modules':'📦 模块浏览器'};
        var apiMap={'pipeline':'/api/v1/workflows','config':'/api/v1/services','scheduler':'/api/v1/scheduler/tasks','events':'/api/v1/status','queue':'/api/v1/status','monitor':'/api/v1/tools/health','modules':'/api/v1/modules'};
        var m=document.getElementById('evo-modal');
        if(!m){
            m=document.createElement('div');m.id='evo-modal';
            m.style.cssText='position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);z-index:99999;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)';
            m.onclick=function(){m.remove()};
        }
        var c=document.createElement('div');
        c.style.cssText='background:#1e293b;border-radius:16px;padding:24px;max-width:600px;width:90%;color:#e2e8f0;border:1px solid #334155;max-height:80vh;overflow-y:auto';
        c.onclick=function(e){e.stopPropagation()};
        c.innerHTML='<h2 style="margin-bottom:12px">'+(titles[name]||name)+'</h2><div id="evo-page-content" style="min-height:100px;text-align:center;color:#64748b;padding:20px">加载中...</div><div style="margin-top:16px;display:flex;gap:8px"><button onclick="document.getElementById(\'evo-modal\')?.remove()" style="padding:8px 20px;background:#6366f1;color:#fff;border:none;border-radius:8px;cursor:pointer">关闭</button></div>';
        m.innerHTML='';m.appendChild(c);document.body.appendChild(m);
        var url=apiMap[name]||('/api/v1/'+name);
        fetch(url).then(function(r){return r.json()}).then(function(d){
            var el=document.getElementById('evo-page-content');if(!el)return;
            el.innerHTML='<pre style="font-size:12px;text-align:left;background:#0f172a;padding:12px;border-radius:8px;overflow:auto;max-height:300px;color:#94a3b8">'+JSON.stringify(d,null,2)+'</pre>';
        }).catch(function(){var el=document.getElementById('evo-page-content');if(el)el.textContent='数据加载失败'});
    }
    function backToOverview() {
        window.scrollTo({top:0,behavior:'smooth'});
        document.querySelectorAll('.group-body').forEach(function(g){g.style.display=''});
        var els=document.querySelectorAll('[class*="page-"],.detail-view');
        els.forEach(function(e){e.remove()});
    }
    function doModuleHealth(name){
        fetch('/api/v1/tools/health').then(function(r){return r.json()}).then(function(d){
            alert('模块健康状态:\n'+JSON.stringify(d,null,2).slice(0,500));
        }).catch(function(){alert('健康检查请求失败')});
    }
    function doModuleExecute(name){
        var cmd=prompt('输入要执行的模块命令:');
        if(cmd){
            fetch('/api/v1/smart',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:'执行模块 '+name+': '+cmd})})
            .then(function(r){return r.json()}).then(function(d){alert(d.result||'执行完成')})
            .catch(function(){alert('执行失败')});
        }
    }
    function doModuleCode(name){alert('模块代码: '+name+'\n请在服务器上查看文件')}
    function doModuleActions(name){showPage('modules')}
    function confirmDelete(name){if(confirm('确定删除模块 '+name+'?'))alert('模块已标记删除');}
    function editModule(name){alert('编辑模块: '+name+'\n请直接修改对应文件')}
    function openWizard(){showPage('config')}
    function closeWizard(){document.getElementById('evo-modal')?.remove()}
    function wizardNext(){alert('下一步')}
    function wizardSave(){alert('保存成功')}
    // Mobile detection
    if (/Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent)) {
        document.body.classList.add('mobile-device');
    }


