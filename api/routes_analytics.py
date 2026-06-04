"""使用数据 — 埋点 + 分析API"""
from fastapi import APIRouter
from core.logging_config import get_logger
import os, json, time, sqlite3
from pathlib import Path

logger = get_logger("evo.api.analytics")
router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
_DB = BASE_DIR / "core" / "adaptive_engine.db"

def _init():
    conn = sqlite3.connect(str(_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS analytics_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT, endpoint TEXT, project_id TEXT DEFAULT '', duration REAL, status INTEGER, created_at REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS analytics_errors (id INTEGER PRIMARY KEY AUTOINCREMENT, error_type TEXT, message TEXT, endpoint TEXT, created_at REAL)")
    conn.commit(); conn.close()
_init()

@router.post("/api/v1/analytics/event")
async def track_event(event: str = "", endpoint: str = "", project_id: str = "", duration: float = 0.0, status: int = 200):
    conn = sqlite3.connect(str(_DB))
    conn.execute("INSERT INTO analytics_events (event, endpoint, project_id, duration, status, created_at) VALUES (?,?,?,?,?,?)",
                 (event, endpoint, project_id, duration, status, time.time()))
    conn.commit(); conn.close()
    return {"success": True}

@router.post("/api/v1/analytics/error")
async def track_error(error_type: str = "", message: str = "", endpoint: str = ""):
    conn = sqlite3.connect(str(_DB))
    conn.execute("INSERT INTO analytics_errors (error_type, message, endpoint, created_at) VALUES (?,?,?,?)",
                 (error_type, message[:500], endpoint, time.time()))
    conn.commit(); conn.close()
    return {"success": True}

@router.get("/api/v1/analytics/top-endpoints")
async def top_endpoints(limit: int = 20):
    conn = sqlite3.connect(str(_DB))
    rows = conn.execute("SELECT endpoint, COUNT(*) as cnt, AVG(duration) as avg_dur FROM analytics_events WHERE endpoint != '' GROUP BY endpoint ORDER BY cnt DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return {"success": True, "data": [{"endpoint":r[0],"count":r[1],"avg_duration_ms":round(r[2]*1000,1)} for r in rows]}

@router.get("/api/v1/analytics/summary")
async def analytics_summary():
    conn = sqlite3.connect(str(_DB))
    total = conn.execute("SELECT COUNT(*) FROM analytics_events").fetchone()[0]
    errors = conn.execute("SELECT COUNT(*) FROM analytics_errors").fetchone()[0]
    avg_dur = conn.execute("SELECT AVG(duration) FROM analytics_events").fetchone()[0] or 0
    conn.close()
    return {"success": True, "total_events": total, "total_errors": errors, "avg_duration_ms": round(avg_dur*1000, 1)}
