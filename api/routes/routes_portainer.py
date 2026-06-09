"""Portainer Docker 管理桥接 (32k⭐) — Zlib"""
from __future__ import annotations

import os, json, time
from typing import Any
from fastapi import APIRouter
from core.logging_config import get_logger

logger = get_logger("evo.routes_portainer")
router = APIRouter(prefix="/api/v1/tools/portainer", tags=["tools"])

PORTAINER_URL = os.environ.get("PORTAINER_URL", "http://127.0.0.1:9000")
PORTAINER_KEY = os.environ.get("PORTAINER_KEY", "")


def _api(method: str, path: str, data: dict | None = None) -> dict:
    import urllib.request, urllib.error
    url = f"{PORTAINER_URL}/api{path}"
    headers = {"X-API-Key": PORTAINER_KEY, "Content-Type": "application/json"} if PORTAINER_KEY else {}
    body = json.dumps(data).encode() if data else None
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("")
async def get_status():
    r = _api("GET", "/system/status") if PORTAINER_KEY else {"message": "需要配置 PORTAINER_KEY"}
    return {
        "tool": "portainer",
        "status": "ok" if r.get("success", True) and not r.get("error") else "unconfigured",
        "url": PORTAINER_URL,
        "detail": r,
    }


@router.get("/health")
async def health_check():
    import urllib.request
    t0 = time.time()
    try:
        urllib.request.urlopen(f"{PORTAINER_URL}/api/status", timeout=3)
        return {"healthy": True, "latency_ms": round((time.time() - t0) * 1000)}
    except Exception:
        return {"healthy": False, "error": "Portainer not reachable"}
