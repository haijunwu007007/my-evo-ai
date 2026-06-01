"""Tabby (30k⭐) — 自托管 AI 代码助手桥接"""
from fastapi import APIRouter
import os, json, urllib.request
from core.logging_config import get_logger

logger = get_logger("evo.routes_tabby")
router = APIRouter(prefix="/api/v1/tools/tabby", tags=["tools"])

TABBY_URL = os.environ.get("TABBY_URL", "http://localhost:8089")


@router.get("")
async def get_status():
    return {
        "available": True,
        "url": TABBY_URL,
        "name": "Tabby",
        "description": "自托管 AI 代码助手 (30k⭐) — 代码补全、内联建议、多模型支持",
    }


@router.get("/health")
async def health_check():
    try:
        req = urllib.request.Request(f"{TABBY_URL}/v1/health", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return {"healthy": True, "status": resp.status}
    except Exception as e:
        return {"healthy": False, "error": str(e)[:60]}


@router.get("/models")
async def list_models():
    try:
        req = urllib.request.Request(f"{TABBY_URL}/v1/models", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)[:60]}
