"""Ntfy (推送通知) API 桥接 — 30k⭐"""
from __future__ import annotations

import os, json
from fastapi import APIRouter
from core.logging_config import get_logger

logger = get_logger("evo.routes_ntfy")
router = APIRouter(prefix="/api/v1/tools/ntfy", tags=["tools"])

NTFY_BASE = os.environ.get("NTFY_BASE", "http://127.0.0.1:8086")


@router.get("")
async def ntfy_status():
    healthy = False
    try:
        import urllib.request
        r = urllib.request.urlopen(f"{NTFY_BASE}/v1/health", timeout=2)
        healthy = r.status == 200
    except Exception as _e:
            logger.warning(f"exception: {_e}")
    return {
        "name": "Ntfy",
        "stars": "30k+",
        "status": "ok" if healthy else "error",
        "healthy": healthy,
        "url": NTFY_BASE,
        "description": "推送通知 — 手机/桌面推送",
    }


@router.get("/health")
async def ntfy_health():
    import urllib.request
    try:
        r = urllib.request.urlopen(f"{NTFY_BASE}/v1/health", timeout=2)
        return {"healthy": r.status == 200}
    except Exception as e:
        return {"healthy": False, "error": str(e)}
