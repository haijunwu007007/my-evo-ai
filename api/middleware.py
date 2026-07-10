"""
AUTO-EVO-AI V0.1 — API 中间件层
=================================
职责：独立于 api_server.py 的中间件，包括请求计数、安全认证、限流等。

依赖：
    from api.infra import app, registry, rate_limiter, manager, ...
"""

from __future__ import annotations

import os
import time
import asyncio
from pathlib import Path
from core.logging_config import get_logger
from fastapi import Request
from fastapi.responses import JSONResponse

from api.infra import (
    app, registry, rate_limiter, manager,
    _request_counter, _request_errors, _request_latency, _request_latency_ms,
    _API_KEY, _API_KEY_ENABLED,
    _api_cache, _CACHE_TTL, _CACHEABLE_PATHS, _CACHE_SHORT_PATHS, _cache_hits,
)
from core.auth_provider import verify_token, verify_api_key, get_auth_config, check_role

# ── Profiler 中间件（可选，pyinstrument 未安装时自动跳过）──
from api.profiler import profiling_middleware_dispatch, HAS_PYINSTRUMENT

logger = get_logger("evo.api")

# ── 公共路径白名单（无需认证/限流）──
_PUBLIC_PATHS = {
    "/static/fix.js", "/i18n.js", "/", "/health",
    "/js/", "/frontend/", "/output/",
    "/hub", "/dashboard", "/canvas", "/fork", "/ComposeCanvas",
    "/app/dashboard", "/dashboard", "/company.html", "/enterprise.html", "/preview_v637.html",
    "/api/v1/", "/company.html",
    "/api/auth/login", "/api/v1/auth/login", "/api/v1/user/login",
    "/api/v1/user/register", "/api/auth/register", "/api/v1/auth/register",
    "/docs", "/openapi.json", "/redoc",
    "/manifest.json", "/sw.js",
    "/api/auth/login", "/api/auth/config",
}


# ═══════════════════════════════════════════════════════
# Profiler 中间件（最先注册，包裹整个请求链路）
# ═══════════════════════════════════════════════════════

@app.middleware("http")
async def profiler_middleware(request: Request, call_next):
    return await profiling_middleware_dispatch(request, call_next)


# ═══════════════════════════════════════════════════════
# API 版本前缀：/api/* → /api/v1/* 向后兼容重写
# ═══════════════════════════════════════════════════════

_API_LEGACY_PREFIXES = ("/api/",)
_V1_PREFIX = "/api/v1/"

@app.middleware("http")
async def api_version_redirect(request: Request, call_next):
    path = request.url.path
    if path.startswith(_API_LEGACY_PREFIXES) and not path.startswith(_V1_PREFIX) and not path.startswith("/api/v2/"):
        new_path = _V1_PREFIX + path[len("/api/"):]
        request.scope["path"] = new_path
        request.scope["raw_path"] = new_path.encode()
    response = await call_next(request)
    return response


# ═══════════════════════════════════════════════════════
# 国际化中间件 — 设置 request.state.lang
# ═══════════════════════════════════════════════════════

_I18N_DIRS = [Path(__file__).resolve().parent.parent / "i18n"]
try:
    _I18N_DIRS = [d for d in _I18N_DIRS if d.is_dir()]
except Exception:
    _I18N_DIRS = []

@app.middleware("http")
async def i18n_middleware(request: Request, call_next):
    """根据 Accept-Language 设置 request.state.lang"""
    accept = request.headers.get("accept-language", "zh-CN")
    lang = accept.split(",")[0].strip().split(";")[0]
    request.state.lang = lang if lang else "zh-CN"
    response = await call_next(request)
    return response


# ═══════════════════════════════════════════════════════
# 缓存中间件 — 内存 LRU 缓存，对 GET 请求自动缓存
# ═══════════════════════════════════════════════════════

_cache_lock = asyncio.Lock()

@app.middleware("http")
async def cache_middleware(request: Request, call_next):
    """内存缓存 GET 请求响应，支持 TTL + 可缓存路径白名单"""
    path = request.url.path
    method = request.method
    if method != "GET":
        return await call_next(request)

    # 检查是否在缓存白名单中
    ttl = _CACHE_TTL
    if path in _CACHE_SHORT_PATHS:
        ttl = 2.0
    elif path not in _CACHEABLE_PATHS:
        return await call_next(request)

    # 查询缓存
    now = time.time()
    async with _cache_lock:
        cached = _api_cache.get(path)
        if cached and (now - cached["ts"]) < ttl and cached.get("content") is not None:
            from api import infra as _evo_infra
            _evo_infra._cache_hits += 1
            from fastapi.responses import JSONResponse
            return JSONResponse(content=cached["content"], status_code=200)

    # 未命中 → 正常处理并缓存
    response = await call_next(request)
    if response.status_code == 200:
        try:
            body = await response.json()
            async with _cache_lock:
                _api_cache[path] = {"ts": time.time(), "content": body}
        except Exception as _e:
            logger.warning(f"error: {_e}")
    return response


# ═══════════════════════════════════════════════════════
# 请求计数中间件
# ═══════════════════════════════════════════════════════

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """统计每个 /api 端点的调用次数/延迟/错误"""
    path = request.url.path
    if not path.startswith("/api") and path != "/metrics":
        return await call_next(request)
    t0 = time.time()
    response = await call_next(request)
    elapsed = (time.time() - t0) * 1000
    _request_counter[path] += 1
    _request_latency[path].append(elapsed)
    if len(_request_latency[path]) > 100:
        _request_latency[path] = _request_latency[path][-100:]
    _request_latency_ms[path] = sum(_request_latency[path]) / len(_request_latency[path])
    if response.status_code >= 400:
        _request_errors[path] += 1
    return response


# ═══════════════════════════════════════════════════════
# 安全中间件 — 认证 + 限流 + 异常处理
# ═══════════════════════════════════════════════════════

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """API Key 校验 + 限流 + 全局异常捕获"""
    start_time = time.time()
    path = request.url.path
    method = request.method
    client_ip = request.client.host if request.client else "unknown"
    status_code = 500
    error_msg = ""
    remaining = 0
    reset_at = 0

    try:
        # ⚠️ 拦截 .env 路径探测攻击
        _blocked_suffixes = [".env", ".git/config", "wp-admin", "phpmyadmin"]
        if any(p in path.lower() for p in _blocked_suffixes):
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "not_found", "message": "资源不存在"},
            )

        # 公共路径直接放行
        is_public = any(
            path == p or path.startswith(p)
            for p in ["/docs", "/redoc", "/openapi", "/static", "/icon-", "/js/", "/frontend/"]
        ) or path in _PUBLIC_PATHS or any(path.startswith(p) for p in _PUBLIC_PATHS if p.endswith("/"))

        # API Key 验证
        if _API_KEY_ENABLED and not is_public:
            api_key = request.headers.get("X-API-Key", "")
            if not api_key or api_key != _API_KEY:
                status_code = 401
                error_msg = "Invalid API Key"
                return JSONResponse(
                    status_code=401,
                    content={"success": False, "error": "unauthorized", "message": "无效的 API Key", "status_code": 401},
                )

        # JWT 认证（环境变量 EVO_AUTH_ENABLED=true 时启用）
        auth_enabled = os.environ.get("EVO_AUTH_ENABLED", "false").lower() == "true"
        if auth_enabled and not is_public:
            auth_header = request.headers.get("Authorization", "")
            token = ""
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
            if not token:
                # 也支持 X-API-Key 作为 fallback
                api_key = request.headers.get("X-API-Key", "")
                if api_key and verify_api_key(api_key):
                    pass  # API Key 通过
                else:
                    status_code = 401
                    return JSONResponse(
                        status_code=401,
                        content={"success": False, "error": "unauthorized", "message": "缺少认证令牌", "status_code": 401},
                    )
            else:
                payload = verify_token(token)
                if payload is None:
                    status_code = 401
                    return JSONResponse(
                        status_code=401,
                        content={"success": False, "error": "token_invalid", "message": "令牌无效或已过期", "status_code": 401},
                    )
                request.state.user = payload

        # 限流检查
        remaining, reset_at = 0, 0
        if not is_public:
            allowed, remaining, reset_at = await rate_limiter.is_allowed(client_ip, method, path)
            if not allowed:
                status_code = 429
                return JSONResponse(
                    status_code=429,
                    content={"success": False, "error": "rate_limited", "message": "请求过于频繁，请稍后重试", "status_code": 429},
                    headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reset_at)},
                )

        response = await call_next(request)
        status_code = response.status_code
        if not is_public:
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_at)
        return response
    except Exception as e:
        error_msg = str(e)
        import traceback
        tb = traceback.format_exc()
        logger.error(f"[MIDDLEWARE] 未捕获异常: {path} - {error_msg}\n{tb[:2000]}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "detail": "服务器内部错误"},
        )
    finally:
        from api.infra import _record_audit
        latency = (time.time() - start_time) * 1000
        _record_audit(method, path, client_ip, status_code, latency, error_msg)
