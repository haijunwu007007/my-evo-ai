"""Appsmith 低代码工具桥接 (35k⭐) — Apache 2.0"""
from __future__ import annotations

import os, json, time
from typing import Any
from fastapi import APIRouter
from core.logging_config import get_logger

logger = get_logger("evo.routes_appsmith")
router = APIRouter(prefix="/api/tools/appsmith", tags=["tools"])

APPSMITH_URL = os.environ.get("APPSMITH_URL", "http://127.0.0.1:8080")
APPSMITH_KEY = os.environ.get("APPSMITH_KEY", "")


def _api(method: str, path: str, data: dict | None = None) -> dict:
    import urllib.request, urllib.error
    url = f"{APPSMITH_URL}/api/v1{path}"
    headers = {"Authorization": f"Bearer {APPSMITH_KEY}"} if APPSMITH_KEY else {}
    if data:
        headers["Content-Type"] = "application/json"
    body = json.dumps(data).encode() if data else None
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("")
async def get_status():
    r = _api("GET", "/users/me") if APPSMITH_KEY else {"message": "需要配置 APPSMITH_KEY"}
    return {
        "tool": "appsmith",
        "status": "ok" if r.get("data") else "unconfigured",
        "url": APPSMITH_URL,
        "detail": r,
    }


@router.get("/health")
async def health_check():
    import urllib.request
    t0 = time.time()
    try:
        urllib.request.urlopen(f"{APPSMITH_URL}/api/v1/health", timeout=3)
        return {"healthy": True, "latency_ms": round((time.time() - t0) * 1000)}
    except Exception:
        return {"healthy": False, "error": "Appsmith not reachable"}
