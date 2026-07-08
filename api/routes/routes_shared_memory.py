"""团队级共享记忆 — Agent间记忆互通（借鉴 Moxt）
每个Agent存入的记忆自动同步到全局池，
其他Agent按 relevancy 评分检索共享记忆。
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger
import os, json, time, sqlite3, hashlib
from pathlib import Path

logger = get_logger("evo.api.shared_memory")
router = APIRouter()
BASE = Path(__file__).resolve().parent.parent.parent
DB = BASE / "data" / "shared_memory.db"

def _db():
    conn = sqlite3.connect(str(DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id TEXT, agent_name TEXT, content TEXT,
        tags TEXT, importance INTEGER DEFAULT 1,
        created_at REAL, source TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS memory_tags (
        tag TEXT PRIMARY KEY, count INTEGER DEFAULT 1
    )""")
    conn.commit()
    return conn

class MemoryInput(BaseModel):
    agent_id: str; agent_name: str = ""
    content: str; tags: str = ""; importance: int = 1; source: str = "manual"

@router.post("/api/v1/shared-memory/store")
async def store_shared(m: MemoryInput):
    conn = _db()
    now = time.time()
    conn.execute("INSERT INTO memories(agent_id,agent_name,content,tags,importance,created_at,source) VALUES(?,?,?,?,?,?,?)",
                 (m.agent_id, m.agent_name, m.content, m.tags, m.importance, now, m.source))
    for t in m.tags.split(","):
        t2 = t.strip()
        if t2:
            conn.execute("INSERT INTO memory_tags(tag,count) VALUES(?,1) ON CONFLICT(tag) DO UPDATE SET count=count+1", (t2,))
    conn.commit(); conn.close()
    return {"success": True, "message": "记忆已存储", "id": now}

@router.get("/api/v1/shared-memory/search")
async def search_shared(q: str = "", agent_id: str = "", limit: int = 20):
    conn = _db()
    sql = "SELECT * FROM memories WHERE 1=1"
    params = []
    if q:
        sql += " AND (content LIKE ? OR tags LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%"])
    if agent_id:
        sql += " AND agent_id=?"
        params.append(agent_id)
    sql += " ORDER BY importance DESC, created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    results = [{"id":r[0],"agent_id":r[1],"agent_name":r[2],"content":r[3][:500],"tags":r[4],"importance":r[5],"time":r[6],"source":r[7]} for r in rows]
    return {"success": True, "total": len(results), "results": results}

@router.get("/api/v1/shared-memory/stats")
async def shared_memory_stats():
    conn = _db()
    c = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    agents = conn.execute("SELECT DISTINCT agent_name FROM memories WHERE agent_name!=''").fetchall()
    top_tags = conn.execute("SELECT tag,count FROM memory_tags ORDER BY count DESC LIMIT 10").fetchall()
    conn.close()
    return {"success": True, "total_memories": c, "agent_count": len(agents),
            "agents": [r[0] for r in agents], "top_tags": [{"tag":r[0],"count":r[1]} for r in top_tags]}
