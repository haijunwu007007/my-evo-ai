"""AUTO-EVO-AI V0.1 — OpenClaw (373k⭐) AI网关桥接"""
from fastapi import APIRouter
import urllib.request, json as _json
router = APIRouter()
B = "/api/tools/openclaw"
HOST = "http://127.0.0.1:3002"

def _alive():
    try:
        r = urllib.request.urlopen(f"{HOST}/health", timeout=2)
        return r.status == 200
    except Exception:
        try:
            r = urllib.request.urlopen(HOST, timeout=2)
            return r.status == 200
        except Exception:
            return False

@router.get(B)
async def oc_status():
    ok = _alive()
    return {"success": True, "available": ok, "url": HOST, "name": "OpenClaw (373k⭐) AI助手网关"}

@router.get(B + "/channels")
async def oc_channels():
    return {"success": True, "available": _alive(), "channels": ["telegram","discord","whatsapp","slack","web"]}
