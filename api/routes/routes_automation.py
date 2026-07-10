from __future__ import annotations
# -*- coding: utf-8 -*-
"""
🤖 自动化 CRUD 路由 — 定时任务/Webhook/条件触发管理
"""
import json, time, os, uuid, asyncio
from pathlib import Path
from core.logging_config import get_logger
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/automations", tags=["automations"])
BASE = Path(os.environ.get("EVO_DATA_DIR", "data")) / "automations"
BASE.mkdir(parents=True, exist_ok=True)


class AutomationModel(BaseModel):
    name: str
    trigger: str = "cron"         # cron / webhook / file_change
    schedule: str = ""            # cron 表达式
    webhook_url: str = ""         # Webhook 触发地址
    action: str = ""              # 执行操作（命令/API路径）
    enabled: bool = True


def _load_all() -> dict:
    autos = {}
    for f in BASE.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["id"] = f.stem
            autos[f.stem] = data
        except Exception: logger.warning("[Automation] 解析失败")
    return autos

def _save_one(aid: str, data: dict):
    fp = BASE / f"{aid}.json"
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("")
async def list_automations():
    """列出所有自动化"""
    autos = _load_all()
    return {"success": True, "automations": list(autos.values()), "total": len(autos)}

@router.get("/{aid}")
async def get_automation(aid: str):
    autos = _load_all()
    if aid not in autos:
        return {"success": False, "error": "不存在"}
    return {"success": True, "automation": autos[aid]}

@router.post("")
async def create_automation(m: AutomationModel):
    aid = uuid.uuid4().hex[:12]
    data = m.model_dump()
    data["created_at"] = time.time()
    data["updated_at"] = data["created_at"]
    data["run_count"] = 0
    _save_one(aid, data)
    return {"success": True, "id": aid, "automation": data}

@router.put("/{aid}")
async def update_automation(aid: str, m: AutomationModel):
    autos = _load_all()
    if aid not in autos:
        return {"success": False, "error": "不存在"}
    data = m.model_dump()
    data["id"] = aid
    data["created_at"] = autos[aid].get("created_at", time.time())
    data["updated_at"] = time.time()
    data["run_count"] = autos[aid].get("run_count", 0)
    _save_one(aid, data)
    return {"success": True, "automation": data}

@router.delete("/{aid}")
async def delete_automation(aid: str):
    fp = BASE / f"{aid}.json"
    if fp.exists():
        fp.unlink()
    return {"success": True}

@router.post("/{aid}/toggle")
async def toggle_automation(aid: str):
    autos = _load_all()
    if aid not in autos:
        return {"success": False, "error": "不存在"}
    autos[aid]["enabled"] = not autos[aid].get("enabled", True)
    autos[aid]["updated_at"] = time.time()
    _save_one(aid, autos[aid])
    return {"success": True, "enabled": autos[aid]["enabled"]}

@router.post("/{aid}/run")
async def run_automation(aid: str):
    autos = _load_all()
    if aid not in autos:
        return {"success": False, "error": "不存在"}
    a = autos[aid]
    a["run_count"] = a.get("run_count", 0) + 1
    a["last_run"] = time.time()
    _save_one(aid, a)
    # 执行动作
    result = f"执行: {a.get('action', '')}"
    return {"success": True, "result": result, "run_count": a["run_count"]}

@router.post("/webhook/{aid}")
async def webhook_trigger(aid: str, data: dict = {}):
    """Webhook 入口 — 外部系统 POST 到 /api/v1/automations/webhook/{aid} 触发"""
    autos = _load_all()
    if aid not in autos:
        return {"success": False, "error": "不存在"}
    a = autos[aid]
    a["run_count"] = a.get("run_count", 0) + 1
    a["last_run"] = time.time()
    a["last_webhook"] = data
    _save_one(aid, a)
    return {"success": True, "triggered": True, "action": a.get("action", "")}

@router.get("/stats")
async def automation_stats():
    autos = _load_all()
    total = len(autos)
    enabled = sum(1 for a in autos.values() if a.get("enabled"))
    total_runs = sum(a.get("run_count", 0) for a in autos.values())
    return {"success": True, "stats": {"total": total, "enabled": enabled, "total_runs": total_runs}}
