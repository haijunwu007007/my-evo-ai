"""AUTO-EVO-AI V0.1 — API服务器（入口文件）
====================================
路由已拆分到 api/routes/routes_*.py（含 routes_static.py 静态资源）
中间件已拆分到 api/middleware.py
后台任务已拆分到 api/startup.py
本文件只保留：应用初始化 + 路由注册 + 入口
"""

from __future__ import annotations
import os, sys, json, time, asyncio, importlib
from typing import Any
from datetime import datetime
from pathlib import Path


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
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn

class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    """限制请求体最大10MB，防止DoS"""
    async def dispatch(self, request, call_next):
        cl = request.headers.get("content-length")
        if cl and int(cl) > 10_485_760:
            return JSONResponse(status_code=413, content={"success": False, "error": "请求体过大", "max_size_mb": 10})
        return await call_next(request)

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
VERSION_BUILD = "20260620"
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

# ── 多Worker + 熔断器 + 配置热加载 ──
from api._multi_worker import get_worker_count, get_circuit_breaker, with_timeout
_WORKER_COUNT = get_worker_count()


# ── RBAC ──
try:
    from api._rbac import RBACMiddleware, check_permission
    _rbac_ok = True
except Exception:
    _rbac_ok = False


# ── 统一响应格式 ──
try:
    from api._response import StandardResponse
    _response_ok = True
except Exception:
    _response_ok = False

# ── 加载中间件（副作用：注册 @app.middleware）──
import api.middleware  # noqa: F401

# ── RBAC 集成 ──
if _rbac_ok:
    try:
        from api._rbac import require_role
        # require_role 作为装饰器在路由中使用
        logger.info("[rbac] RBAC loaded (require_role decorator)")
    except Exception:
        pass

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

# ── 批量注册路由模块（自动发现 api/routes/routes_*.py + hub_static.py）──
# 新增路由只需创建 routes_xxx.py，无需修改本文件
from api.routes import register_all_routers
_router_count = register_all_routers(app)
logger.info("[ROUTES] 已注册 %d 个路由模块", _router_count)

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

js_dir = BASE_DIR / "js"
if js_dir.exists():
    app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")

output_dir = BASE_DIR / "output"
if output_dir.exists():
    app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")

frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")

uploads_dir = BASE_DIR / "uploads"
if uploads_dir.exists():
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


# ═══════════════════════════════════════════════════════
# 全局异常处理 — 统一 JSON 响应格式
# ═══════════════════════════════════════════════════════


def _error_response(status: int, error: str, message: str, detail: str = "") -> dict:
    return {"success": False, "error": error, "message": message, "detail": detail, "status_code": status}

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content=_error_response(404, "not_found", f"资源不存在: {request.url.path}"),
    )

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

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=_error_response(422, "validation_error", "请求参数验证失败", str(exc.errors())[:500]),
    )

# ═══════════════════════════════════════════════════════
# 根端点
# ═══════════════════════════════════════════════════════

@app.get("/")
async def root(request: Request = None):
    from fastapi.responses import FileResponse, HTMLResponse
    from api.infra import BASE_DIR
    import html as _pyhtml
    # / 路由由 lifespan 的 _mount_vue_frontend 覆盖，此处只做兜底
    chat_path = BASE_DIR / "frontend" / "chat.html"
    # Server-side expert injection (most reliable approach)
    if request and request.query_params and request.query_params.get("expert"):
        expert = request.query_params.get("expert", "")
        dept = request.query_params.get("dept", "")
        if chat_path.exists():
            html = chat_path.read_text(encoding="utf-8")
            safe_name = _pyhtml.escape(expert)
            safe_dept = _pyhtml.escape(dept)
            script = f"""<script>document.addEventListener("DOMContentLoaded",function(){{
var i=document.getElementById("input");if(i){{i.value="{safe_name}：";i.focus()}}
var g=document.getElementById("greeting");if(g)g.textContent="🎯 已激活专家: {safe_name}"
var sys="你现在是 {safe_name}（{safe_dept}）。你是这个领域的专家，请始终保持这个角色身份回答问题。"
try{{CTX=CTX||[]}}catch(ex){{}};CTX.push({{role:"system",content:sys}})
try{{CHAT=CHAT||[]}}catch(ex){{}};addMsg("🎯 已激活专家: {safe_name}（{safe_dept}）","bot")
window.history.replaceState({{}},"","/")}})</script></body>"""
            return HTMLResponse(html.replace("</body>", script))
    if chat_path.exists():
        return FileResponse(str(chat_path))
    idx_path = BASE_DIR / "frontend" / "index.html"
    if idx_path.exists():
        return FileResponse(str(idx_path))


@app.get("/{path:path}")
async def serve_static_html(path: str):
    """兜底：frontend/ 下的任意 .html 文件自动可访问"""
    from fastapi.responses import FileResponse
    from api.infra import BASE_DIR
    if path.endswith(".html"):
        fp = BASE_DIR / "frontend" / path
        if fp.exists() and fp.is_file():
            return FileResponse(str(fp))
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Not Found")


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
                "automation_score": coord.get_automation_score() or 0,
                "modules_registered": st.get("modules", {}).get("registered", 0) or len(registry.modules),
                "modules_healthy": st.get("modules", {}).get("healthy", 0) or 0,
            }
        except Exception:
            coord_data = {"status": "initializing"}
    return {
        "success": True,
        "system": BUILD_TAG,
        "status": "running",
        "uptime": datetime.now().isoformat(),
        "modules_loaded": len(registry.modules) + len(getattr(registry, '_pending_modules', {})),
        "modules_total": len([p for p in Path(__file__).parent.glob("modules/*.py") if p.name != "__init__.py"]),
        "modules_files": len([p for p in Path(__file__).parent.glob("modules/*.py") if p.name != "__init__.py"]),
        "modules_stub": registry.get_stub_count(),
        "coordinator": coord_data,
        "api_version": VERSION,
    }


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
# 以下端点已抽离到独立路由文件：
#   routes_auth.py  — 认证 (login/config/verify)
#   routes_metrics.py — Prometheus 指标 + 健康检查
#   routes_static.py — 静态资源 (manifest/icon/sw/docs/i18n)
# 自动发现系统（routes/__init__.py）会自动注册它们。
# ═══════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    # 从配置系统读取 host/port，环境变量可覆盖
    port = int(get_config_value(_EVO_CONFIG, "server.port", 8765))
    host = get_config_value(_EVO_CONFIG, "server.host", "127.0.0.1")
    reload = os.environ.get("EVO_RELOAD", "").lower() in ("1", "true", "yes")
    _frozen = getattr(sys, 'frozen', False)

    # 启动时预热 — warmup_modules 已由 lifespan 异步调用，此处无需重复执行
    # 见 api/startup.py lifespan() 中 asyncio.create_task(warmup_modules())
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

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        reload=reload,
        workers=_WORKER_COUNT,
    )

# routes 已全部迁移到 api/routes/（自动发现注册）