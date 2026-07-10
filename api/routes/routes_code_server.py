from __future__ import annotations
"""Code-Server (Web IDE) API 桥接 — 70k⭐"""

import os
from fastapi import APIRouter
from core.logging_config import get_logger

logger = get_logger("evo.routes_code_server")
router = APIRouter(prefix="/api/v1/tools/code-server", tags=["tools"])

CODE_SERVER_BASE = os.environ.get("CODE_SERVER_BASE", "http://127.0.0.1:8443")


@router.get("")
async def code_server_status():
    healthy = False
    try:
        import urllib.request
        r = urllib.request.urlopen(f"{CODE_SERVER_BASE}/healthz", timeout=2)
        healthy = r.status == 200
    except Exception as _ex:
        logger.warning(f"[routes_code_server]" + str(_ex)[:80])
    return {
        "name": "Code-Server",
        "stars": "70k+",
        "status": "ok" if healthy else "error",
        "healthy": healthy,
        "url": CODE_SERVER_BASE,
        "description": "Web IDE — 浏览器里跑 VS Code",
    }


@router.get("/health")
async def code_server_health():
    import urllib.request
    try:
        r = urllib.request.urlopen(f"{CODE_SERVER_BASE}/healthz", timeout=2)
        return {"healthy": r.status == 200}
    except Exception as e:
        return {"healthy": False, "error": str(e)}
