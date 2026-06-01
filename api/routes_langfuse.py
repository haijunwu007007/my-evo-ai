"""Langfuse — LLM 可观测性与追踪集成"""
from fastapi import APIRouter
import os, json
from core.logging_config import get_logger

logger = get_logger("evo.routes_langfuse")
router = APIRouter(prefix="/api/tools/langfuse", tags=["tools"])

HAS_LANGFUSE = False
langfuse_client = None
LANGFUSE_CONFIG = {
    "public_key": os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
    "secret_key": os.environ.get("LANGFUSE_SECRET_KEY", ""),
    "base_url": os.environ.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com"),
}

try:
    from langfuse import Langfuse
    if LANGFUSE_CONFIG["public_key"] and LANGFUSE_CONFIG["secret_key"]:
        langfuse_client = Langfuse(
            public_key=LANGFUSE_CONFIG["public_key"],
            secret_key=LANGFUSE_CONFIG["secret_key"],
            base_url=LANGFUSE_CONFIG["base_url"],
        )
        HAS_LANGFUSE = True
except ImportError:
    pass


@router.get("")
async def get_status():
    return {
        "available": HAS_LANGFUSE,
        "configured": bool(LANGFUSE_CONFIG["public_key"]),
        "base_url": LANGFUSE_CONFIG["base_url"],
        "name": "Langfuse",
        "description": "LLM 可观测性 — 追踪每次 LLM 调用的耗时、token 数、成本",
    }


@router.get("/health")
async def health_check():
    if not HAS_LANGFUSE:
        return {"healthy": False, "error": "SDK not installed or not configured"}
    try:
        ok = langfuse_client.auth_check()
        return {"healthy": ok, "configured": True}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


@router.get("/traces")
async def get_traces(limit: int = 10):
    if not HAS_LANGFUSE:
        return {"traces": [], "error": "not configured"}
    return {"traces": [], "note": "通过 Langfuse 网页端查看完整追踪数据"}
