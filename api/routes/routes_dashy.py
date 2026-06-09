"""Dashy (统一启动页) API 桥接 — 17k⭐"""
from __future__ import annotations

import os
from fastapi import APIRouter
from core.logging_config import get_logger

logger = get_logger("evo.routes_dashy")
router = APIRouter(prefix="/api/v1/tools/dashy", tags=["tools"])

DASHY_BASE = os.environ.get("DASHY_BASE", "http://127.0.0.1:4000")


@router.get("")
async def dashy_status():
    healthy = False
    try:
        import urllib.request
        r = urllib.request.urlopen(f"{DASHY_BASE}/api/health", timeout=2)
        healthy = r.status == 200
    except Exception:
        pass
    return {
        "name": "Dashy",
        "stars": "17k+",
        "status": "ok" if healthy else "error",
        "healthy": healthy,
        "url": DASHY_BASE,
        "description": "统一启动页 — 30 个工具一站式入口",
    }


@router.get("/health")
async def dashy_health():
    import urllib.request
    try:
        r = urllib.request.urlopen(f"{DASHY_BASE}/api/health", timeout=2)
        return {"healthy": r.status == 200}
    except Exception as e:
        return {"healthy": False, "error": str(e)}
