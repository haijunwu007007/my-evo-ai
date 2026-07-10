"""
AUTO-EVO-AI V0.1 — Agent 团队管理
提供 Agent 团队创建、状态查询、协作消息接口
"""
import logging
logger = logging.getLogger("evo.routes_agent_team")

from fastapi import APIRouter, Request
from typing import Optional
from pathlib import Path
import time, json, sqlite3, uuid

router = APIRouter()
BASE = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE / "data" / "agent_team.db"


def _get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS teams ("
        "id TEXT PRIMARY KEY, name TEXT, description TEXT,"
        "members TEXT, status TEXT, created_at REAL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS team_messages ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, team_id TEXT,"
        "sender TEXT, content TEXT, msg_type TEXT, created_at REAL)"
    )
    return conn


@router.get("/api/v1/agent/team")
async def list_teams():
    """列出所有 Agent 团队"""
    try:
        conn = _get_db()
        rows = conn.execute("SELECT id, name, description, members, status, created_at FROM teams ORDER BY created_at DESC").fetchall()
        teams = []
        for r in rows:
            teams.append({
                "id": r[0], "name": r[1], "description": r[2],
                "members": json.loads(r[3]) if r[3] else [],
                "status": r[4], "created_at": r[5]
            })
        return {"success": True, "teams": teams, "total": len(teams)}
    except Exception as e:
        return {"success": True, "teams": [], "total": 0, "error": str(e)}


@router.post("/api/v1/agent/team/create")
async def create_team(req: Request):
    """创建新 Agent 团队"""
    try:
        body = await req.json()
        conn = _get_db()
        team_id = str(uuid.uuid4())[:8]
        conn.execute(
            "INSERT INTO teams (id, name, description, members, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (team_id, body.get("name", "未命名团队"), body.get("description", ""),
             json.dumps(body.get("members", [])), "idle", time.time())
        )
        conn.commit()
        return {"success": True, "team_id": team_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/api/v1/agent/team/{team_id}")
async def get_team(team_id: str):
    """获取团队详情"""
    try:
        conn = _get_db()
        r = conn.execute("SELECT id, name, description, members, status, created_at FROM teams WHERE id=?", (team_id,)).fetchone()
        if not r:
            return {"success": False, "error": "team_not_found"}
        messages = conn.execute(
            "SELECT sender, content, msg_type, created_at FROM team_messages WHERE team_id=? ORDER BY id ASC", (team_id,)
        ).fetchall()
        return {
            "success": True,
            "team": {
                "id": r[0], "name": r[1], "description": r[2],
                "members": json.loads(r[3]) if r[3] else [],
                "status": r[4], "created_at": r[5]
            },
            "messages": [{"sender": m[0], "content": m[1], "msg_type": m[2], "created_at": m[3]} for m in messages]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/v1/agent/team/{team_id}/message")
async def send_message(team_id: str, req: Request):
    """向团队发送消息"""
    try:
        body = await req.json()
        conn = _get_db()
        conn.execute(
            "INSERT INTO team_messages (team_id, sender, content, msg_type, created_at) VALUES (?, ?, ?, ?, ?)",
            (team_id, body.get("sender", "user"), body.get("content", ""), body.get("msg_type", "text"), time.time())
        )
        conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def register_routes(app):
    """兼容性入口"""
    app.include_router(router)


setup_agent_team_routes = register_routes
