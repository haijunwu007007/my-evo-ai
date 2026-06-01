"""AUTO-EVO-AI V0.1 — Uptime Kuma 监控桥接路由 (增强版)"""
from fastapi import APIRouter
import urllib.request, json as _json, os
from core.logging_config import get_logger

logger = get_logger("evo.routes_uptime_kuma")
router = APIRouter()
BASE = "/api/tools/uptime"

UPTIME_HOST = os.environ.get("UPTIME_HOST", "http://127.0.0.1:3001")


def _kuma_api(method: str, path: str, timeout: int = 5) -> dict:
    """调用 Uptime Kuma API"""
    url = f"{UPTIME_HOST}/api{path}"
    try:
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return _json.loads(resp.read())
    except Exception as e:
        logger.debug(f"Kuma API call failed: {url} {e}")
        return {"success": False, "error": str(e)[:120]}


@router.get(BASE)
async def uptime_status():
    """Uptime Kuma 整体状态"""
    result = _kuma_api("GET", "/status")
    return {
        "success": True,
        "available": result.get("success", False),
        "host": UPTIME_HOST,
        "detail": result if result.get("success") else {"status": "unreachable"},
    }


@router.get(f"{BASE}/monitors")
async def uptime_monitors():
    """获取监控项列表"""
    data = _kuma_api("GET", "/monitors")
    monitors = data if isinstance(data, list) else data.get("monitors", []) if isinstance(data, dict) else []
    return {"success": True, "monitors": monitors, "count": len(monitors)}


@router.get(f"{BASE}/health")
async def uptime_health():
    """健康检查"""
    result = _kuma_api("GET", "/status")
    ok = result.get("success", False)
    return {"success": True, "healthy": ok, "host": UPTIME_HOST}
