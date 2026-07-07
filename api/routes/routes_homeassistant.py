"""Home Assistant — 智能家居桥接 (80k⭐)"""
from fastapi import APIRouter; from api.infra import registry
import os; router=APIRouter(); URL=os.environ.get("HOMEASSISTANT_URL","http://localhost:8123")
@router.get("/api/v1/tools/homeassistant")
async def s():return {"name":"Home Assistant","version":"latest","status":"configured","url":URL,"description":"开源智能家居平台 — IoT设备控制/自动化场景/传感器监控"}
@router.get("/api/v1/tools/homeassistant/health")
async def h():
    try:import urllib.request;r=urllib.request.urlopen(URL+"/api/",timeout=5);return{"healthy":r.status==200}
    except Exception as e:return{"healthy":False,"error":str(e)}
async def _register():registry.modules["routes_homeassistant"]=__import__("api.routes_homeassistant",fromlist=["routes_homeassistant"])
