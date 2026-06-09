"""事件中心 — 系统事件查询API"""
from fastapi import APIRouter
from core.logging_config import get_logger
import sqlite3, json, time
from pathlib import Path

logger = get_logger("evo.api.events")
router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

@router.get("/api/v1/events")
async def list_events(limit: int = 50):
    """获取最近系统事件"""
    db_path = BASE_DIR / "core" / "adaptive_engine.db"
    events = []
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            rows = conn.execute(
                "SELECT event, endpoint, created_at FROM analytics_events ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            conn.close()
            events = [{"event": r[0], "endpoint": r[1], "time": r[2]} for r in rows]
        except Exception as e:
            logger.warning(f"读取事件失败: {e}")
    return {"success": True, "total": len(events), "events": events}
