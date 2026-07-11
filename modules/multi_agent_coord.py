from __future__ import annotations
from modules._base.enterprise_module import EnterpriseModule
# -*- coding: utf-8 -*-
"""多Agent协作 — 角色编排+任务分配"""
import os, json, sqlite3, time
from typing import Optional

ROLES = {"planner": "规划者", "coder": "编码者", "reviewer": "审查者",
         "operator": "执行者", "analyst": "分析师", "researcher": "研究者"}

class MultiAgentCoordinator(EnterpriseModule):
    def __init__(self, db_path: str = ""):
        self._db = db_path or os.path.join(os.path.dirname(__file__), "..", "multi_agent.db")
        self._conn: Optional[sqlite3.Connection] = None
    
    def _get_db(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self._db)
            self._conn.execute("""CREATE TABLE IF NOT EXISTS teams(
                id TEXT PRIMARY KEY, name TEXT, members TEXT, created REAL
            )""")
            self._conn.execute("""CREATE TABLE IF NOT EXISTS sessions(
                id INTEGER PRIMARY KEY AUTOINCREMENT, team_id TEXT,
                task TEXT, status TEXT, result TEXT, started REAL, finished REAL
            )""")
        return self._conn
    
    def create_team(self, team_id: str, name: str, members: list) -> dict:
        db = self._get_db()
        db.execute("INSERT OR REPLACE INTO teams VALUES(?,?,?,?)",
                   (team_id, name, json.dumps(members), time.time()))
        db.commit()
        return {"team": team_id, "name": name, "members": members}
    
    def run_session(self, team_id: str, task: str) -> dict:
        db = self._get_db()
        team = db.execute("SELECT members FROM teams WHERE id=?", (team_id,)).fetchone()
        members = json.loads(team[0]) if team else ["planner","coder","reviewer"]
        db.execute("INSERT INTO sessions(team_id,task,status,started) VALUES(?,?,?,?)",
                   (team_id, task[:200], "running", time.time()))
        sid = db.lastrowid
        db.commit()
        return {"session_id": sid, "team": team_id, "members": members, "task": task, "status": "running"}
    
    def get_sessions(self, limit: int = 10) -> list:
        db = self._get_db()
        rows = db.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"id":r[0],"team":r[1],"task":r[2],"status":r[3],"result":r[4],"started":r[5],"finished":r[6]} for r in rows]
    
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
