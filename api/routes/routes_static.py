"""
路由文件: routes_static.py — 静态资源和前端路由端点

从 api_server.py 抽离的内联端点，保持功能不变。
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from pathlib import Path
from api.infra import BASE_DIR

router = APIRouter(tags=["static"])


@router.get("/apps")
async def apps_list():
    """列出已生成的 APP 文件"""
    apps_dir = BASE_DIR / "output" / "apps"
    apps = []
    if apps_dir.exists():
        for f in sorted(apps_dir.glob("*.html"), reverse=True)[:50]:
            apps.append({
                "name": f.stem[:40],
                "url": f"/output/apps/{f.name}",
                "size": f"{f.stat().st_size / 1024:.1f}KB",
                "date": __import__("time").ctime(f.stat().st_mtime),
            })
    html = f"""<!DOCTYPE html><html><head>
<meta charset="UTF-8"><title>已生成APP</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{{font-family:-apple-system,system-ui,sans-serif;background:#0f0f1a;color:#e2e8f0;max-width:800px;margin:0 auto;padding:20px}}
h1{{font-size:24px}}
.app{{background:#1a1a2e;border-radius:12px;padding:16px;margin:12px 0;border:1px solid #2d2d4a}}
.app a{{color:#818cf8;text-decoration:none;font-size:16px}}
.meta{{color:#64748b;font-size:12px;margin-top:4px}}
.size{{color:#22c55e}}
.empty{{text-align:center;padding:60px;color:#64748b}}
@media(max-width:480px){{body{{padding:10px}}h1{{font-size:20px}}.app{{padding:12px}}}}
</style></head><body><h1>📂 已生成APP</h1>"""
    if not apps:
        html += '<div class="empty">还没有APP<br>试试说"开发一个任务管理系统"</div>'
    for a in apps:
        html += (
            f'<div class="app"><a href="{a["url"]}" target="_blank">{a["name"]}</a>'
            f'<div class="meta"><span class="size">{a["size"]}</span> · {a["date"]}</div></div>'
        )
    html += "</body></html>"
    return HTMLResponse(html)


@router.get("/manifest.json")
async def get_manifest():
    """PWA manifest 文件"""
    manifest_path = BASE_DIR / "manifest.json"
    if manifest_path.exists():
        return FileResponse(str(manifest_path), media_type="application/json")
    return JSONResponse({"name": "AUTO-EVO-AI", "short_name": "EVO-AI"})


@router.get("/icon-{size}.png")
async def get_icon(size: int):
    """PWA 图标"""
    icon_path = BASE_DIR / f"icon-{size}.png"
    if icon_path.exists():
        return FileResponse(str(icon_path), media_type="image/png")
    raise HTTPException(404)


@router.get("/sw.js")
async def service_worker():
    """Service Worker"""
    sw_path = BASE_DIR / "sw.js"
    if sw_path.exists():
        return FileResponse(sw_path, media_type="application/javascript")
    return StreamingResponse(iter(["// Service Worker"]), media_type="application/javascript")


@router.get("/api/docs")
async def api_docs_redirect():
    """API 文档重定向到 Scalar"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/scalar")


@router.get("/i18n.js")
async def i18n_js():
    """返回国际化 JS 配置"""
    i18n_path = BASE_DIR / "frontend" / "i18n.js"
    if i18n_path.exists():
        return FileResponse(str(i18n_path), media_type="application/javascript")
    return JSONResponse({"error": "i18n file not found"})


@router.get("/frontend/i18n.js", include_in_schema=False)
async def frontend_i18n_js():
    """兼容旧路径的 i18n.js"""
    js_path = BASE_DIR / "js" / "i18n.js"
    if js_path.exists():
        return FileResponse(str(js_path))
    return JSONResponse({"success": False, "error": "i18n.js not found"})


# ── 前端页面路由 ──

@router.get("/canvas")
async def canvas_page():
    """工作流画布页面"""
    html_path = BASE_DIR / "frontend" / "canvas.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    raise HTTPException(404)

@router.get("/fork")
async def fork_page():
    """Fork 工作室页面"""
    html_path = BASE_DIR / "frontend" / "ForkStudio.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    raise HTTPException(404)

@router.get("/company.html")
async def company_page():
    """虚拟公司页面"""
    html_path = BASE_DIR / "frontend" / "company.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    raise HTTPException(404)

@router.get("/dashboard")
async def dash_route():
    """仪表盘"""
    from fastapi.responses import HTMLResponse
    html_path = BASE_DIR / "frontend" / "dashboard.html"
    if html_path.exists():
        html = html_path.read_text(encoding="utf-8")
        # Add no-cache headers and version bust
        html = html.replace('</head>', '<meta http-equiv="Pragma" content="no-cache"><meta http-equiv="Expires" content="0"><style>body{transition:opacity .3s}</style></head>')
        return HTMLResponse(html, headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})
    return FileResponse(str(BASE_DIR / "frontend" / "chat.html"))

@router.get("/app/dashboard")
@router.get("/app/dash")
@router.get("/dash")
async def app_dashboard_route():
    """仪表盘（showDashboard 跳转目标）"""
    html_path = BASE_DIR / "frontend" / "dashboard.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return FileResponse(str(BASE_DIR / "frontend" / "chat.html"))

@router.get("/enterprise.html")
async def enterprise_page():
    """企业管理 — V0.1完整模块管理器"""
    html_path = BASE_DIR / "frontend" / "enterprise.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    raise HTTPException(404)

@router.get("/deploy")
async def deploy_page():
    """一键部署页面"""
    html_path = BASE_DIR / "frontend" / "deploy.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    raise HTTPException(404)

@router.get("/ComposeCanvas")
async def compose_canvas_page():
    """组合画布页面"""
    html_path = BASE_DIR / "frontend" / "ComposeCanvas.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    raise HTTPException(404)

@router.get("/office")
async def office_page():
    """文档办公套件页面"""
    html_path = BASE_DIR / "frontend" / "docs.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    raise HTTPException(404)

@router.get("/review")
async def review_page():
    """AI 代码审查 + Diff 对比页面"""
    html_path = BASE_DIR / "frontend" / "review.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    raise HTTPException(404)

@router.get("/hooks")
async def hooks_page():
    """Hooks 拦截器配置页面"""
    html_path = BASE_DIR / "frontend" / "hooks.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    raise HTTPException(404)
