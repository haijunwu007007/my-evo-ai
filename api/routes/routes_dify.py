"""AUTO-EVO-AI V0.1 — Dify LLM应用平台 桥接路由"""
import logging
logger = logging.getLogger("evo.routes_dify")

from fastapi import APIRouter
router = APIRouter()
B = "/api/v1/tools/dify"

_mod = None
def _get_mod():
    global _mod
    if _mod is None:
        try:
            from modules.dify import module_class
            _mod = module_class()
            _mod.initialize()
        except Exception as e:
            return None
    return _mod

@router.get(B)
async def dify_status():
    m = _get_mod()
    _dify_url = os.environ.get("DIFY_URL", "http://localhost:3000")
    return {"success": True, "available": m is not None, "name": "Dify LLM平台", "url": _dify_url, "doc": "https://docs.dify.ai"}

@router.get(B + "/health")
async def dify_health():
    m = _get_mod()
    if not m:
        return {"success": False, "error": "模块不可用"}
    try:
        return m.health_check() if hasattr(m, 'health_check') else {"status": "healthy"}
    except Exception as e:
        logger.error("[Dify] health 异常: %s", e)
        return {"success": False, "error": f"health 异常: {e}"}

@router.post(B + "/execute")
async def dify_execute():
    m = _get_mod()
    if not m:
        return {"success": False, "error": "模块不可用"}
    try:
        return m.execute(action="execute", params={"action": "status"})
    except Exception as e:
        logger.error("[Dify] execute 异常: %s", e)
        return {"success": False, "error": f"execute 异常: {e}"}
