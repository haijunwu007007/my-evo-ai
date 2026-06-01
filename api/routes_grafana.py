"""Grafana 仪表盘桥接 (70k⭐) — AGPL v3"""
from __future__ import annotations

import os, json, time
from typing import Any
from fastapi import APIRouter
from core.logging_config import get_logger

logger = get_logger("evo.routes_grafana")
router = APIRouter(prefix="/api/tools/grafana", tags=["tools"])

GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://127.0.0.1:3000")
GRAFANA_API_KEY = os.environ.get("GRAFANA_API_KEY", "")


def _api(method: str, path: str, data: dict | None = None) -> dict:
    import urllib.request, urllib.error
    url = f"{GRAFANA_URL}/api{path}"
    headers = {"Authorization": f"Bearer {GRAFANA_API_KEY}"} if GRAFANA_API_KEY else {}
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
    r = _api("GET", "/org")
    return {
        "tool": "grafana",
        "status": "ok" if r.get("id") else "unconfigured",
        "url": GRAFANA_URL,
        "detail": r,
    }


@router.get("/health")
async def health_check():
    import urllib.request
    t0 = time.time()
    try:
        urllib.request.urlopen(f"{GRAFANA_URL}/api/health", timeout=3)
        return {"healthy": True, "latency_ms": round((time.time() - t0) * 1000)}
    except Exception:
        return {"healthy": False, "error": "Grafana not reachable"}


@router.get("/dashboards")
async def list_dashboards():
    r = _api("GET", "/search?type=dash-db&limit=50")
    return r


@router.get("/datasources")
async def list_datasources():
    r = _api("GET", "/datasources")
    return r
