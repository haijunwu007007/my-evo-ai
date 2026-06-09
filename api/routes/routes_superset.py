"""Apache Superset — 数据可视化平台桥接"""
from fastapi import APIRouter
import os, json, urllib.request
from core.logging_config import get_logger

logger = get_logger("evo.routes_superset")
router = APIRouter(prefix="/api/v1/tools/superset", tags=["tools"])

SUPERSET_URL = os.environ.get("SUPERSET_URL", "http://localhost:8088")


@router.get("")
async def get_status():
    return {
        "available": True,
        "url": SUPERSET_URL,
        "name": "Apache Superset",
        "description": "企业级数据可视化平台 — 拖拽式图表、Dashboard、SQL 查询",
    }


@router.get("/health")
async def health_check():
    try:
        req = urllib.request.Request(f"{SUPERSET_URL}/api/v1/health", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return {"healthy": True, "status": resp.status}
    except Exception as e:
        return {"healthy": False, "error": str(e)[:60]}
