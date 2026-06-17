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

@app.get("/")
async def root():
    from fastapi.responses import FileResponse
    from api.infra import BASE_DIR
    chat_path = BASE_DIR / "frontend" / "chat.html"
    if chat_path.exists():
        return FileResponse(str(chat_path))


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
