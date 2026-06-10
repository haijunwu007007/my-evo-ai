"""
AUTO-EVO-AI V0.1 — 自愈/自进化引擎
提供 /api/v1/selfheal/* 端点，用于错误记录 + 修复建议
"""
from fastapi import APIRouter, Request
from typing import Optional
from pathlib import Path
import time, json, sqlite3

router = APIRouter()
BASE = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE / "data" / "selfheal.db"


def _get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS selfheal_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "error_type TEXT, module_name TEXT, message TEXT,"
        "fix_suggestion TEXT, created_at REAL, fixed INTEGER DEFAULT 0)"
    )
    return conn


@router.get("/api/v1/selfheal/log")
async def get_selfheal_log(limit: int = 50):
    """获取自愈日志"""
    try:
        conn = _get_db()
        rows = conn.execute(
            "SELECT id, error_type, module_name, message, fix_suggestion, created_at, fixed "
            "FROM selfheal_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        logs = []
        for r in rows:
            logs.append({
                "id": r[0], "error_type": r[1], "module_name": r[2],
                "message": r[3], "fix_suggestion": r[4],
                "created_at": r[5], "fixed": bool(r[6])
            })
        return {"success": True, "logs": logs, "count": len(logs)}
    except Exception as e:
        return {"success": True, "logs": [], "count": 0, "error": str(e)}


@router.post("/api/v1/selfheal/report")
async def report_error(req: Request):
    """报告错误（供各模块调用）"""
    try:
        body = await req.json()
        conn = _get_db()
        conn.execute(
            "INSERT INTO selfheal_log (error_type, module_name, message, fix_suggestion, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (body.get("error_type", "unknown"), body.get("module_name", ""),
             body.get("message", ""), body.get("fix_suggestion", ""), time.time())
        )
        conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/api/v1/selfheal/report")
async def get_selfheal_report():
    """获取自愈修复报告"""
    try:
        conn = _get_db()
        total = conn.execute("SELECT COUNT(*) FROM selfheal_log").fetchone()[0]
        fixed = conn.execute("SELECT COUNT(*) FROM selfheal_log WHERE fixed=1").fetchone()[0]
        by_type = conn.execute(
            "SELECT error_type, COUNT(*) FROM selfheal_log GROUP BY error_type ORDER BY COUNT(*) DESC"
        ).fetchall()
        return {
            "success": True,
            "total": total,
            "fixed": fixed,
            "auto_heal_rate": f"{fixed / max(total, 1) * 100:.1f}%",
            "by_type": {r[0]: r[1] for r in by_type}
        }
    except Exception as e:
        return {"success": True, "total": 0, "fixed": 0, "auto_heal_rate": "0%", "error": str(e)}


def register_routes(app):
    """兼容性入口"""
    app.include_router(router)


setup_selfheal_routes = register_routes
