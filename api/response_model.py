"""统一响应格式"""
from fastapi.responses import JSONResponse

class StandardResponse:
    @staticmethod
    def ok(data="", tool="", extra=None):
        r = {"success": True, "data": data, "tool": tool}
        if extra: r.update(extra)
        return JSONResponse(content=r)
    
    @staticmethod
    def fail(error="", code=400):
        return JSONResponse(
            content={"success": False, "error": error, "status_code": code},
            status_code=code
        )
    
    @staticmethod
    def wrap(func_result, tool=""):
        if isinstance(func_result, dict):
            ok = func_result.get("ok", func_result.get("success", True))
            if ok:
                return StandardResponse.ok(func_result.get("data",""), tool)
            return StandardResponse.fail(func_result.get("data","错误"), 400)
        return StandardResponse.ok(str(func_result), tool)
