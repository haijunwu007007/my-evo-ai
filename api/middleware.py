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
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

from api.infra import (
    app, registry, rate_limiter, manager,
    _request_counter, _request_errors, _request_latency, _request_latency_ms,
    _API_KEY, _API_KEY_ENABLED,
)
from core.auth_provider import verify_token, verify_api_key, get_auth_config, check_role

# ── Profiler 中间件（可选，pyinstrument 未安装时自动跳过）──
from api.profiler import profiling_middleware_dispatch, HAS_PYINSTRUMENT

logger = logging.getLogger("evo.api")

# ── 公共路径白名单（无需认证/限流）──
_PUBLIC_PATHS = {
    "/static/fix.js", "/i18n.js", "/", "/health",
    "/docs", "/openapi.json", "/redoc", "/dashboard",
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

    try:
        # 公共路径直接放行
        is_public = any(
            path == p or path.startswith(p)
            for p in ["/docs", "/redoc", "/openapi", "/static", "/icon-"]
        ) or path in _PUBLIC_PATHS

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
            content={"success": False, "detail": "服务器内部错误", "error": error_msg[:500], "path": path},
        )
    finally:
        from api.infra import _record_audit
        latency = (time.time() - start_time) * 1000
        _record_audit(method, path, client_ip, status_code, latency, error_msg)
