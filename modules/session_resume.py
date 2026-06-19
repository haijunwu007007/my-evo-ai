"""
Grade: A
AUTO-EVO-AI V0.1 — 会话Resume恢复
持久化会话到SQLite，支持服务重启/断线后恢复，保留上下文+审批历史
"""
from __future__ import annotations

__module_meta__ = {
    "id": "session-resume",
    "name": "会话恢复引擎",
    "version": "V0.1",
    "group": "system",
    "grade": "A",
    "description": "持久化会话到SQLite，支持服务重启/断线后恢复",
    "tags": ["session", "resume", "persist"],
}

import json, time, sqlite3, threading, uuid
from pathlib import Path
from datetime import datetime
from typing import Optional
from modules._base import Result
from modules._base.enterprise_module import EnterpriseModule


class SessionResume:
    """会话恢复引擎"""

    def __init__(self):
        self._db_path = Path(__file__).parent.parent / ".evo_data" / "sessions.db"
        self._active_session_id: Optional[str] = None
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    label TEXT,
                    created_at REAL,
                    updated_at REAL,
                    message_count INTEGER DEFAULT 0,
                    context_summary TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'active'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp REAL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    action_type TEXT,
                    action_data TEXT,
                    timestamp REAL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
            """)
            conn.commit()
            conn.close()

    def create_session(self, label: str = "新会话", context_summary: str = "") -> str:
        sid = f"sess_{uuid.uuid4().hex[:12]}"
        now = time.time()
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute(
                "INSERT INTO sessions (id, label, created_at, updated_at, context_summary) VALUES (?, ?, ?, ?, ?)",
                (sid, label[:100], now, now, context_summary[:500]),
            )
            conn.commit()
            conn.close()
        self._active_session_id = sid
        return sid

    def set_active(self, session_id: str) -> bool:
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            row = conn.execute("SELECT id FROM sessions WHERE id=?", (session_id,)).fetchone()
            conn.close()
            if row:
                self._active_session_id = session_id
                return True
            return False

    def get_active(self) -> Optional[str]:
        return self._active_session_id

    def add_message(self, role: str, content: str, session_id: Optional[str] = None):
        sid = session_id or self._active_session_id
        if not sid:
            sid = self.create_session()

        now = time.time()
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute(
                "INSERT INTO session_messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (sid, role, content[:10000], now),
            )
            conn.execute(
                "UPDATE sessions SET updated_at=?, message_count=message_count+1 WHERE id=?",
                (now, sid),
            )
            conn.commit()
            conn.close()

    def add_action(self, action_type: str, action_data: dict, session_id: Optional[str] = None):
        sid = session_id or self._active_session_id
        if not sid:
            return
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute(
                "INSERT INTO session_actions (session_id, action_type, action_data, timestamp) VALUES (?, ?, ?, ?)",
                (sid, action_type[:50], json.dumps(action_data, ensure_ascii=False)[:5000], time.time()),
            )
            conn.commit()
            conn.close()

    def get_messages(self, session_id: Optional[str] = None, limit: int = 200) -> list[dict]:
        sid = session_id or self._active_session_id
        if not sid:
            return []
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            rows = conn.execute(
                "SELECT role, content, timestamp FROM session_messages WHERE session_id=? ORDER BY id ASC LIMIT ?",
                (sid, limit),
            ).fetchall()
            conn.close()
            return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows]

    def get_recent_sessions(self, limit: int = 20) -> list[dict]:
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            rows = conn.execute(
                "SELECT id, label, created_at, updated_at, message_count, status FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            conn.close()
            return [
                {"id": r[0], "label": r[1], "created_at": r[2], "updated_at": r[3],
                 "message_count": r[4], "status": r[5]}
                for r in rows
            ]

    def delete_session(self, session_id: str):
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute("DELETE FROM session_messages WHERE session_id=?", (session_id,))
            conn.execute("DELETE FROM session_actions WHERE session_id=?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
            conn.commit()
            conn.close()
            if self._active_session_id == session_id:
                self._active_session_id = None

    def get_session_info(self, session_id: str) -> Optional[dict]:
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            row = conn.execute(
                "SELECT id, label, created_at, updated_at, message_count, context_summary, status FROM sessions WHERE id=?",
                (session_id,),
            ).fetchone()
            conn.close()
            if not row:
                return None
            return {
                "id": row[0], "label": row[1], "created_at": row[2],
                "updated_at": row[3], "message_count": row[4],
                "context_summary": row[5], "status": row[6],
            }


_session_resume = SessionResume()


def get_session_resume() -> SessionResume:
    return _session_resume


class SessionResumeModule(EnterpriseModule):
    def __init__(self):
        super().__init__(module_id="session-resume", name="会话恢复引擎")

    async def initialize(self):
        self._status = "ready"
        return Result(success=True, message="Session Resume 就绪")

    async def execute(self, action: str, **params) -> Result:
        sr = get_session_resume()
        try:
            if action == "create":
                sid = sr.create_session(params.get("label", "新会话"), params.get("summary", ""))
                return Result(success=True, data={"session_id": sid})
            elif action == "list":
                return Result(success=True, data={"sessions": sr.get_recent_sessions()})
            elif action == "messages":
                msgs = sr.get_messages(params.get("session_id"))
                return Result(success=True, data={"messages": msgs, "count": len(msgs)})
            elif action == "resume":
                sid = params.get("session_id", "")
                ok = sr.set_active(sid)
                if ok:
                    info = sr.get_session_info(sid)
                    return Result(success=True, data=info or {"session_id": sid})
                return Result(success=False, error="会话不存在")
            elif action == "info":
                info = sr.get_session_info(params.get("session_id", ""))
                return Result(success=True, data=(info or {}))
            elif action == "delete":
                sr.delete_session(params.get("session_id", ""))
                return Result(success=True, data={"deleted": True})
            return Result(success=False, error=f"未知动作: {action}")
        except Exception as e:
            return Result(success=False, error=str(e))

    async def health_check(self):
        return Result(success=True, data={"status": self._status})
