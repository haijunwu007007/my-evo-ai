from __future__ import annotations
from modules._base.enterprise_module import EnterpriseModule
# -*- coding: utf-8 -*-
"""角色权限管理 — RBAC 角色+权限"""
import os, json, sqlite3, time
from typing import Optional

class RoleRBAC(EnterpriseModule):
    def __init__(self, db_path: str = ""):
        self._db = db_path or os.path.join(os.path.dirname(__file__), "..", "rbac.db")
        self._conn: Optional[sqlite3.Connection] = None
    
    def _get_db(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self._db)
            self._conn.execute("""CREATE TABLE IF NOT EXISTS roles(
                name TEXT PRIMARY KEY, permissions TEXT, desc TEXT
            )""")
            self._conn.execute("""CREATE TABLE IF NOT EXISTS users(
                username TEXT PRIMARY KEY, role TEXT, token TEXT
            )""")
        return self._conn
    
    def add_role(self, name: str, permissions: list, desc: str = ""):
        db = self._get_db()
        db.execute("INSERT OR REPLACE INTO roles VALUES(?,?,?)",
                   (name, json.dumps(permissions), desc))
        db.commit()
    
    def assign(self, username: str, role: str):
        db = self._get_db()
        db.execute("INSERT OR REPLACE INTO users(username,role,token) VALUES(?,?,?)",
                   (username, role, ""))
        db.commit()
    
    def check(self, username: str, permission: str) -> dict:
        db = self._get_db()
        row = db.execute("SELECT role FROM users WHERE username=?", (username,)).fetchone()
        if not row: return {"allowed": False, "reason": "用户不存在"}
        role = row[0]
        perms = db.execute("SELECT permissions FROM roles WHERE name=?", (role,)).fetchone()
        if not perms: return {"allowed": False, "reason": "角色不存在"}
        p_list = json.loads(perms[0])
        return {"allowed": permission in p_list or "*" in p_list, "role": role, "permission": permission}
    
    def get_roles(self) -> list:
        db = self._get_db()
        rows = db.execute("SELECT name,permissions,desc FROM roles").fetchall()
        return [{"name":r[0],"permissions":json.loads(r[1]),"desc":r[2]} for r in rows]
    
    def close(self):
        if self._conn: self._conn.close()

    def health_check(self) -> dict:
        return {"status": "healthy", "module": getattr(self, "name", self.__class__.__name__)}

    def initialize(self) -> dict:
        self._initialized = True
        return {"success": True, "module": getattr(self, "name", self.__class__.__name__)}

    def shutdown(self) -> dict:
        self._initialized = False
        return {"success": True, "module": getattr(self, "name", self.__class__.__name__)}

    async def status(self) -> dict:
        return {"name": getattr(self, "name", self.__class__.__name__), "status": "ok", "initialized": getattr(self, "_initialized", False)}

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        params = params or {}
        try:
            if action in ("status", "info", "stats"):
                return self.health_check()
            elif action == "help":
                return {"actions": ["status", "help"], "module": getattr(self, "name", self.__class__.__name__)}
            return {"success": True, "action": action, "module": getattr(self, "name", self.__class__.__name__)}
        except Exception as e:
            return {"success": False, "error": str(e)}
