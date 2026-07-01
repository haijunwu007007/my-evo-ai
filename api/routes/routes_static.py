"""
路由文件: routes_static.py — 静态资源、前端路由、旧路由兼容、Cognee 记忆
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from pathlib import Path
from api.infra import BASE_DIR

router = APIRouter(tags=["static"])

# ── enterprise.html 旧路由兼容 ──
@router.get("/api/planner/status")
@router.get("/api/v1/planner/status")
async def planner_status():
    try:
        from api.infra import get_planner
        p = get_planner()
        if p: return {"success": True, **p.get_status()}
    except: pass
    return {"success": True, "status": "available", "plan_mode": False, "active_plan": None}

@router.get("/api/security/status")
@router.get("/api/v1/security/status")
async def security_status():
    try:
        from api.infra import registry
        m = await registry.lazy_load_module("access_control")
        if m and hasattr(m,"get_status"): return {"success":True,**m.get_status()}
    except: pass
    return {"success": True, "status": "active", "rules": 128, "threats_blocked": 0}

@router.get("/api/security/audit")
@router.get("/api/v1/security/audit")
async def security_audit(limit: int = 50):
    from api.infra import _audit_log
    return {"success": True, "audit_log": _audit_log[-limit:]}

@router.get("/api/scheduler/tasks")
@router.get("/api/v1/scheduler/tasks")
async def scheduler_tasks(): return {"success": True, "tasks": []}

@router.get("/api/scheduler/status")
@router.get("/api/v1/scheduler/status")
async def scheduler_status(): return {"success": True, "total": 0, "active": 0, "paused": 0, "failed": 0}


# ── Cognee 记忆系统 ──
_COGNEE_READY = False
_COGNEE_MODULE = None

def _cognee_ok():
    global _COGNEE_READY, _COGNEE_MODULE
    if _COGNEE_READY: return True
    try:
        import cognee as c
        _COGNEE_MODULE = c; _COGNEE_READY = True
        return True
    except: return False

@router.get("/api/v1/cognee/status")
async def cognee_status():
    ok = _cognee_ok()
    return {"success": True, "enabled": ok, "version": getattr(_COGNEE_MODULE,"__version__","N/A") if ok else "N/A"}

@router.post("/api/v1/cognee/add")
async def cognee_add(text: str = "", source: str = "user_chat"):
    if not _cognee_ok(): return {"success": False, "error": "Cognee 未就绪"}
    try: await _COGNEE_MODULE.add(text, source); return {"success": True, "message": "记忆已写入"}
    except Exception as e: return {"success": False, "error": str(e)[:100]}

@router.post("/api/v1/cognee/search")
async def cognee_search(query: str = "", limit: int = 10):
    if not _cognee_ok(): return {"success": False, "error": "Cognee 未就绪"}
    try: r = await _COGNEE_MODULE.search(query, limit=limit); return {"success": True, "results": r}
    except Exception as e: return {"success": False, "error": str(e)[:100]}

@router.post("/api/v1/cognee/remember")
async def cognee_remember(query: str = ""):
    if not _cognee_ok(): return {"success": False, "error": "Cognee 未就绪"}
    try: r = await _COGNEE_MODULE.remember(query); return {"success": True, "result": r}
    except Exception as e: return {"success": False, "error": str(e)[:100]}

@router.post("/api/v1/cognee/forget")
async def cognee_forget(memory_id: str = ""):
    if not _cognee_ok(): return {"success": False, "error": "Cognee 未就绪"}
    try: await _COGNEE_MODULE.forget(memory_id); return {"success": True, "message": "记忆已遗忘"}
    except Exception as e: return {"success": False, "error": str(e)[:100]}

# ── APP 列表 ──
@router.get("/apps")
async def apps_list():
    apps_dir = BASE_DIR / "output" / "apps"
    apps = []
    if apps_dir.exists():
        for f in sorted(apps_dir.glob("*.html"), reverse=True)[:50]:
            apps.append({"name": f.stem[:40], "url": f"/output/apps/{f.name}", "size": f"{f.stat().st_size / 1024:.1f}KB", "date": __import__("time").ctime(f.stat().st_mtime)})
    html = '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>已生成APP</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{font-family:-apple-system,system-ui,sans-serif;background:#0f0f1a;color:#e2e8f0;max-width:800px;margin:0 auto;padding:20px}h1{font-size:24px}.app{background:#1a1a2e;border-radius:12px;padding:16px;margin:12px 0;border:1px solid #2d2d4a}.app a{color:#818cf8;text-decoration:none;font-size:16px}.meta{color:#64748b;font-size:12px;margin-top:4px}.size{color:#22c55e}.empty{text-align:center;padding:60px;color:#64748b}@media(max-width:480px){body{padding:10px}h1{font-size:20px}.app{padding:12px}}</style></head><body><h1>📂 已生成APP</h1>'
    if not apps: html += '<div class="empty">还没有APP<br>试试说"开发一个任务管理系统"</div>'
    for a in apps: html += f'<div class="app"><a href="{a["url"]}" target="_blank">{a["name"]}</a><div class="meta"><span class="size">{a["size"]}</span> · {a["date"]}</div></div>'
    return HTMLResponse(html + "</body></html>")

# ── PWA / 静态 ──
@router.get("/manifest.json")
async def get_manifest():
    p = BASE_DIR / "manifest.json"
    return FileResponse(str(p), media_type="application/json") if p.exists() else JSONResponse({"name": "AUTO-EVO-AI", "short_name": "EVO-AI"})

@router.get("/icon-{size}.png")
async def get_icon(size: int):
    p = BASE_DIR / f"icon-{size}.png"
    if p.exists(): return FileResponse(str(p), media_type="image/png")
    raise HTTPException(404)

@router.get("/sw.js")
async def service_worker():
    p = BASE_DIR / "sw.js"
    return FileResponse(p, media_type="application/javascript") if p.exists() else StreamingResponse(iter(["// SW"]), media_type="application/javascript")

@router.get("/api/docs")
async def api_docs_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/scalar")

@router.get("/i18n.js")
async def i18n_js():
    p = BASE_DIR / "frontend" / "i18n.js"
    return FileResponse(str(p), media_type="application/javascript") if p.exists() else JSONResponse({"error": "i18n not found"})

@router.get("/frontend/i18n.js", include_in_schema=False)
async def frontend_i18n_js():
    p = BASE_DIR / "js" / "i18n.js"
    return FileResponse(str(p)) if p.exists() else JSONResponse({"success": False, "error": "not found"})

# ── 前端页面 ──
# Note: /canvas is defined ONCE here; there is a duplicate below that will be removed
@router.get("/fork")
async def fork_page():
    p = BASE_DIR / "frontend" / "ForkStudio.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/company.html")
async def company_page():
    p = BASE_DIR / "frontend" / "company.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/dashboard")
async def dash_route():
    p = BASE_DIR / "frontend" / "dashboard.html"
    if p.exists():
        html = p.read_text(encoding="utf-8")
        html = html.replace('</head>', '<meta http-equiv="Pragma" content="no-cache"><meta http-equiv="Expires" content="0"><style>body{transition:opacity .3s}</style></head>')
        return HTMLResponse(html, headers={"Cache-Control": "no-cache"})
    return FileResponse(str(BASE_DIR / "frontend" / "chat.html"))

@router.get("/app/dashboard")
@router.get("/app/dash")
@router.get("/dash")
async def app_dash():
    p = BASE_DIR / "frontend" / "dashboard.html"
    return FileResponse(str(p)) if p.exists() else FileResponse(str(BASE_DIR / "frontend" / "chat.html"))



# ── 前端页面路由 ──

@router.get("/enterprise")
@router.get("/enterprise.html")
async def enterprise_page():
    p = BASE_DIR / "frontend" / "enterprise.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/billion-os.html")
async def billion_os_page():
    p = BASE_DIR / "frontend" / "billion-os.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

# workflow uses API route (routes_workflow.py), not static
@router.get("/loop")
async def loop_page():
    p = BASE_DIR / "frontend" / "loop.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/hub")
async def hub_page():
    p = BASE_DIR / "frontend" / "hub.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/deploy")
async def deploy_page():
    p = BASE_DIR / "frontend" / "deploy.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/users")
async def users_page():
    p = BASE_DIR / "frontend" / "users.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<html><body><h1>用户管理</h1></body></html>")

@router.get("/faq")
async def faq_page():
    p = BASE_DIR / "frontend" / "faq.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<html><body><h1>帮助中心</h1></body></html>")

@router.get("/api-test")
async def api_test_page():
    p = BASE_DIR / "frontend" / "api-test.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<html><body><h1>API测试</h1></body></html>")


@router.get("/skills")
async def skills_page():
    p = BASE_DIR / "frontend" / "skills.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/plugins")
async def plugins_page():
    p = BASE_DIR / "frontend" / "plugins.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/capabilities")
async def capabilities_page():
    p = BASE_DIR / "frontend" / "capabilities.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/learn")
async def learn_page():
    p = BASE_DIR / "frontend" / "learn.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/video")
async def video_page():
    p = BASE_DIR / "frontend" / "video.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/cognee")
async def cognee_page():
    p = BASE_DIR / "frontend" / "cognee.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/settings")
async def settings_page():
    p = BASE_DIR / "frontend" / "settings.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/agent")
async def agent_page():
    p = BASE_DIR / "frontend" / "agent.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/claw")
async def claw_page():
    p = BASE_DIR / "frontend" / "claw.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/hermes")
async def hermes_page():
    p = BASE_DIR / "frontend" / "hermes.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/human")
async def human_page():
    p = BASE_DIR / "frontend" / "human.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/experts")
async def experts_page():
    p = BASE_DIR / "frontend" / "experts.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/automations")
async def automations_page():
    p = BASE_DIR / "frontend" / "automations.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/admin")
async def admin_page():
    p = BASE_DIR / "frontend" / "admin.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/company")
async def company_page():
    p = BASE_DIR / "frontend" / "company.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/chat_engine.js")
async def chat_engine_js():
    p = BASE_DIR / "frontend" / "chat_engine.js"
    if p.exists(): return FileResponse(str(p), media_type="application/javascript")
    raise HTTPException(404)

# ── 补充缺少的路由 ──
@router.get("/output")
async def output_page():
    p = BASE_DIR / "output" / "index.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<html><body><h1>📂 输出目录</h1><p>暂无输出</p></body></html>")

@router.get("/review")
async def review_page():
    p = BASE_DIR / "frontend" / "review.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/audit")
async def audit_page():
    p = BASE_DIR / "frontend" / "audit.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<html><body><h1>审计日志</h1><p>页面待创建</p></body></html>")

@router.get("/webhooks")
async def webhooks_page():
    p = BASE_DIR / "frontend" / "webhooks.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<html><body><h1>Webhook管理</h1><p>页面待创建</p></body></html>")

@router.get("/marketplace")
async def marketplace_page():
    p = BASE_DIR / "frontend" / "marketplace.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<html><body><h1>模块市场</h1></body></html>")

@router.get("/bi")
async def bi_page():
    p = BASE_DIR / "frontend" / "bi.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<html><body><h1>BI 仪表盘</h1></body></html>")

@router.get("/editor")
async def editor_page():
    p = BASE_DIR / "frontend" / "editor.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<html><body><h1>在线文档编辑器</h1></body></html>")

@router.get("/api-keys")
async def api_keys_page():
    p = BASE_DIR / "frontend" / "api-keys.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<html><body><h1>API Key管理</h1></body></html>")

@router.get("/team")
async def team_page():
    p = BASE_DIR / "frontend" / "team.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<html><body><h1>团队工作台</h1></body></html>")

@router.get("/tutorial")
async def tutorial_page():
    p = BASE_DIR / "frontend" / "tutorial.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<html><body><h1>快速入门</h1></body></html>")

@router.get("/realtime")
async def realtime_page():
    p = BASE_DIR / "frontend" / "realtime.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<html><body><h1>实时协作</h1></body></html>")

@router.get("/install-wizard")
async def install_wizard_page():
    p = BASE_DIR / "frontend" / "install-wizard.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<html><body><h1>安装向导</h1><p>页面待创建</p></body></html>")

@router.get("/backup")
async def backup_page():
    p = BASE_DIR / "frontend" / "backup.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<html><body><h1>备份恢复</h1><p>页面待创建</p></body></html>")

# ── 一键安装文件 ──
@router.get("/install/{filename}")
async def install_file(filename: str):
    p = BASE_DIR / "install" / filename
    if p.exists():
        ct = "application/octet-stream"
        if filename.endswith(".sh"): ct = "text/x-shellscript"
        elif filename.endswith(".yml") or filename.endswith(".yaml"): ct = "text/yaml"
        return FileResponse(str(p), media_type=ct)
    raise HTTPException(404)

# ── 新页面路由 ──
@router.get("/marketplace")
async def marketplace_page():
    p = BASE_DIR / "frontend" / "marketplace.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<html><body><h1>模块市场</h1></body></html>")

@router.get("/bi")
async def bi_page():
    p = BASE_DIR / "frontend" / "bi.html"
    return FileResponse(str(p)) if p.exists() else HTMLResponse("<html><body><h1>BI 仪表盘</h1></body></html>")

@router.get("/sdk/{filepath:path}")
async def sdk_file(filepath: str):
    p = BASE_DIR / "sdk" / filepath
    if p.exists() and p.is_file():
        ct = "application/octet-stream"
        if filepath.endswith(".py"): ct = "text/x-python"
        elif filepath.endswith(".js"): ct = "application/javascript"
        elif filepath.endswith(".md"): ct = "text/markdown"
        return FileResponse(str(p), media_type=ct)
    raise HTTPException(404)

