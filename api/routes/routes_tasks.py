import logging
logger = logging.getLogger("evo.routes_tasks")
# -*- coding: utf-8 -*-
"""任务/看板管理路由"""
from fastapi import APIRouter
import json, os, time, hashlib

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
_DB = os.path.join(os.path.dirname(__file__), "..", "data", "tasks.json")
os.makedirs(os.path.dirname(_DB), exist_ok=True)

def _load():
    try: return json.load(open(_DB))
    except: return []

def _save(data):
    json.dump(data, open(_DB, "w"), indent=2)

@router.post("/create")
async def create_task(data: dict):
    """创建任务"""
    tasks = _load()
    tid = hashlib.md5(str(time.time()).encode()).hexdigest()[:10]
    task = {
        "id": tid,
        "title": data.get("title", ""),
        "desc": data.get("desc", ""),
        "status": data.get("status", "todo"),
        "assignee": data.get("assignee", ""),
        "created_at": time.time(),
        "depends_on": data.get("depends_on", [])
    }
    tasks.append(task)
    _save(tasks)
    return {"success": True, "id": tid}

@router.get("/board")
async def task_board():
    """获取看板所有列"""
    tasks = _load()
    board = {"todo": [], "in_progress": [], "done": [], "blocked": []}
    for t in tasks:
        s = t.get("status", "todo")
        if s not in board: s = "todo"
        board[s].append(t)
    return {"board": board, "total": len(tasks)}

@router.post("/update")
async def update_task(data: dict):
    """更新任务状态"""
    tasks = _load()
    tid = data.get("id")
    for t in tasks:
        if t["id"] == tid:
            t["status"] = data.get("status", t["status"])
            _save(tasks)
            return {"success": True}
    return {"success": False, "error": "not found"}
