"""AUTO-EVO-AI V0.1 — OpenClaw (373k⭐) AI助手网关 桥接路由"""
from fastapi import APIRouter
import os, json, urllib.request
router = APIRouter()
B = "/api/tools/openclaw"

OC_URL = os.environ.get("OPENCLAW_URL", "http://localhost:3002")

@router.get(B)
async def status():
    try:
        r = urllib.request.urlopen(f"{OC_URL}/health", timeout=5)
        return {"success": True, "available": True, "url": OC_URL, "name": "OpenClaw (373k⭐) AI助手网关", "stars": "373k"}
    except Exception:
        return {"success": True, "available": False, "url": OC_URL, "name": "OpenClaw (373k⭐) AI助手网关", "note": "需要先启动 OpenClaw 服务"}

@router.get(B + "/channels")
async def channels():
    try:
        r = urllib.request.urlopen(f"{OC_URL}/api/channels", timeout=5)
        return json.loads(r.read().decode())
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post(B + "/message")
async def send_message():
    return {"success": True, "note": "OpenClaw handles its own messaging. Integrate by pointing OpenClaw to this EVO server's API."}
