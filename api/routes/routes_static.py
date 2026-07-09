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

    topbar = '<div class="topbar"><button class="topbar-back" onclick="window.location.href=\'/\'">← 返回</button><span class="topbar-title">📂 已生成APP</span></div>'
    html = '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>已生成APP</title><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/frontend/share.css"><body style="max-width:800px;margin:0 auto;padding:0">' + topbar + '<div style="padding:20px"><h1 class="grad-title" style="font-size:22px;margin-bottom:16px">📂 已生成APP</h1>'

    if not apps: html += '<div class="empty">还没有APP<br>试试说"开发一个任务管理系统"</div>'

    for a in apps: html += f'<div class="app"><a href="{a["url"]}" target="_blank">{a["name"]}</a><div class="meta"><span class="size">{a["size"]}</span> · {a["date"]}</div></div>'

    return HTMLResponse(html + "</div></body></html>")



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

@router.get("/icon-{size}.svg")
async def get_icon_svg(size: int):
    p = BASE_DIR / "frontend" / f"icon-{size}.svg"
    if p.exists(): return FileResponse(str(p), media_type="image/svg+xml")
    raise HTTPException(404)

@router.get("/ppt-gen.html")
async def ppt_gen_html():
    p = BASE_DIR / "frontend" / "ppt-gen.html"
    return FileResponse(str(p), media_type="text/html")

@router.get("/data-analyzer")
async def data_analyzer_html():
    p = BASE_DIR / "frontend" / "data-analyzer.html"
    return FileResponse(str(p), media_type="text/html")

@router.get("/assistant")
async def assistant_html():
    p = BASE_DIR / "frontend" / "assistant.html"
    return FileResponse(str(p), media_type="text/html")

@router.get("/site-builder")
async def site_builder_html():
    p = BASE_DIR / "frontend" / "site-builder.html"
    return FileResponse(str(p), media_type="text/html")

@router.get("/social-media")
async def social_media_html():
    p = BASE_DIR / "frontend" / "social-media.html"
    return FileResponse(str(p), media_type="text/html")

@router.get("/resume")
async def resume_html():
    p = BASE_DIR / "frontend" / "resume.html"
    return FileResponse(str(p), media_type="text/html")

@router.get("/contract-review")
async def contract_review_html():
    p = BASE_DIR / "frontend" / "contract-review.html"
    return FileResponse(str(p), media_type="text/html")

@router.get("/image-processor")
async def image_processor_html():
    p = BASE_DIR / "frontend" / "image-processor.html"
    return FileResponse(str(p), media_type="text/html")

@router.get("/doc-qa")
async def doc_qa_html():
    p = BASE_DIR / "frontend" / "doc-qa.html"
    return FileResponse(str(p), media_type="text/html")

@router.get("/price-compare")
async def price_compare_html():
    p = BASE_DIR / "frontend" / "price-compare.html"
    return FileResponse(str(p), media_type="text/html")

@router.get("/mortgage-calc")
async def mortgage_calc_html():
    p = BASE_DIR / "frontend" / "mortgage-calc.html"
    return FileResponse(str(p), media_type="text/html")

@router.get("/health-report")
async def health_report_html():
    p = BASE_DIR / "frontend" / "health-report.html"
    return FileResponse(str(p), media_type="text/html")

@router.get("/favicon.ico")
async def favicon_ico():
    p = BASE_DIR / "frontend" / "favicon.svg"
    return FileResponse(str(p), media_type="image/svg+xml")

@router.get("/favicon.svg")
async def favicon_svg():
    p = BASE_DIR / "frontend" / "favicon.svg"
    return FileResponse(str(p), media_type="image/svg+xml")



@router.get("/desktop")
async def desktop_html():
    p = BASE_DIR / "frontend" / "desktop.html"
    return FileResponse(str(p), media_type="text/html")

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



@router.get("/canvas")
async def canvas_page():
    p = BASE_DIR / "frontend" / "canvas.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/n8n-browse")
async def n8n_browse_page():
    p = BASE_DIR / "frontend" / "n8n.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/workflow")
async def workflow_page():
    try:
        from api.routes.routes_new_features import _WORKFLOW_HTML
        from fastapi.responses import HTMLResponse
        return HTMLResponse(_WORKFLOW_HTML)
    except Exception:
        p = BASE_DIR / "frontend" / "canvas.html"
        if p.exists(): return FileResponse(str(p))
        raise HTTPException(404)

@router.get("/enterprise")

@router.get("/enterprise.html")

async def enterprise_page():

    p = BASE_DIR / "frontend" / "enterprise.html"

    if p.exists(): return FileResponse(str(p))

    raise HTTPException(404)



@router.get("/billion-os")
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



@router.get("/agents")
async def agents_page():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/frontend/agents.html")

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



@router.get("/i18n-loader.js")
async def i18n_loader_js():
    p = BASE_DIR / "frontend" / "i18n-loader.js"
    return FileResponse(str(p), media_type="application/javascript")

@router.get("/share.css")
async def share_css():
    p = BASE_DIR / "frontend" / "share.css"
    return FileResponse(str(p), media_type="text/css")

@router.get("/components.js")
async def components_js():
    p = BASE_DIR / "frontend" / "components.js"
    return FileResponse(str(p), media_type="application/javascript")

@router.get("/register")
async def register_page():
    p = BASE_DIR / "frontend" / "register.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/forgot-password")
async def forgot_password_page():
    p = BASE_DIR / "frontend" / "forgot-password.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/chat_engine.js")

async def chat_engine_js():

    p = BASE_DIR / "frontend" / "chat_engine.js"

    if p.exists(): return FileResponse(str(p), media_type="application/javascript")

    raise HTTPException(404)


@router.get("/enterprise-modules.js")

async def enterprise_modules_js():

    p = BASE_DIR / "frontend" / "enterprise-modules.js"

    if p.exists(): return FileResponse(str(p), media_type="application/javascript")

    raise HTTPException(404)



# ── 补充缺少的路由 ──

@router.get("/output")

async def output_page():

    p = BASE_DIR / "output" / "index.html"

    if p.exists(): return FileResponse(str(p))

    topbar = '<div class="topbar"><button class="topbar-back" onclick="window.location.href=\'/\'">← 返回</button><span class="topbar-title">📂 输出目录</span></div>'

    html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>输出目录 - AUTO-EVO-AI</title><link rel="stylesheet" href="/frontend/share.css"><style>
body{margin:0;padding:0;background:var(--bg);color:var(--text);font-family:-apple-system,'Segoe UI',sans-serif;min-height:100vh}
.c{max-width:600px;margin:60px auto;padding:20px;text-align:center}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:40px}
.ico{font-size:48px;margin-bottom:12px}
h2{font-size:18px;margin-bottom:8px}
p{font-size:12px;color:var(--text2);line-height:1.6;margin-bottom:16px}
.hint{display:inline-block;padding:6px 14px;background:var(--accent);color:#fff;border-radius:8px;font-size:12px;text-decoration:none}
.hint:hover{opacity:.85}
</style></head><body>""" + topbar + """
<div class="c"><div class="card">
<div class="ico">📂</div><h2>输出目录</h2>
<p>系统生成的文件、报告、截图等都在这里。<br>还没生成任何输出内容。</p>
<a class="hint" href="/">💬 去聊天框试试说"生成一份报告"</a>
</div></div></body></html>"""

    return HTMLResponse(html)



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

# ── 错误页面 ──
@router.get("/404")
async def err_404():
    p = BASE_DIR / "frontend" / "404.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)

@router.get("/500")
async def err_500():
    p = BASE_DIR / "frontend" / "500.html"
    if p.exists(): return FileResponse(str(p))
    raise HTTPException(404)


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



