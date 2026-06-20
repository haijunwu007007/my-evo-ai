import shutil, os

root = r'D:\AUTO-EVO-AI-V0.1\frontend'

# ===== FIX 1: index.html - remove broken refs =====
print('SKIP index.html (root stub, not served)')

# ===== FIX 2: capabilities.html - real API call =====
cap = os.path.join(root, 'capabilities.html')
c = open(cap, encoding='utf-8').read()
# Remove the empty capabilities list, add real dynamic content
old = '<div class="cap-list">'
new = '''<div class="cap-list" id="capList">
<script>
fetch('/api/v1/capabilities/list').then(r=>r.json()).then(d=>{
  var h=document.getElementById('capList');
  if(d&&d.capabilities) h.innerHTML=d.capabilities.map(function(c){
    return '<div class="cap-item"><span class="cap-icon">'+c.icon+'</span><strong>'+c.name+'</strong><p>'+c.desc+'</p></div>';
  }).join('');
}).catch(function(){h.innerHTML='<p>❌ 无法加载能力数据</p>'});
</script>'''
c = c.replace(old, new)
open(cap, 'w', encoding='utf-8').write(c)
print('OK capabilities.html')

# ===== FIX 3: permission.html - real RBAC data =====
per = os.path.join(root, 'permission.html')
c = open(per, encoding='utf-8').read()
# Replace static table with dynamic
old = '<table'
new = '''<h2>角色权限配置</h2>
<div id="rbacView"><p>⏳ 加载中...</p></div>
<script>
fetch('/api/v1/rbac/status').then(r=>r.json()).then(d=>{
  var html='<table border="1" cellpadding="8" style="border-collapse:collapse;width:100%"><tr><th>角色</th><th>权限</th></tr>';
  (d.roles||[]).forEach(function(r){html+='<tr><td><strong>'+r.name+'</strong></td><td>'+(r.permissions||[]).join(', ')+'</td></tr>'});
  html+='</table>';
  document.getElementById('rbacView').innerHTML=html;
}).catch(function(){document.getElementById('rbacView').innerHTML='<p>❌ 无法加载权限数据</p>'});
</script>
<table style="display:none"'''
c = c.replace(old, new)
open(per, 'w', encoding='utf-8').write(c)
print('OK permission.html')

# ===== FIX 4: memory.html - real memory/learning data =====
mem = os.path.join(root, 'memory.html')
c = open(mem, encoding='utf-8').read()
old = '<div class="memories"'
new = '''<div id="memView"><p>⏳ 加载中...</p></div>
<script>
fetch('/api/v1/memory/list').then(r=>r.json()).then(d=>{
  var items=d.memories||d.data||[];
  var html='';
  items.slice(0,20).forEach(function(m){
    html+='<div class="mem-item"><strong>'+(m.title||m.name||'记录')+'</strong><p>'+(m.content||m.desc||'').slice(0,100)+'</p></div>';
  });
  document.getElementById('memView').innerHTML=html||'<p>暂无记忆数据</p>';
}).catch(function(){document.getElementById('memView').innerHTML='<p>❌ 无法加载</p>'});
</script>
<div style="display:none" class="memories"'''
c = c.replace(old, new)
open(mem, 'w', encoding='utf-8').write(c)
print('OK memory.html')

# ===== FIX 5: multi_agent.html =====
ma = os.path.join(root, 'multi_agent.html')
c = open(ma, encoding='utf-8').read()
old = '<div class="container"'
new = '''<div class="agent-grid" id="agView"><p>⏳ 加载中...</p></div>
<script>
fetch('/api/v1/agents/list').then(r=>r.json()).then(d=>{
  var agents=d.agents||[];
  var html='<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:15px">';
  agents.forEach(function(a){
    html+='<div class="card" style="padding:20px"><h3>'+(a.name||a.id)+'</h3><p>'+(a.desc||'')+'</p><span class="tag">'+(a.status||'idle')+'</span></div>';
  });
  document.getElementById('agView').innerHTML=html+'</div>';
}).catch(function(){document.getElementById('agView').innerHTML='<p>❌ 无法加载Agent列表</p>'});
</script>
<div class="container"'''
c = c.replace(old, new)
open(ma, 'w', encoding='utf-8').write(c)
print('OK multi_agent.html')

# ===== FIX 6: SEO meta for all HTML files =====
seo = '\n<meta name="description" content="AUTO-EVO-AI 智能进化平台 - 一键部署、智能Agent、自动化工作流">\n<meta property="og:title" content="AUTO-EVO-AI">\n<meta property="og:description" content="一键部署任意项目，自动完成所有工作">\n<meta property="og:type" content="website">\n<meta name="twitter:card" content="summary">\n<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⚡</text></svg>">\n'
for f in os.listdir(root):
    if f.endswith('.html') and f != 'test.html':
        p = os.path.join(root, f)
        c2 = open(p, encoding='utf-8').read()
        if '<meta name="description"' in c2: continue
        if '<head>' in c2:
            c2 = c2.replace('<head>', '<head>' + seo)
            open(p, 'w', encoding='utf-8').write(c2)
            print('SEO', f)
        else:
            c2 = c2.replace('<!DOCTYPE html>\n<html', '<!DOCTYPE html>\n<html<head>' + seo + '</head')
            open(p, 'w', encoding='utf-8').write(c2)
            print('SEO(nohead)', f)

print('ALL DONE')
