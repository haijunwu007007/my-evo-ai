"""routes_new_features — 合并子模块路由"""
from fastapi import APIRouter
import json

router = APIRouter()

# 从3个拆分文件导入并合并路由
from .core_basic import router as _basic_router
from .core_auth import router as _auth_router
from .core_plugins import router as _plugins_router

router.include_router(_basic_router)
router.include_router(_auth_router)
router.include_router(_plugins_router)

# 保留 _WORKFLOW_HTML 供 routes_static.py 回退导入
_WORKFLOW_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<link rel="stylesheet" href="/frontend/share.css">
<title>Workflow - AUTO-EVO-AI</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);overflow:hidden;height:100vh}
.back-btn{z-index:999;padding:6px 14px;border-radius:6px;border:1px solid var(--border);background:var(--card);color:var(--text);font-size:14px;cursor:pointer;text-decoration:none}
.toolbar{display:flex;align-items:center;gap:10px;padding:10px 16px;background:var(--card);border-bottom:1px solid var(--border)}
.toolbar h2{font-size:16px;margin-right:20px;color:var(--accent)}
</style>
</head>
<body>
<script>
(function(){var t=localStorage.getItem('evo_theme');if(t==='dark')document.body.classList.add('dark')})();
function toggleTheme(){document.body.classList.toggle('dark');localStorage.setItem('evo_theme',document.body.classList.contains('dark')?'dark':'light')}
</script>
<div class="toolbar">
<span class="back-btn" onclick="window.location.href='/'">←</span>
<h2>工作流引擎</h2>
<button onclick="toggleTheme()">🌙</button>
</div>
<div style="padding:20px;text-align:center;color:var(--text2)">
<p>工作流画布即将加载...</p>
<script>
fetch('/frontend/workflow_full.html').then(r=>r.text()).then(html=>{
document.body.innerHTML=html;eval(html.match(/<script>([\s\S]*?)<\\/script>/)?.[1]||'')})
</script>
</div>
</body></html>"""
