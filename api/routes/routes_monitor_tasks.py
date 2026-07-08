"""任务监控面板 — 统一查看所有后台任务/定时任务/调度器状态"""
from fastapi import APIRouter
from core.logging_config import get_logger
import json, time
from pathlib import Path

logger = get_logger("evo.api.monitor_tasks")
router = APIRouter(prefix="/api/v1/monitor", tags=["monitor_tasks"])
BASE = Path(__file__).resolve().parent.parent.parent

@router.get("/tasks")
async def get_all_tasks():
    """返回所有任务状态汇总"""
    result = {
        "scheduler": {},
        "queue": {},
        "pipelines": {},
        "events": {},
        "timestamp": time.time(),
    }
    # 调度器任务
    try:
        import sqlite3
        db = BASE / "data" / "scheduler.db"
        if db.exists():
            conn = sqlite3.connect(str(db))
            conn.row_factory = sqlite3.Row
            tasks = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 20").fetchall()
            result["scheduler"] = {
                "count": len(tasks),
                "tasks": [dict(r) for r in tasks],
            }
            conn.close()
    except Exception as e:
        result["scheduler"]["error"] = str(e)

    # 队列任务
    try:
        db2 = BASE / "data" / "queue.db"
        if db2.exists():
            conn = sqlite3.connect(str(db2))
            conn.row_factory = sqlite3.Row
            tasks = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 20").fetchall()
            result["queue"] = {
                "count": len(tasks),
                "tasks": [dict(r) for r in tasks],
            }
            conn.close()
    except Exception as e:
        result["queue"]["error"] = str(e)

    # 管线
    try:
        db3 = BASE / "data" / "pipelines.db"
        if db3.exists():
            conn = sqlite3.connect(str(db3))
            conn.row_factory = sqlite3.Row
            tasks = conn.execute("SELECT * FROM pipelines ORDER BY created_at DESC LIMIT 20").fetchall()
            result["pipelines"] = {
                "count": len(tasks),
                "tasks": [dict(r) for r in tasks],
            }
            conn.close()
    except Exception as e:
        result["pipelines"]["error"] = str(e)

    return {"success": True, "data": result}

@router.get("/tasks/overview")
async def task_overview():
    """简化的总览数据（用于前端仪表盘）"""
    result = {"scheduler": 0, "queue": 0, "pipelines": 0, "events": 0, "healthy": True}
    try:
        import sqlite3
        db = BASE / "data" / "scheduler.db"
        if db.exists():
            conn = sqlite3.connect(str(db))
            result["scheduler"] = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            conn.close()
    except: pass
    try:
        db2 = BASE / "data" / "queue.db"
        if db2.exists():
            conn = sqlite3.connect(str(db2))
            result["queue"] = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            conn.close()
    except: pass
    try:
        db3 = BASE / "data" / "pipelines.db"
        if db3.exists():
            conn = sqlite3.connect(str(db3))
            result["pipelines"] = conn.execute("SELECT COUNT(*) FROM pipelines").fetchone()[0]
            conn.close()
    except: pass
    return {"success": True, "data": result}
