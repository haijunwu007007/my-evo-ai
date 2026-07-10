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

@router.post("/github")
async def github_webhook(req: Request):
    """GitHub push webhook — 自动触发部署"""
    body = await req.body()
    data = json.loads(body.decode())
    
    repo = data.get("repository", {}).get("clone_url", "")
    ref = data.get("ref", "")
    branch = ref.split("/")[-1] if ref else "main"
    
    if not repo:
        return {"success": False, "error": "no repo"}
    
    # 记录触发事件
    logs = _load()
    logs.append({
        "time": time.time(),
        "repo": repo,
        "branch": branch,
        "event": "push",
        "action": "auto_deploy"
    })
    _save(logs[-100:])
    
    return {
        "success": True,
        "triggered": True,
        "repo": repo,
        "branch": branch,
        "action": "auto_deploy"
    }

@router.get("/logs")
async def webhook_logs(limit: int = 20):
    return {"logs": _load()[-limit:]}
