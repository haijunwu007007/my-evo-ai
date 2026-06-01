"""MinIO S3 对象存储桥接 (55k⭐) — AGPL v3"""
from __future__ import annotations

import os, json, time
from typing import Any
from fastapi import APIRouter, HTTPException
from core.logging_config import get_logger
from api._paths import BASE_DIR

logger = get_logger("evo.routes_minio")
router = APIRouter(prefix="/api/tools/minio", tags=["tools"])

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://127.0.0.1:9000")
MINIO_CONSOLE = os.environ.get("MINIO_CONSOLE", "http://127.0.0.1:9001")
MINIO_ROOT_USER = os.environ.get("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "evo-data")


def _minio_admin_api(method: str, path: str, data: dict | None = None) -> dict:
    import urllib.request, urllib.error, base64
    url = f"{MINIO_CONSOLE}/api/v1{path}"
    auth = base64.b64encode(f"{MINIO_ROOT_USER}:{MINIO_ROOT_PASSWORD}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("")
async def get_status():
    r = _minio_admin_api("GET", "/system/status")
    return {
        "tool": "minio",
        "status": "ok" if r.get("success", True) else "error",
        "endpoint": MINIO_ENDPOINT,
        "console": MINIO_CONSOLE,
        "default_bucket": MINIO_BUCKET,
        "detail": r,
    }


@router.get("/buckets")
async def list_buckets():
    r = _minio_admin_api("GET", "/buckets")
    return r


@router.get("/health")
async def health_check():
    import urllib.request
    t0 = time.time()
    try:
        urllib.request.urlopen(f"{MINIO_ENDPOINT}/minio/health/live", timeout=3)
        return {"healthy": True, "latency_ms": round((time.time() - t0) * 1000)}
    except Exception as e:
        return {"healthy": False, "error": str(e)}
