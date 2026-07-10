"""Nextcloud — 企业网盘桥接 (30k⭐)"""
import logging
logger = logging.getLogger("evo.routes_nextcloud")

from fastapi import APIRouter
from api.infra import registry
router = APIRouter()
import os; NC_URL = os.environ.get("NEXTCLOUD_URL", "http://localhost:8080")
@router.get("/api/v1/tools/nextcloud")
async def nc_status():
    return {"name":"Nextcloud","version":"latest","status":"configured","url":NC_URL,"description":"自托管企业网盘 — 文件同步/共享/协作/日历/联系人"}
@router.get("/api/v1/tools/nextcloud/health")
async def nc_health():
    try:
        import urllib.request; r=urllib.request.urlopen(f"{NC_URL}/status.php",timeout=5)
        return {"healthy":r.status==200,"version":"nextcloud"}
    except Exception as e: return {"healthy":False,"error":str(e)}
async def _register():
    registry.modules["routes_nextcloud"] = __import__("api.routes_nextcloud",fromlist=["routes_nextcloud"])
