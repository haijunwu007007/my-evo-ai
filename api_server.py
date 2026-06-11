"""AUTO-EVO-AI V0.1 — API服务器（入口文件）
====================================
路由已拆分到 api/routes_*.py
中间件已拆分到 api/middleware.py
后台任务已拆分到 api/startup.py
本文件只保留：端点注册 + 静态资源 + 入口
"""

from __future__ import annotations
import os, sys, json, time, asyncio, importlib
from typing import Any
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict

# ── 统一 HTTP 客户端（在任意模块导入前生效）──
try:
    from modules._client import configure_requests
    configure_requests()
except Exception:
    pass

# ── 统一路径（从共享模块计算 BASE_DIR + sys.path.insert）──
from api._paths import BASE_DIR

# ── FastAPI ──
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# ── 日志 ──
from core.logging_config import get_logger

# ── 配置系统 ──
from core.config_loader import load_config, get_config_value
_EVO_CONFIG = load_config()  # 全局配置字典

# 从配置中读取 JSON 日志开关（在 logger 创建前生效）
if get_config_value(_EVO_CONFIG, "logging.json_format", False):
    os.environ["EVO_LOG_JSON"] = "true"

logger = get_logger("evo.api")

# ── 版本常量（集中管理，升级只需改此处）──
VERSION = "V0.1"
VERSION_BUILD = "20260609"
BUILD_TAG = f"AUTO-EVO-AI {VERSION}"

# ── 导入共享基础设施 ──
from api.infra import (
    app, registry, rate_limiter, manager,
    _request_counter, _request_errors, _request_latency, _request_latency_ms,
    _cache_hits, _api_cache, _CACHE_TTL, _CACHEABLE_PATHS, _CACHE_SHORT_PATHS,
    _execution_log, _invalidate_caches, _append_exec_log,
    _module_activity, _START_TIME, _API_KEY, _API_KEY_ENABLED,
    get_coordinator_v3, get_planner,
)

# ── 加载中间件（副作用：注册 @app.middleware）──
import api.middleware  # noqa: F401

# ── Scalar API 文档（替换 Swagger UI）──
try:
    from scalar_fastapi import get_scalar_api_reference
    @app.get("/scalar", include_in_schema=False)
    async def scalar_html():
        return get_scalar_api_reference(
            openapi_url=app.openapi_url,
            title=f"{BUILD_TAG} API 文档",
        )
    logger.info("[SCALAR] API 文档已挂载: /scalar")
except ImportError:
    logger.warning("[SCALAR] scalar-fastapi 未安装，使用默认 /docs")

# ── Profiler 模块 ──
from api.profiler import router as profiler_router

app.include_router(profiler_router)
import api.startup  # noqa: F401

# ── 注册路由模块 ──
from api.routes.routes_modules import router as modules_router
from api.routes.routes_services import router as services_router
from api.routes.routes_ws import router as ws_router
from api.routes.routes_auth_system import router as auth_system_router
from api.routes.routes_scheduler import router as scheduler_router
from api.routes.routes_coordinator import router as coordinator_router
from api.routes.routes_insights import router as insights_router
from api.routes.routes_modules_browse import router as modules_browse_router
from api.routes.routes_litellm import router as litellm_router
from api.routes.routes_agent_s import router as agent_s_router
from api.routes.routes_missing import router as missing_router
from api.routes.routes_tools_health import router as tools_health_router
from api.routes.routes_gitea_sync import router as gitea_sync_router
from api.routes.routes_metabase_bridge import router as metabase_bridge_router
from api.routes.routes_workflows import router as workflows_router
from api.routes.routes_dify import router as dify_router
from api.routes.routes_chroma import router as chroma_router
from api.routes.routes_browser_use import router as browser_use_router
from api.routes.routes_filebrowser import router as filebrowser_router
from api.routes.routes_openclaw import router as openclaw_router
from api.routes.routes_meilisearch import router as meili_router
from api.routes.routes_stirling_pdf import router as stirling_router
from api.routes.routes_uptime_kuma import router as uptime_router
from api.routes.routes_nextchat import router as nextchat_router
from api.routes.routes_langfuse import router as langfuse_router
from api.routes.routes_superset import router as superset_router
from api.routes.routes_activepieces import router as activepieces_router
from api.routes.routes_hoppscotch import router as hoppscotch_router
from api.routes.routes_tabby import router as tabby_router
from api.routes.routes_firecrawl import router as firecrawl_router
from api.routes.routes_mcp import router as mcp_router
from api.routes.routes_minio import router as minio_router
from api.routes.routes_portainer import router as portainer_router
from api.routes.routes_grafana import router as grafana_router
from api.routes.routes_outline import router as outline_router
from api.routes.routes_appsmith import router as appsmith_router
from api.routes.routes_code_server import router as code_server_router
from api.routes.routes_dashy import router as dashy_router
from api.routes.routes_ntfy import router as ntfy_router
from api.routes.routes_nocodb import router as nocodb_router
from api.routes.routes_changedetection import router as changedetection_router
from api.routes.routes_setup import router as setup_router
from api.routes.routes_chat import router as chat_router
from api.routes.routes_plugins import router as plugins_router
from api.routes.routes_agents import router as agents_router
from api.routes.routes_llm_chat import router as llm_chat_router
from api.routes.routes_new_features import router as new_features_router
from api.routes.routes_i18n import router as i18n_router
from api.routes.routes_smart_chat import router as smart_chat_router
from api.routes.routes_skills import router as skills_router
from api.routes.routes_rag import router as rag_router
from api.routes.routes_connectors import router as connectors_router
from api.routes.routes_mcpize import router as mcpize_router
from api.routes.routes_agent_engine import router as agent_engine_router
from api.routes.routes_public_api import router as public_api_router
from api.routes.routes_gateway import router as gateway_router
from api.routes.routes_rest2mcp import router as rest2mcp_router
from api.routes.routes_a2a import router as a2a_router
from api.routes.routes_multitenant import router as tenant_router
from api.routes.routes_analytics import router as analytics_router
from api.routes.routes_events import router as events_router
from api.routes.routes_diagnosis import router as diagnosis_router
from api.routes.routes_selfheal import router as selfheal_router
from api.routes.routes_rerank import router as rerank_router
from api.routes.routes_agent_team import router as agent_team_router
from api.routes.routes_env import router as env_router
from api.routes.routes_skills_market import router as skills_market_router
from api.routes.routes_github import router as github_router

app.include_router(skills_market_router)
app.include_router(selfheal_router)
app.include_router(rerank_router)
app.include_router(agent_team_router)
app.include_router(modules_browse_router)
app.include_router(litellm_router)
app.include_router(agent_s_router)
app.include_router(tools_health_router)
app.include_router(gitea_sync_router)
app.include_router(metabase_bridge_router)
app.include_router(workflows_router)
app.include_router(modules_router)
app.include_router(services_router)
app.include_router(ws_router)
app.include_router(auth_system_router)
app.include_router(scheduler_router)
app.include_router(coordinator_router)
app.include_router(insights_router)
app.include_router(dify_router)
app.include_router(chroma_router)
app.include_router(meili_router)
app.include_router(browser_use_router)
app.include_router(filebrowser_router)
app.include_router(openclaw_router)
app.include_router(stirling_router)
app.include_router(uptime_router)
app.include_router(nextchat_router)
app.include_router(langfuse_router)
app.include_router(superset_router)
app.include_router(activepieces_router)
app.include_router(hoppscotch_router)
app.include_router(tabby_router)
app.include_router(firecrawl_router)
app.include_router(mcp_router)
app.include_router(minio_router)
app.include_router(portainer_router)
app.include_router(grafana_router)
app.include_router(outline_router)
app.include_router(appsmith_router)
app.include_router(code_server_router)
app.include_router(missing_router)

app.include_router(dashy_router)
app.include_router(ntfy_router)
app.include_router(nocodb_router)
app.include_router(changedetection_router)
app.include_router(setup_router)
app.include_router(chat_router)
app.include_router(plugins_router)
app.include_router(agents_router)
app.include_router(llm_chat_router)
app.include_router(new_features_router)
app.include_router(i18n_router)
app.include_router(smart_chat_router)
app.include_router(skills_router)
app.include_router(rag_router)
app.include_router(connectors_router)
app.include_router(mcpize_router)
app.include_router(agent_engine_router)
app.include_router(public_api_router)
app.include_router(gateway_router)
app.include_router(rest2mcp_router)
app.include_router(a2a_router)
app.include_router(tenant_router)
app.include_router(analytics_router)
app.include_router(events_router)
app.include_router(diagnosis_router)
app.include_router(env_router)
app.include_router(github_router)

# ── 动态路由加载（LLM创建的新API自动挂载） ──
_apidir = Path(__file__).parent / "output" / "api"
_apidir.mkdir(parents=True, exist_ok=True)
for _f in sorted(_apidir.glob("*.py")):
    try:
        _mod = importlib.import_module(f"output.api.{_f.stem}")
        if hasattr(_mod, 'router'):
            app.include_router(_mod.router, prefix="/api/ext")
    except Exception:
        pass


# ── 静态文件 ──
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

frontend_static = BASE_DIR / "frontend" / "static"
if frontend_static.exists():
    app.mount("/frontend/static", StaticFiles(directory=str(frontend_static)), name="frontend_static")

output_dir = BASE_DIR / "output"
if output_dir.exists():
    app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")

frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")


# ═══════════════════════════════════════════════════════
# 全局异常处理 — 统一 JSON 响应格式
# ═══════════════════════════════════════════════════════

def _error_response(status: int, error: str, message: str, detail: str = "") -> dict:
    return {"success": False, "error": error, "message": message, "detail": detail, "status_code": status}

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_response(exc.status_code, "http_error", str(exc.detail), exc.detail if isinstance(exc.detail, str) else ""),
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    tb = traceback.format_exc()
    logger.error(f"[FATAL] {request.method} {request.url.path}: {exc}\n{tb[:2000]}")
    return JSONResponse(
        status_code=500,
        content=_error_response(500, "internal_error", "服务器内部错误", str(exc)[:500]),
    )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content=_error_response(404, "not_found", f"资源不存在: {request.url.path}"),
    )

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=_error_response(422, "validation_error", "请求参数验证失败", str(exc.errors())[:500]),
    )

# ═══════════════════════════════════════════════════════
# 根端点
# ═══════════════════════════════════════════════════════

# ── 生产路由（仅保留生产文件）──

@app.get("/apps")
async def apps_list():
    from fastapi.responses import HTMLResponse
    from api.infra import BASE_DIR
    from pathlib import Path
    apps_dir = BASE_DIR / "output" / "apps"
    apps = []
    if apps_dir.exists():
        for f in sorted(apps_dir.glob("*.html"), reverse=True)[:50]:
            apps.append({"name":f.stem[:40], "url":f"/output/apps/{f.name}", "size":f"{f.stat().st_size/1024:.1f}KB", "date":__import__('time').ctime(f.stat().st_mtime)})
    html = '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>已生成APP</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{font-family:-apple-system,system-ui,sans-serif;background:#0f0f1a;color:#e2e8f0;max-width:800px;margin:0 auto;padding:20px}h1{font-size:24px}.app{background:#1a1a2e;border-radius:12px;padding:16px;margin:12px 0;border:1px solid #2d2d4a}.app a{color:#818cf8;text-decoration:none;font-size:16px}.meta{color:#64748b;font-size:12px;margin-top:4px}.size{color:#22c55e}.empty{text-align:center;padding:60px;color:#64748b}</style></head><body><h1>📂 已生成APP</h1>'
    if not apps: html += '<div class="empty">还没有APP<br>试试说"开发一个任务管理系统"</div>'
    for a in apps: html += f'<div class="app"><a href="{a["url"]}" target="_blank">{a["name"]}</a><div class="meta"><span class="size">{a["size"]}</span> · {a["date"]}</div></div>'
    html += '</body></html>'
    return HTMLResponse(html)

@app.get("/")
async def root():
    from fastapi.responses import FileResponse
    from api.infra import BASE_DIR
    chat_path = BASE_DIR / "frontend" / "chat.html"
    if chat_path.exists():
        return FileResponse(str(chat_path))
    # fallback: 返回 JSON 状态
    return {
        "success": True,
        "system": BUILD_TAG,
        "status": "running",
        "modules_files": len([p for p in Path(__file__).parent.glob("modules/*.py") if p.name != "__init__.py"]),
        "modules_stub": registry.get_stub_count(),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/status")
@app.get("/api/v1/status")
async def system_status():
    coord = get_coordinator_v3()
    coord_data = {}
    if coord:
        try:
            st = coord.get_status()
            coord_data = {
                "version": VERSION,
                "coordinator_version": "3.0.0",
                "status": st.get("status", "ready"),
                "automation_score": coord.get_automation_score(),
                "modules_registered": st.get("modules", {}).get("registered", 0),
                "modules_healthy": st.get("modules", {}).get("healthy", 0),
            }
        except Exception:
            coord_data = {"status": "initializing"}
    return {
        "success": True,
        "system": BUILD_TAG,
        "status": "running",
        "uptime": datetime.now().isoformat(),
        "modules_loaded": len(registry.modules),
        "modules_total": len(registry._pending_modules) + len(registry.modules),
        "modules_files": len([p for p in Path(__file__).parent.glob("modules/*.py") if p.name != "__init__.py"]),
        "modules_stub": registry.get_stub_count(),
        "coordinator": coord_data,
        "api_version": VERSION,
    }


@app.get("/api/v1/health")
async def health_check():
    """系统健康检查端点"""
    return {"success": True, "status": "healthy", "version": VERSION, "timestamp": __import__('time').time()}

@app.get("/api/v1/version")
async def get_version():
    """系统版本信息 — modules统一使用registry计数（与status一致）"""
    _mod_count = 0
    try:
        from api.infra import registry as _registry
        _mod_count = len(_registry._pending_modules) + len(_registry.modules)
    except Exception:
        pass
    return {"success": True, "version": VERSION, "build": VERSION_BUILD, "modules": _mod_count}


# ═══════════════════════════════════════════════════════
# i18n 及 PWA 静态资源（由 api/startup.py 中 _mount_vue_frontend()
# 挂载 Vue SPA 前端 + /assets 静态文件 + 路由兜底）
# ═══════════════════════════════════════════════════════

@app.get("/manifest.json")
async def get_manifest():
    manifest_path = BASE_DIR / "manifest.json"
    if manifest_path.exists():
        return FileResponse(str(manifest_path), media_type="application/json")
    return JSONResponse({"name": "AUTO-EVO-AI", "short_name": "EVO-AI"})


@app.get("/icon-{size}.png")
async def get_icon(size: int):
    icon_path = BASE_DIR / f"icon-{size}.png"
    if icon_path.exists():
        return FileResponse(str(icon_path), media_type="image/png")
    raise HTTPException(404)


@app.get("/sw.js")
async def service_worker():
    sw_path = BASE_DIR / "sw.js"
    if sw_path.exists():
        return FileResponse(sw_path, media_type="application/javascript")
    return StreamingResponse(iter(["// Service Worker"]), media_type="application/javascript")

@app.get("/docs")
@app.get("/api/docs")
async def api_docs_redirect():
    """API 文档重定向到 Scalar"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/scalar")


@app.get("/i18n.js")
async def i18n_js():
    """返回国际化 JS 配置"""
    i18n_path = BASE_DIR / "frontend" / "i18n.js"
    if i18n_path.exists():
        return FileResponse(str(i18n_path), media_type="application/javascript")
    return {"error": "i18n file not found"}


# ═══════════════════════════════════════════════════════
# 认证端点
# ═══════════════════════════════════════════════════════

@dataclass
class LoginRequest:
    username: str = ""
    api_key: str = ""
    role: str = "user"

@dataclass
class TokenRefreshRequest:
    token: str = ""

@app.post("/api/auth/login")
@app.post("/api/v1/auth/login")
async def auth_login(req: LoginRequest):
    """登录获取 JWT 令牌。"""
    from core.auth_provider import create_token, verify_api_key, _ADMIN_KEY
    # 支持 API Key 登录
    if req.api_key:
        if verify_api_key(req.api_key):
            token = create_token(subject="api_user", role="admin" if req.api_key == _ADMIN_KEY else "user")
            return token
        return JSONResponse(status_code=401, content={"detail": "无效的 API Key", "error": "unauthorized"})
    # 支持用户名密码式（简化，生产环境应查数据库）
    if req.username:
        role = "admin" if req.username == "admin" else "user"
        token = create_token(subject=req.username, role=role)
        return token
    return JSONResponse(status_code=400, content={"detail": "请提供 username 或 api_key"})

@app.get("/api/auth/config")
@app.get("/api/v1/auth/config")
async def auth_config():
    """获取认证配置状态。"""
    from core.auth_provider import get_auth_config
    return get_auth_config()

@app.get("/api/auth/verify")
@app.get("/api/v1/auth/verify")
async def auth_verify(token: str = ""):
    """验证令牌是否有效。"""
    from core.auth_provider import verify_token
    payload = verify_token(token)
    if payload:
        return {"valid": True, "subject": payload.get("sub"), "role": payload.get("role"), "expires_at": payload.get("exp")}
    return {"valid": False, "error": "令牌无效或已过期"}


# ═══════════════════════════════════════════════════════
# Prometheus Metrics
# ═══════════════════════════════════════════════════════

@app.get("/metrics", include_in_schema=False)
@app.get("/api/v1/metrics", include_in_schema=False)
async def prometheus_metrics():
    now = time.time()
    uptime = now - _START_TIME
    lines: list = []
    lines.append(f"# {BUILD_TAG} Prometheus Metrics Export")

    # 模块级 Prometheus 指标（由 _prometheus 模块收集）
    try:
        from modules._prometheus import get_prometheus_text
        pt = get_prometheus_text()
        if pt.strip():
            lines.append("")
            lines.append("# -- modules._prometheus --")
            lines.append(pt)
    except Exception:
        pass

    health = registry.get_all_health()
    ok_count = sum(1 for h in health.values() if h.get("status") in ("ok", "healthy", "configured", "module_only"))
    err_count = sum(1 for h in health.values() if h.get("status") in ("error", "lazy_error", "timeout"))
    lazy_count = sum(1 for h in health.values() if h.get("status") in ("pending_lazy",))

    lines.append(f"evo_system_uptime_seconds {uptime:.0f}")
    lines.append(f"evo_modules_total {len(health)}")
    lines.append(f"evo_modules_healthy {ok_count}")
    lines.append(f"evo_modules_error {err_count}")
    stub_count = registry.get_stub_count()
    lines.append(f"evo_modules_lazy_pending {lazy_count}")
    lines.append(f"evo_modules_stub {stub_count}")

    for path, count in sorted(_request_counter.items()):
        lines.append(f'evo_http_requests_total{{endpoint="{path}"}} {count}')
    for path, count in sorted(_request_errors.items()):
        lines.append(f'evo_http_errors_total{{endpoint="{path}"}} {count}')
    for path, avg in sorted(_request_latency_ms.items()):
        lines.append(f'evo_http_request_duration_ms{{endpoint="{path}"}} {avg:.1f}')

    lines.append(f"evo_ws_connections_active {len(manager.active)}")
    lines.append(f"evo_cache_hits_total {_cache_hits}")
    lines.append(f"evo_cache_entries {len(_api_cache)}")

    # 引擎指标
    try:
        from api.routes.routes_scheduler import HAS_SCHEDULER, HAS_EVENTS, HAS_PIPELINE, HAS_QUEUE
        lines.append(f'evo_engine_active{{engine="scheduler"}} {1 if HAS_SCHEDULER else 0}')
        lines.append(f'evo_engine_active{{engine="events"}} {1 if HAS_EVENTS else 0}')
        lines.append(f'evo_engine_active{{engine="pipeline"}} {1 if HAS_PIPELINE else 0}')
        lines.append(f'evo_engine_active{{engine="queue"}} {1 if HAS_QUEUE else 0}')
    except Exception:
        pass

    text = "\n".join(lines)
    return Response(content=text, media_type="text/plain; version=0.0.4; charset=utf-8")


# ═══════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    # 从配置系统读取 host/port，环境变量可覆盖
    port = int(get_config_value(_EVO_CONFIG, "server.port", 8765))
    host = get_config_value(_EVO_CONFIG, "server.host", "127.0.0.1")
    reload = os.environ.get("EVO_RELOAD", "").lower() in ("1", "true", "yes")
    _frozen = getattr(sys, 'frozen', False)

    # 启动时预热（如果 startup 模块提供了 warmup 函数）
    try:
        from api.startup import warmup as _warmup_fn
        _warmup_fn()
    except (ImportError, Exception):
        pass

    auth_status = "已启用" if _API_KEY_ENABLED else "未启用"
    if os.environ.get("EVO_AUTH_ENABLED","true").lower()=="true":
        auth_status = "JWT+APIKey"
    print(f"""
┌──────────────────────────────────────────────────────┐
│  {BUILD_TAG} API Server  {'[EXE]' if _frozen else '[Python]'}
├──────────────────────────────────────────────────────┤
│  本地: http://{host}:{port:<5}                        │
│  文档: http://{host}:{port}/docs                     │
│  面板: http://{host}:{port}/dashboard                │
│  认证: {auth_status:<10}     │
│  限流: {rate_limiter.max_requests}req/{rate_limiter.window_seconds}s per IP
├──────────────────────────────────────────────────────┤
│  架构: api_server(入口) + api/middleware(中间件)      │
│        + api/startup(后台) + api/routes_*(65个路由文件)   │
└──────────────────────────────────────────────────────┘
""")

    if _frozen:
        import threading, webbrowser
        def _open_browser() -> Any:
            time.sleep(2)
            webbrowser.open(f"http://localhost:{port}/dashboard")
        threading.Thread(target=_open_browser, daemon=True).start()

    uvicorn.run(app, host=host, port=port, log_level="info", reload=reload)
