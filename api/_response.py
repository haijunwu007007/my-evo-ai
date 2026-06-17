"""统一API响应格式"""
from fastapi.responses import JSONResponse

def api_response(ok: bool, data=None, error=None, status_code=200):
    """统一响应格式"""
    body = {"success": ok}
    if data is not None:
        body["data"] = data
    if error:
        body["error"] = error
        body["status_code"] = status_code
    return JSONResponse(content=body, status_code=status_code)

def ok(data=None):
    return api_response(True, data=data)

def fail(error="操作失败", status_code=400):
    return api_response(False, error=error, status_code=status_code)

def not_found(msg="资源不存在"):
    return fail(msg, 404)

def unauthorized(msg="未授权"):
    return fail(msg, 401)
