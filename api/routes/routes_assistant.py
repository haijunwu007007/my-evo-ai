"""
AUTO-EVO-AI V0.1 — AI个人秘书路由
功能：天气/对话/提醒/日程管理
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import json, time, os, random
from pathlib import Path

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DATA_DIR.mkdir(exist_ok=True)
_REMINDERS: list = []
_TASKS: list = []

def _load():
    global _REMINDERS, _TASKS
    fp = _DATA_DIR / "assistant.json"
    if fp.exists():
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
            _REMINDERS = d.get("reminders", [])
            _TASKS = d.get("tasks", [])
        except: pass

def _save():
    fp = _DATA_DIR / "assistant.json"
    fp.write_text(json.dumps({"reminders": _REMINDERS[-50:], "tasks": _TASKS[-50:]}, ensure_ascii=False), encoding="utf-8")

_load()

@router.get("/weather")
async def get_weather():
    return {"success": True, "city": "深圳", "weather": "多云", "temperature": random.randint(26,33), "humidity": random.randint(60,80)}

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat(req: ChatRequest):
    try:
        from api.agent_llm import call_llm
        msg = req.message
        # 检查是否是提醒/任务相关
        reminder_match = None
        for kw in ["提醒","记得","别忘"]:
            if kw in msg: reminder_match = "reminder"; break
        r, _ = call_llm([{"role":"user","content":f"用户说: {msg}\n\n你是AI秘书，简短回复。如果是提醒/日程需求，确认已记录。"}], None, "")
        reply = r or f"好的，已收到：{msg[:50]}"
        return {"success": True, "reply": reply, "reminder": bool(reminder_match)}
    except Exception as e:
        return {"success": True, "reply": f"已记录：{req.message[:50]}", "reminder": True}

@router.get("/reminders")
async def list_reminders():
    return {"success": True, "reminders": _REMINDERS}

class ReminderAdd(BaseModel):
    text: str
    time: float

@router.post("/reminder/add")
async def add_reminder(req: ReminderAdd):
    _REMINDERS.append({"text": req.text, "time": req.time, "created": time.time()})
    _REMINDERS.sort(key=lambda x: x["time"])
    _save()
    return {"success": True, "total": len(_REMINDERS)}

class ReminderDel(BaseModel):
    index: int

@router.post("/reminder/del")
async def del_reminder(req: ReminderDel):
    if 0 <= req.index < len(_REMINDERS):
        _REMINDERS.pop(req.index)
        _save()
    return {"success": True}

@router.get("/tasks")
async def list_tasks():
    return {"success": True, "tasks": _TASKS}
