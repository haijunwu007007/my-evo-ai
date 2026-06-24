"""
AUTO-EVO-AI V0.1 — MaxKB RAG知识库桥接路由
对接 MaxKB 开源知识库问答系统的 API
"""
import logging
from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger("routes_maxkb")
router = APIRouter(prefix="/api/v1/maxkb", tags=["maxkb"])

MAXKB_CONFIG = {
    "available": False,  # 需要启动 MaxKB Docker 容器
    "api_url": "http://localhost:8082",
    "version": "1.0.0",
    "note": "需要启动 MaxKB Docker 容器: docker run -d -p 8082:8082 1panel/maxkb",
}

@router.get("/status")
def maxkb_status():
    return {"success": True, **MAXKB_CONFIG, "knowledge_bases": []}

@router.post("/query")
def maxkb_query(q: str = Query("", description="查询问题")):
    if not MAXKB_CONFIG["available"]:
        return {"success": False, "error": "MaxKB 服务未启动", "help": "请先启动 MaxKB Docker 容器"}
    # 对接 MaxKB API
    import requests
    try:
        r = requests.post(f"{MAXKB_CONFIG['api_url']}/api/v1/chat", json={"question": q}, timeout=30)
        return {"success": True, "answer": r.json().get("answer", ""), "source": "maxkb"}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}

@router.get("/help")
def maxkb_help():
    return {
        "success": True,
        "install": "docker run -d -p 8082:8082 --name maxkb 1panel/maxkb",
        "docs": "https://maxkb.cn/docs/",
    }
