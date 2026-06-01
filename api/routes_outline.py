"""Outline 知识库桥接 (30k⭐) — BSL"""
from __future__ import annotations

import os, json, time
from typing import Any
from fastapi import APIRouter
from core.logging_config import get_logger

logger = get_logger("evo.routes_outline")
router = APIRouter(prefix="/api/v1/tools/outline", tags=["tools"])

OUTLINE_URL = os.environ.get("OUTLINE_URL", "http://127.0.0.1:3001")
OUTLINE_API_KEY = os.environ.get("OUTLINE_API_KEY", "")


def _api(method: str, path: str, data: dict | None = None) -> dict:
    import urllib.request, urllib.error
    url = f"{OUTLINE_URL}/api{path}"
    headers = {
        "Authorization": f"Bearer {OUTLINE_API_KEY}",
        "Content-Type": "application/json",
    } if OUTLINE_API_KEY else {}
    body = json.dumps(data).encode() if data else None
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("")
async def get_status():
    r = _api("POST", "/auth.info", {}) if OUTLINE_API_KEY else {"message": "需要配置 OUTLINE_API_KEY"}
    return {
        "tool": "outline",
        "status": "ok" if r.get("data") else "unconfigured",
        "url": OUTLINE_URL,
        "detail": r,
    }


@router.get("/health")
async def health_check():
    import urllib.request
    t0 = time.time()
    try:
        urllib.request.urlopen(OUTLINE_URL, timeout=3)
        return {"healthy": True, "latency_ms": round((time.time() - t0) * 1000)}
    except Exception:
        return {"healthy": False, "error": "Outline not reachable"}
