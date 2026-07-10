"""NocoDB (数据库管理) API 桥接 — 55k⭐"""
from __future__ import annotations

import os
from fastapi import APIRouter
from core.logging_config import get_logger

logger = get_logger("evo.routes_nocodb")
router = APIRouter(prefix="/api/v1/tools/nocodb", tags=["tools"])

NOCODB_BASE = os.environ.get("NOCODB_BASE", "http://127.0.0.1:8088")


@router.get("")
async def nocodb_status():
    healthy = False
    try:
        import urllib.request
        r = urllib.request.urlopen(f"{NOCODB_BASE}/api/v1/health", timeout=2)
        healthy = r.status == 200
    except Exception as _e:
            logger.warning(f"exception: {_e}")
    return {
        "name": "NocoDB",
        "stars": "55k+",
        "status": "ok" if healthy else "error",
        "healthy": healthy,
        "url": NOCODB_BASE,
        "description": "数据库管理 — SQLite/MySQL 转电子表格",
    }


@router.get("/health")
async def nocodb_health():
    import urllib.request
    try:
        r = urllib.request.urlopen(f"{NOCODB_BASE}/api/v1/health", timeout=2)
        return {"healthy": r.status == 200}
    except Exception as e:
        return {"healthy": False, "error": str(e)}
