import logging
logger = logging.getLogger("evo.routes_audit")
# -*- coding: utf-8 -*-
"""📋 审计日志系统"""
import os, json, time, sqlite3
from fastapi import APIRouter
from pathlib import Path

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])
BASE = Path(__file__).resolve().parent.parent.parent
DB = BASE / "data" / "audit.db"
# index.html is frontend
AUDITS_DIR = BASE / "data" / "audit_files"
AUDITS_DIR.mkdir(parents=True, exist_ok=True)

def _init():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB))
    conn.execute("CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, action TEXT, user TEXT, detail TEXT, ip TEXT, path TEXT, status INTEGER)")
    conn.commit()
    conn.close()
_init()

def _log(action: str, user: str = "system", detail: str = "", ip: str = "", path: str = "", status: int = 200):
    try:
        conn = sqlite3.connect(str(DB))
        conn.execute("INSERT INTO audit (ts,action,user,detail,ip,path,status) VALUES (?,?,?,?,?,?,?)",
                     (time.time(), action, user, detail[:200], ip, path, status))
        conn.commit()
        conn.close()
    except: pass

@router.get("/log")
def audit_log(limit: int = 50, offset: int = 0):
    try:
        conn = sqlite3.connect(str(DB))
        c = conn.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
        rows = [{"id":r[0],"ts":r[1],"action":r[2],"user":r[3],"detail":r[4],"ip":r[5],"path":r[6],"status":r[7]} for r in c.fetchall()]
        total = conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
        conn.close()
        return {"success": True, "total": total, "entries": rows}
    except Exception as e:
        return {"success": False, "error": str(e)[:100]}

@router.get("/stats")
def audit_stats():
    try:
        conn = sqlite3.connect(str(DB))
        total = conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
        top = conn.execute("SELECT action, COUNT(*) as cnt FROM audit GROUP BY action ORDER BY cnt DESC LIMIT 10").fetchall()
        conn.close()
        return {"success": True, "total": total, "top_actions": [{"action":r[0],"count":r[1]} for r in top]}
    except Exception as e:
        return {"success": False, "error": str(e)[:100]}

_log("audit_init", "system", "审计日志系统初始化")
