"""Metabase — 数据分析桥接 (45k⭐)"""
import logging
logger = logging.getLogger("evo.routes_metabase")

from fastapi import APIRouter
from api.infra import registry
router = APIRouter()
URL = "http://localhost:3000"
@router.get("/api/v1/tools/metabase")
async def tool_status():
    return {"name":"Metabase","version":"latest","status":"configured","url":URL,"description":"轻量级 BI 分析工具 — SQL 查询/可视化图表/Dashboard"}
@router.get("/api/v1/tools/metabase/health")
async def tool_health():
    try:
        import urllib.request; r=urllib.request.urlopen(URL+"/api/health",timeout=5)
        return {"healthy":r.status==200}
    except Exception as e: return {"healthy":False,"error":str(e)}
async def _register():
    registry.modules["routes_metabase"]=__import__("api.routes_metabase",fromlist=["routes_metabase"])
