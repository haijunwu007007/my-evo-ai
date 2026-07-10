"""Plane — 项目管理桥接 (30k⭐)"""
import logging
logger = logging.getLogger("evo.routes_plane")

from fastapi import APIRouter; from api.infra import registry
router=APIRouter(); import os; URL=os.environ.get("PLANE_URL","http://localhost:8080")
@router.get("/api/v1/tools/plane")
async def s():return {"name":"Plane","version":"latest","status":"configured","url":URL,"description":"开源项目管理 — Issue/Kanban/Sprint/文档 (Jira替代)"}
@router.get("/api/v1/tools/plane/health")
async def h():
    try:import urllib.request;r=urllib.request.urlopen(URL+"/api/v1/health",timeout=5);return{"healthy":r.status==200}
    except Exception as e:return{"healthy":False,"error":str(e)}
async def _register():registry.modules["routes_plane"]=__import__("api.routes_plane",fromlist=["routes_plane"])
