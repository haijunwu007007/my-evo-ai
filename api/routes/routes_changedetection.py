from __future__ import annotations
"""Changedetection.io (网页变更监控) API 桥接 — 20k⭐"""

import os
from fastapi import APIRouter
from core.logging_config import get_logger

logger = get_logger("evo.routes_changedetection")
router = APIRouter(prefix="/api/v1/tools/changedetection", tags=["tools"])

CD_BASE = os.environ.get("CHANGEDETECTION_BASE", "http://127.0.0.1:5000")


@router.get("")
async def changedetection_status():
    healthy = False
    version = "unknown"
    try:
        import urllib.request
        r = urllib.request.urlopen(f"{CD_BASE}/api/v1/version", timeout=2)
        if r.status == 200:
            healthy = True
            version = r.read().decode().strip()
    except Exception as _e:
            logger.warning(f"exception: {_e}")
    return {
        "name": "Changedetection.io",
        "stars": "20k+",
        "status": "ok" if healthy else "error",
        "healthy": healthy,
        "url": CD_BASE,
        "version": version,
        "description": "网页变更监控 — 与 GitHub Trending 互补",
    }


@router.get("/health")
async def changedetection_health():
    import urllib.request
    try:
        r = urllib.request.urlopen(f"{CD_BASE}/api/v1/version", timeout=2)
        return {"healthy": r.status == 200}
    except Exception as e:
        return {"healthy": False, "error": str(e)}
