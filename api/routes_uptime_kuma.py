"""AUTO-EVO-AI V0.1 — Uptime Kuma 监控桥接路由"""
from fastapi import APIRouter
import urllib.request, json as _json

router = APIRouter()
B = "/api/tools/uptime"

UPTIME_HOST = "http://127.0.0.1:3001"

@router.get(B)
async def uptime_status():
    try:
        r = urllib.request.urlopen(f"{UPTIME_HOST}/api/status", timeout=5)
        return {"success": True, "available": True, "host": UPTIME_HOST}
    except Exception as e:
        return {"success": True, "available": False, "host": UPTIME_HOST, "error": str(e)[:100]}
