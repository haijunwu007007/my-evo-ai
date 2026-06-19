"""
N8N Workflow Bridge
"""
import os, json, sqlite3, re
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/v1/n8n", tags=["n8n"])

BASE = os.environ.get("N8N_BASE", "/home/ubuntu/n8n-workflows/n8n-workflows-main")
DB_PATH = BASE + "/workflows.db"

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@router.get("/status")
async def status():
    conn = _db()
    total = conn.execute("SELECT COUNT(*) as c FROM workflows").fetchone()["c"]
    stats = {"total": total, "active": 0, "inactive": 0}
    for r in conn.execute("SELECT active,COUNT(*) as c FROM workflows GROUP BY active"):
        k = "active" if r["active"] else "inactive"
        stats[k] = r["c"]
    triggers = {}
    for r in conn.execute("SELECT trigger,COUNT(*) as c FROM workflows GROUP BY trigger"):
        t = r["trigger"].split(".")[-1] if r["trigger"] else "Manual"
        triggers[t] = triggers.get(t, 0) + r["c"]
    stats["triggers"] = triggers
    complexity = {}
    for r in conn.execute("SELECT complexity,COUNT(*) as c FROM workflows GROUP BY complexity"):
        complexity[r["complexity"]] = r["c"]
    stats["complexity"] = complexity
    total_nodes = conn.execute("SELECT SUM(nodes) as s FROM workflows").fetchone()["s"] or 0
    stats["total_nodes"] = total_nodes
    stats["unique_integrations"] = conn.execute("SELECT COUNT(DISTINCT integrations) as c FROM workflows").fetchone()["c"]
    conn.close()
    return stats

@router.get("/search")
async def search(q: str = Query(""), cat: str = Query(None), page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    conn = _db()
    where = []
    params = []
    if q:
        where.append("(name LIKE ? OR filename LIKE ?)")
        params.extend(["%" + q + "%", "%" + q + "%"])
    if cat:
        where.append("integrations LIKE ?")
        params.append("%" + cat + "%")
    w = " AND ".join(where) if where else "1=1"
    total = conn.execute(f"SELECT COUNT(*) as c FROM workflows WHERE {w}", params).fetchone()["c"]
    offset = (page - 1) * limit
    rows = conn.execute(f"SELECT id,filename,name FROM workflows WHERE {w} ORDER BY nodes DESC LIMIT ? OFFSET ?", params + [limit, offset]).fetchall()
    results = [{"id": r["id"], "filename": r["filename"], "name": r["name"][:80] if r["name"] else ""} for r in rows]
    conn.close()
    return {"success": True, "total": total, "results": results, "page": page}

@router.get("/categories")
async def categories():
    conn = _db()
    cats = set()
    for r in conn.execute("SELECT integrations FROM workflows").fetchall():
        try:
            for i in json.loads(r["integrations"]):
                if i and i not in ("I", "IError"):
                    cats.add(i)
        except:
            pass
    conn.close()
    return {"success": True, "categories": sorted(cats)}

@router.get("/integrations")
async def integrations():
    conn = _db()
    tags = {}
    for r in conn.execute("SELECT integrations,COUNT(*) as c FROM workflows GROUP BY integrations ORDER BY c DESC LIMIT 50").fetchall():
        try:
            for i in json.loads(r["integrations"]):
                if i and i not in ("I", "IError"):
                    tags[i] = tags.get(i, 0) + r["c"]
        except:
            pass
    conn.close()
    return {"success": True, "integrations": sorted(tags.items(), key=lambda x: -x[1])[:50]}

@router.get("/category/{cat}")
async def by_category(cat: str, page: int = Query(1, ge=1), limit: int = Query(20)):
    conn = _db()
    total = conn.execute("SELECT COUNT(*) as c FROM workflows WHERE integrations LIKE ?", ["%" + cat + "%"]).fetchone()["c"]
    offset = (page - 1) * limit
    rows = conn.execute("SELECT id,filename,name FROM workflows WHERE integrations LIKE ? ORDER BY nodes DESC LIMIT ? OFFSET ?", ["%" + cat + "%", limit, offset]).fetchall()
    results = [{"id": r["id"], "filename": r["filename"], "name": r["name"][:80] if r["name"] else ""} for r in rows]
    conn.close()
    return {"success": True, "total": total, "results": results}

@router.get("/workflow/{wid}")
async def workflow_detail(wid: int):
    conn = _db()
    r = conn.execute("SELECT * FROM workflows WHERE id=?", (wid,)).fetchone()
    conn.close()
    if not r:
        return {"success": False, "error": "not found"}
    raw = json.loads(r["raw"]) if r["raw"] else {}
    return {
        "success": True,
        "id": r["id"],
        "filename": r["filename"],
        "name": r["name"],
        "active": bool(r["active"]),
        "nodes": r["nodes"],
        "trigger": r["trigger"],
        "complexity": r["complexity"],
        "integrations": json.loads(r["integrations"]) if r["integrations"] else [],
        "raw": raw,
    }

@router.get("/index")
async def reindex():
    conn = _db()
    total = conn.execute("SELECT COUNT(*) as c FROM workflows").fetchone()["c"]
    return {"total": total, "db_path": DB_PATH}
