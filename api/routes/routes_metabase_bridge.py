"""Metabase 数据桥接 — 系统数据 → Metabase 可查询格式"""

from fastapi import APIRouter
import sqlite3, os, json
from pathlib import Path
from core.logging_config import get_logger

logger = get_logger("evo.api.metabase-bridge")
router = APIRouter()

MB_DB_PATH = Path(__file__).parent.parent.parent / "_data" / "metabase_bridge" / "evo_analytics.db"

def _ensure_db():
    """确保分析数据库存在"""
    MB_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(MB_DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS modules_snapshot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT NOT NULL,
            total_modules INTEGER,
            loaded_modules INTEGER,
            stub_modules INTEGER,
            grade_a INTEGER DEFAULT 0,
            grade_b INTEGER DEFAULT 0,
            grade_c INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            endpoint TEXT,
            status_code INTEGER,
            duration_ms REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS engine_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            engine_name TEXT,
            active INTEGER,
            task_count INTEGER
        )
    """)
    conn.commit()
    return conn

@router.get("/api/v1/metabase/status")
async def metabase_status():
    """Metabase 桥接状态"""
    return {
        "success": True,
        "db_path": str(MB_DB_PATH),
        "metabase_connect": {
            "type": "sqlite",
            "path": str(MB_DB_PATH),
            "note": "在Metabase中添加SQLite数据库连接到此路径"
        }
    }

@router.post("/api/v1/metabase/snapshot")
async def take_snapshot():
    """采集系统快照写入分析数据库"""
    import httpx, datetime
    conn = _ensure_db()
    now = datetime.datetime.now().isoformat()
    
    try:
        r = await httpx.AsyncClient(timeout=10).get("http://127.0.0.1:8765/api/v1/status")
        if r.status_code == 200:
            data = r.json()
            conn.execute(
                "INSERT INTO modules_snapshot (snapshot_date, total_modules, loaded_modules, stub_modules) VALUES (?,?,?,?)",
                (now, data.get("modules_total", 0), data.get("modules_loaded", 0), data.get("modules_stub", 0))
            )
    except Exception as _e:
        logger.warning(f"error: {_e}")
    
    conn.commit()
    conn.close()
    return {"success": True, "snapshot_at": now}

@router.get("/api/v1/metabase/modules-snapshots")
async def get_snapshots(limit: int = 100):
    """获取模块快照数据"""
    conn = _ensure_db()
    rows = conn.execute(
        "SELECT * FROM modules_snapshot ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return {
        "success": True,
        "data": [dict(zip(["id","date","total","loaded","stub","grade_a","grade_b","grade_c"], r)) for r in rows],
        "metabase_sqlite_path": str(MB_DB_PATH),
        "how_to_connect": f"Metabase → 添加数据库 → SQLite → 选择文件: {MB_DB_PATH}"
    }
