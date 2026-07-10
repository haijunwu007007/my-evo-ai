"""企业安全审计 — 全程操作日志+审计追踪（借鉴 WorkBuddy）
记录所有API操作：谁、什么时间、做了什么、结果如何。
支持审计日志查询、导出、统计。
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from core.logging_config import get_logger
import os, json, time, sqlite3
from pathlib import Path

logger = get_logger("evo.api.audit_trail")
router = APIRouter()
BASE = Path(__file__).resolve().parent.parent.parent
DB = BASE / "data" / "audit_trail.db"

def _db():
    conn = sqlite3.connect(str(DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT, action TEXT, target TEXT, detail TEXT,
        status TEXT, ip TEXT, created_at REAL
    )""")
    conn.commit()
    return conn

def log_audit(user: str, action: str, target: str = "", detail: str = "", status: str = "success", ip: str = ""):
    try:
        conn = _db()
        conn.execute("INSERT INTO audit_logs(user,action,target,detail,status,ip,created_at) VALUES(?,?,?,?,?,?,?)",
                     (user, action, target, str(detail)[:500], status, ip, time.time()))
        conn.commit()
        conn.close()
        # 自动清理30天前的日志
        _cleanup_old()
    except Exception as _e:
            logger.warning(f"[Audit] 异常: {_e}")

def _cleanup_old():
    try:
        conn = _db()
        cutoff = time.time() - 86400 * 30
        conn.execute("DELETE FROM audit_logs WHERE created_at < ?", (cutoff,))
        conn.commit()
        conn.close()
    except Exception:
        pass

class AuditLogInput(BaseModel):
    user: str = "system"; action: str; target: str = ""; detail: str = ""; status: str = "success"; ip: str = ""

@router.post("/api/v1/audit/log")
async def write_audit(m: AuditLogInput):
    log_audit(m.user, m.action, m.target, m.detail, m.status, m.ip)
    return {"success": True}

@router.get("/api/v1/audit/logs")
async def read_audit(user: str = "", action: str = "", limit: int = 100, offset: int = 0):
    conn = _db()
    sql = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    if user: sql += " AND user=?"; params.append(user)
    if action: sql += " AND action=?"; params.append(action)
    sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = conn.execute(sql, params).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
    conn.close()
    return {"success": True, "total": total, "logs": [
        {"id":r[0],"user":r[1],"action":r[2],"target":r[3],"detail":r[4][:200],"status":r[5],"ip":r[6],"time":r[7]} for r in rows
    ]}

@router.get("/api/v1/audit/stats")
async def audit_stats():
    conn = _db()
    total = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
    by_action = conn.execute("SELECT action,COUNT(*) as c FROM audit_logs GROUP BY action ORDER BY c DESC LIMIT 10").fetchall()
    by_user = conn.execute("SELECT user,COUNT(*) as c FROM audit_logs GROUP BY user ORDER BY c DESC LIMIT 10").fetchall()
    conn.close()
    return {"success": True, "total_logs": total,
            "top_actions": [{"action":r[0],"count":r[1]} for r in by_action],
            "top_users": [{"user":r[0],"count":r[1]} for r in by_user]}
