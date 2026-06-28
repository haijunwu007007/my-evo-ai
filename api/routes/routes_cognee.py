"""Cognee 记忆系统 — remember/recall/forget/improve API
灵感: Cognee, Hermes Agent 记忆系统
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import sqlite3, json, time, hashlib, threading, os
from pathlib import Path
from datetime import datetime

router = APIRouter(prefix="/api/v1/cognee", tags=["cognee"])

_MEM_DB = Path(__file__).resolve().parent.parent.parent / "data" / "cognee_mem.db"
_MEM_DB.parent.mkdir(exist_ok=True)

_local = threading.local()

def _db():
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(str(_MEM_DB))
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA synchronous=NORMAL")
        _init_schema(_local.conn)
    return _local.conn

def _init_schema(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            embedding TEXT,
            tags TEXT DEFAULT '[]',
            source TEXT DEFAULT 'user',
            importance INTEGER DEFAULT 1,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            access_count INTEGER DEFAULT 0
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(content, tags, content=memories, content_rowid=rowid);
        CREATE TABLE IF NOT EXISTS skills (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            code TEXT,
            trigger_pattern TEXT,
            created_at REAL NOT NULL,
            use_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS experiences (
            id TEXT PRIMARY KEY,
            task TEXT NOT NULL,
            steps TEXT DEFAULT '[]',
            result TEXT,
            success INTEGER DEFAULT 1,
            created_at REAL NOT NULL
        );
    """)
    conn.commit()

# ─── Models ───
class RememberRequest(BaseModel):
    content: str
    tags: list[str] = []
    source: str = "user"
    importance: int = 1

class RecallRequest(BaseModel):
    query: str
    limit: int = 10

class ImproveRequest(BaseModel):
    task: str
    steps: list[str] = []
    result: str = ""

# ─── API ───

@router.get("/status")
async def status():
    conn = _db()
    mc = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    sc = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    ec = conn.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
    return {"success": True, "memories": mc, "skills": sc, "experiences": ec, "version": "1.0"}

@router.post("/remember")
async def remember(req: RememberRequest):
    """存储记忆"""
    conn = _db()
    mid = hashlib.md5((req.content + str(time.time())).encode()).hexdigest()[:16]
    now = time.time()
    tags_json = json.dumps(req.tags, ensure_ascii=False)
    conn.execute(
        "INSERT OR REPLACE INTO memories(id,content,tags,source,importance,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
        (mid, req.content, tags_json, req.source, req.importance, now, now)
    )
    conn.execute("INSERT INTO memories_fts(rowid,content,tags) VALUES(last_insert_rowid(),?,?)", (req.content, tags_json))
    conn.commit()
    return {"success": True, "id": mid, "message": "记忆已存储"}

@router.post("/recall")
async def recall(req: RecallRequest):
    """检索记忆 — FTS5 全文搜索"""
    conn = _db()
    query = req.query.strip()
    if not query:
        # 最近记忆
        rows = conn.execute("SELECT id,content,tags,source,importance,created_at,access_count FROM memories ORDER BY created_at DESC LIMIT ?", (req.limit,)).fetchall()
    else:
        # FTS5 搜索
        terms = ' OR '.join(query.split())
        sql = """
            SELECT m.id, m.content, m.tags, m.source, m.importance, m.created_at, m.access_count,
                   rank
            FROM memories_fts f
            JOIN memories m ON m.rowid = f.rowid
            WHERE memories_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """
        try:
            rows = conn.execute(sql, (terms, req.limit)).fetchall()
        except sqlite3.OperationalError:
            rows = conn.execute("SELECT id,content,tags,source,importance,created_at,access_count FROM memories ORDER BY created_at DESC LIMIT ?", (req.limit,)).fetchall()
    results = []
    for r in rows:
        results.append({
            "id": r["id"], "content": r["content"],
            "tags": json.loads(r["tags"]),
            "source": r["source"], "importance": r["importance"],
            "created_at": datetime.fromtimestamp(r["created_at"]).isoformat(),
            "access_count": r["access_count"],
        })
        conn.execute("UPDATE memories SET access_count = access_count + 1 WHERE id = ?", (r["id"],))
    conn.commit()
    return {"success": True, "results": results, "total": len(results)}

@router.post("/forget")
async def forget(mid: str):
    """删除记忆"""
    conn = _db()
    conn.execute("DELETE FROM memories WHERE id = ?", (mid,))
    conn.commit()
    return {"success": True, "message": "记忆已删除"}

@router.post("/improve")
async def improve(req: ImproveRequest):
    """从经验中改进 — 记录任务步骤和结果"""
    conn = _db()
    eid = hashlib.md5((req.task + str(time.time())).encode()).hexdigest()[:16]
    now = time.time()
    conn.execute(
        "INSERT INTO experiences(id,task,steps,result,created_at) VALUES(?,?,?,?,?)",
        (eid, req.task, json.dumps(req.steps), req.result, now)
    )
    conn.commit()
    return {"success": True, "id": eid, "message": "经验已记录"}

@router.get("/skills")
async def list_skills():
    conn = _db()
    rows = conn.execute("SELECT id,name,description,trigger_pattern,use_count,created_at FROM skills ORDER BY use_count DESC").fetchall()
    return {"success": True, "skills": [dict(r) for r in rows], "total": len(rows)}

@router.post("/skills/learn")
async def learn_skill(name: str, description: str = "", trigger_pattern: str = "", code: str = ""):
    """学习新技能"""
    conn = _db()
    sid = hashlib.md5((name + str(time.time())).encode()).hexdigest()[:16]
    conn.execute(
        "INSERT OR IGNORE INTO skills(id,name,description,code,trigger_pattern,created_at) VALUES(?,?,?,?,?,?)",
        (sid, name, description, code, trigger_pattern, time.time())
    )
    conn.commit()
    return {"success": True, "id": sid, "message": f"技能 '{name}' 已学习"}

@router.get("/stats")
async def stats():
    """记忆统计"""
    conn = _db()
    mc = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    sc = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    ec = conn.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
    top = conn.execute("SELECT content, access_count FROM memories ORDER BY access_count DESC LIMIT 5").fetchall()
    return {
        "success": True,
        "memories": mc, "skills": sc, "experiences": ec,
        "most_accessed": [{"content": r["content"][:60], "count": r["access_count"]} for r in top],
    }
