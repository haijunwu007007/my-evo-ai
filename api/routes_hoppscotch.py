"""Hoppscotch (66k⭐) — 开源 API 测试工具"""  # noqa: E501
from fastapi import APIRouter
import os, urllib.request
from core.logging_config import get_logger

logger = get_logger("evo.routes_hoppscotch")
router = APIRouter(prefix="/api/tools/hoppscotch", tags=["tools"])

HOPSCOTCH_URL = os.environ.get("HOPSCOTCH_URL", "http://localhost:3010")


@router.get("")
async def get_status():
    return {
        "available": True,
        "url": HOPSCOTCH_URL,
        "name": "Hoppscotch",
        "description": "开源 API 测试工具 (66k⭐) — Postman 替代品，支持 HTTP/GraphQL/WebSocket",
    }


@router.get("/health")
async def health_check():
    try:
        req = urllib.request.Request(f"{HOPSCOTCH_URL}/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return {"healthy": True, "status": resp.status}
    except Exception as e:
        return {"healthy": False, "error": str(e)[:60]}
