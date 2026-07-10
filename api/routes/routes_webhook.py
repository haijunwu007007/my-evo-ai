import logging
logger = logging.getLogger("evo.routes_webhook")
# -*- coding: utf-8 -*-
"""Webhook 触发器路由"""
from fastapi import APIRouter, Request
import json, hashlib, hmac, time, os

router = APIRouter(prefix="/api/v1/webhook", tags=["webhook"])

_WEBHOOK_DB = os.path.join(os.path.dirname(__file__), "..", "data", "webhooks.json")
os.makedirs(os.path.dirname(_WEBHOOK_DB), exist_ok=True)

def _load():
    try: return json.load(open(_WEBHOOK_DB))
    except: return []

def _save(data):
    json.dump(data, open(_WEBHOOK_DB, "w"), indent=2)

@router.get("/config")
async def webhook_config():
    """获取Webhook配置"""
    try:
        data = json.load(open(_WEBHOOK_DB, encoding="utf-8"))
        return {"success": True, "webhooks": data, "total": len(data)}
    except:
        return {"success": True, "webhooks": [], "total": 0}

# @router.post("/github")
# async def github_webhook(req: Request):
#     """GitHub push webhook — 由 routes_services.py 的 modules.github_webhook 接管"""
#     pass

@router.get("/logs")
async def webhook_logs(limit: int = 20):
    return {"logs": _load()[-limit:]}
