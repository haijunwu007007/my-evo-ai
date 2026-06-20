from modules._base.enterprise_module import EnterpriseModule
# -*- coding: utf-8 -*-
"""权限沙箱 — 工具权限分级+审计日志"""
from __future__ import annotations
import os, json, sqlite3, time
from typing import Optional

PERM_LEVELS = {"safe": 0, "ask": 1, "danger": 2}

class PermissionSandbox(EnterpriseModule):
    def __init__(self, db_path: str = ""):
        self._db = db_path or os.path.join(os.path.dirname(__file__), "..", "permission.db")
        self._conn: Optional[sqlite3.Connection] = None
    
    def _get_db(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self._db)
            self._conn.execute("""CREATE TABLE IF NOT EXISTS tools(
                name TEXT PRIMARY KEY, level INT DEFAULT 1,
                desc TEXT, allowed_users TEXT
            )""")
            self._conn.execute("""CREATE TABLE IF NOT EXISTS audit(
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL,
                user TEXT, tool TEXT, action TEXT, approved INT, detail TEXT
            )""")
        return self._conn
    
    def register_tool(self, name: str, level: int = 1, desc: str = "", allowed: str = "*"):
        db = self._get_db()
        db.execute("INSERT OR REPLACE INTO tools VALUES(?,?,?,?)", (name, level, desc, allowed))
        db.commit()
    
    def check(self, user: str, tool: str) -> dict:
        db = self._get_db()
        row = db.execute("SELECT level,desc,allowed_users FROM tools WHERE name=?", (tool,)).fetchone()
        if not row: return {"allowed": True, "level": 0, "reason": "未注册工具默认放行"}
        level, desc, allowed = row
        user_allowed = allowed == "*" or user in (allowed or "").split(",")
        if not user_allowed: return {"allowed": False, "level": level, "reason": "用户无权限"}
        return {"allowed": level < 2, "level": level, "reason": "需确认" if level == 1 else "危险操作"}
    
    def log(self, user: str, tool: str, action: str, approved: int, detail: str = ""):
        db = self._get_db()
        db.execute("INSERT INTO audit(timestamp,user,tool,action,approved,detail) VALUES(?,?,?,?,?,?)",
                   (time.time(), user, tool, action, approved, detail[:200]))
        db.commit()
    
    def get_audit_log(self, limit: int = 50) -> list:
        db = self._get_db()
        rows = db.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"id":r[0],"time":r[1],"user":r[2],"tool":r[3],"action":r[4],"approved":bool(r[5]),"detail":r[6]} for r in rows]
    
    def close(self):
        if self._conn: self._conn.close()
