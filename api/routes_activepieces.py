"""ActivePieces — 开源工作流引擎桥接"""
from fastapi import APIRouter
import os, json, urllib.request
from core.logging_config import get_logger

logger = get_logger("evo.routes_activepieces")
router = APIRouter(prefix="/api/tools/activepieces", tags=["tools"])

AP_URL = os.environ.get("ACTIVEPIECES_URL", "http://localhost:8080")
AP_API_KEY = os.environ.get("ACTIVEPIECES_API_KEY", "")


@router.get("")
async def get_status():
    return {
        "available": True,
        "url": AP_URL,
        "name": "ActivePieces",
        "description": "TypeScript 原生工作流引擎 — 拖拽式自动化、AI 集成、200+ 连接器",
    }


@router.get("/health")
async def health_check():
    try:
        req = urllib.request.Request(f"{AP_URL}/api/v1/health", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return {"healthy": True, "status": resp.status}
    except Exception as e:
        return {"healthy": False, "error": str(e)[:60]}
