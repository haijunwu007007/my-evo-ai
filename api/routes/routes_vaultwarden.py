"""Vaultwarden — 密码管理桥接 (40k⭐)"""
from fastapi import APIRouter; from api.infra import registry
router=APIRouter(); import os; URL=os.environ.get("VAULTWARDEN_URL","http://localhost:8080")
@router.get("/api/v1/tools/vaultwarden")
async def s():return {"name":"Vaultwarden","version":"latest","status":"configured","url":URL,"description":"轻量密码管理器 — Bitwarden兼容/自托管凭证库"}
@router.get("/api/v1/tools/vaultwarden/health")
async def h():
    try:import urllib.request;r=urllib.request.urlopen(URL+"/api/health",timeout=5);return{"healthy":r.status==200}
    except Exception as e:return{"healthy":False,"error":str(e)}
async def _register():registry.modules["routes_vaultwarden"]=__import__("api.routes_vaultwarden",fromlist=["routes_vaultwarden"])
