"""
AUTO-EVO-AI V0.1 — 全局入口：统一错误处理 + API响应规范化
======================================================
⚠️ 已弃用：全局异常处理已统一在 api_server.py 中实现。
   本文件保留仅用于向后兼容，不被任何代码导入。
"""
import json, logging
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("routes_entry")

def register_handlers(app):
    """注册全局异常处理器和响应中间件"""
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        msg = exc.detail
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": msg, "message": msg, "path": str(request.url.path)},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(f"未处理异常: {exc}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(exc)[:200], "message": str(exc)[:200], "path": str(request.url.path)},
        )
