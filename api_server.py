"""
AUTO-EVO-AI V0.1 — API服务器（入口文件）
====================================
路由已拆分到 api/routes_*.py
中间件已拆分到 api/middleware.py
后台任务已拆分到 api/startup.py
本文件只保留：端点注册 + 静态资源 + 入口
"""

from __future__ import annotations
import os, sys, json, time, asyncio, hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict

# ── 添加模块路径 ──
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _MEIPASS = Path(sys._MEIPASS)
    BASE_DIR = _MEIPASS
    _ORIGINAL_BASE = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent
    _ORIGINAL_BASE = BASE_DIR
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "modules"))

# ── FastAPI ──
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# ── 日志 ──
from core.logging_config import get_logger, StructuredLogger

# ── 配置系统 ──
from core.config_loader import load_config, get_config_value
_EVO_CONFIG = load_config()  # 全局配置字典

# 从配置中读取 JSON 日志开关（在 logger 创建前生效）
if get_config_value(_EVO_CONFIG, "logging.json_format", False):
    os.environ["EVO_LOG_JSON"] = "true"

logger = get_logger("evo.api")

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

# ── 加载后台任务（副作用：注册 @app.on_event("startup")）──
import api.startup  # noqa: F401

# ── 注册路由模块 ──
from api.routes_modules import router as modules_router
from api.routes_services import router as services_router
from api.routes_ws import router as ws_router
from api.routes_auth_system import router as auth_system_router
from api.routes_scheduler import router as scheduler_router
from api.routes_coordinator import router as coordinator_router
from api.routes_insights import router as insights_router
from api.routes_modules_browse import router as modules_browse_router

app.include_router(modules_browse_router)
app.include_router(modules_router)
app.include_router(services_router)
app.include_router(ws_router)
app.include_router(auth_system_router)
app.include_router(scheduler_router)
app.include_router(coordinator_router)
app.include_router(insights_router)

# ── Prometheus 指标端点 ──
@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    from modules._prometheus import get_prometheus_text
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(get_prometheus_text())

# ── 静态文件 ──
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

frontend_static = BASE_DIR / "frontend" / "static"
if frontend_static.exists():
    app.mount("/frontend/static", StaticFiles(directory=str(frontend_static)), name="frontend_static")


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
    return {
        "success": True,
        "system": "AUTO-EVO-AI V0.1",
        "status": "running",
        "modules_loaded": len(registry.modules),
        "modules_total": len(registry.classes) + len(registry._pending_modules),
        "modules_stub": registry.get_stub_count(),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/status")
async def system_status():
    coord = get_coordinator_v3()
    coord_data = {}
    if coord:
        try:
            st = coord.get_status()
            coord_data = {
                "version": "V0.1",
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
        "system": "AUTO-EVO-AI V0.1",
        "status": "running",
        "uptime": datetime.now().isoformat(),
        "modules_loaded": len(registry.modules),
        "modules_total": len(registry._pending_modules) + len(registry.modules),
        "modules_stub": registry.get_stub_count(),
        "coordinator": coord_data,
        "api_version": "0.1.0",
    }


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


@app.get("/i18n.js")
async def i18n_js():
    """返回国际化 JS 配置"""
    i18n_path = BASE_DIR / "i18n-patch.js"
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
async def auth_config():
    """获取认证配置状态。"""
    from core.auth_provider import get_auth_config
    return get_auth_config()

@app.get("/api/auth/verify")
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

@app.get("/metrics")
async def prometheus_metrics():
    now = time.time()
    uptime = now - _START_TIME
    lines = []
    lines.append("# AUTO-EVO-AI V0.1 Prometheus Metrics Export")

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
        safe = path.replace("/", "_").strip("_") or "root"
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
        from api.routes_scheduler import HAS_SCHEDULER, HAS_EVENTS, HAS_PIPELINE, HAS_QUEUE
        lines.append(f'evo_engine_active{{engine="scheduler"}} {1 if HAS_SCHEDULER else 0}')
        lines.append(f'evo_engine_active{{engine="events"}} {1 if HAS_EVENTS else 0}')
        lines.append(f'evo_engine_active{{engine="pipeline"}} {1 if HAS_PIPELINE else 0}')
        lines.append(f'evo_engine_active{{engine="queue"}} {1 if HAS_QUEUE else 0}')
    except Exception:
        pass

    text = "\n".join(lines)
    return JSONResponse(content=text, media_type="text/plain; version=0.0.4; charset=utf-8")


# ═══════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    # 从配置系统读取 host/port，环境变量可覆盖
    port = int(get_config_value(_EVO_CONFIG, "server.port", 8765))
    host = get_config_value(_EVO_CONFIG, "server.host", "127.0.0.1")
    reload = os.environ.get("EVO_RELOAD", "").lower() in ("1", "true", "yes")
    _frozen = getattr(sys, 'frozen', False)

    # 启动时预热
    from api.startup import warmup_modules
    try:
        asyncio.run(warmup_modules())
    except RuntimeError:
        pass  # 有运行中事件循环时跳过

    auth_status = "已启用" if _API_KEY_ENABLED else "未启用"
    if os.environ.get("EVO_AUTH_ENABLED","false").lower()=="true":
        auth_status = "JWT+APIKey"
    print(f"""
┌──────────────────────────────────────────────────────┐
│  AUTO-EVO-AI V0.1 API Server  {'[EXE]' if _frozen else '[Python]'}
├──────────────────────────────────────────────────────┤
│  本地: http://{host}:{port:<5}                        │
│  文档: http://{host}:{port}/docs                     │
│  面板: http://{host}:{port}/dashboard                │
│  认证: {auth_status:<10}     │
│  限流: {rate_limiter.max_requests}req/{rate_limiter.window_seconds}s per IP
├──────────────────────────────────────────────────────┤
│  架构: api_server(入口) + api/middleware(中间件)      │
│        + api/startup(后台) + api/routes_*(4个路由)   │
└──────────────────────────────────────────────────────┘
""")

    if _frozen:
        import threading, webbrowser
        def _open_browser() -> Any:
            time.sleep(2)
            webbrowser.open(f"http://localhost:{port}/dashboard")
        threading.Thread(target=_open_browser, daemon=True).start()

    uvicorn.run(app, host=host, port=port, log_level="info", reload=reload)
