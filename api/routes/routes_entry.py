"""
AUTO-EVO-AI V0.1 — 全局入口：统一错误处理 + API响应规范化
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

    @app.middleware("http")
    async def normalize_api_response(request: Request, call_next):
        """统一响应格式：所有包含detail的自动补充message字段"""
        import time
        start = time.time()
        response = await call_next(request)
        # 只处理JSON响应
        ct = response.headers.get("content-type", "")
        if "json" in ct and request.url.path.startswith("/api/"):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            try:
                data = json.loads(body)
                if isinstance(data, dict):
                    if "detail" in data and "message" not in data:
                        data["message"] = data["detail"]
                    data["_t"] = round(time.time() - start, 3)
                return JSONResponse(status_code=response.status_code, content=data)
            except Exception:
                pass
        return response
