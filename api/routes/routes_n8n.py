"""
N8N Workflow Bridge + Full Reverse Proxy
"""
import os, json, sqlite3, re, httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from urllib.parse import urljoin

router = APIRouter(tags=["n8n"])

BASE = os.environ.get("N8N_BASE", "/home/ubuntu/n8n-workflows/n8n-workflows-main")
DB_PATH = BASE + "/workflows.db"
N8N_HOST = "http://127.0.0.1:18000"

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _rewrite_html(html: str) -> str:
    """重写n8n HTML中所有绝对路径，添加反向代理前缀"""
    p = "/api/v1/n8n/editor"
    # Replace href/src absolute paths
    for attr in ('href', 'src'):
        html = re.sub(f'{attr}="/', f'{attr}="{p}/', html)
    return html

async def _proxy(path: str):
    """反向代理到n8n容器，自动重写HTML资源路径"""
    url = urljoin(N8N_HOST + "/", path)
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.get(url, follow_redirects=True)
            ct = resp.headers.get("content-type", "")
            if "text/html" in ct:
                return HTMLResponse(content=_rewrite_html(resp.text), status_code=resp.status_code)
            return Response(content=resp.content, status_code=resp.status_code, media_type=ct)
    except ImportError:
        import urllib.request
        r = urllib.request.urlopen(url, timeout=15)
        ct = r.headers.get("content-type", "text/html")
        if "text/html" in ct:
            return HTMLResponse(content=_rewrite_html(r.read().decode('utf-8','replace')), status_code=r.status)
        return Response(content=r.read(), status_code=r.status, media_type=ct)
    except Exception as e:
        return JSONResponse({"error": str(e)[:100]}, status_code=502)

@router.get("/api/v1/n8n/editor")
async def n8n_editor_root():
    return await _proxy("")

@router.get("/api/v1/n8n/editor/{path:path}")
async def n8n_editor_proxy(path: str):
    return await _proxy(path)

@router.api_route("/api/v1/n8n/editor/{path:path}", methods=["POST", "PUT", "DELETE", "PATCH"])
async def n8n_editor_api(path: str, request: Request):
    """代理n8n REST API调用"""
    url = urljoin(N8N_HOST + "/", path)
    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length", "transfer-encoding")}
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60) as c:
            resp = await c.request(method=request.method, url=url, content=body, headers=headers, follow_redirects=True)
            return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))
    except ImportError:
        import urllib.request, urllib.parse
        req = urllib.request.Request(url, data=body, headers=headers, method=request.method)
        r = urllib.request.urlopen(req, timeout=30)
        return Response(content=r.read(), status_code=r.status, media_type=r.headers.get("content-type"))
    except Exception as e:
        return JSONResponse({"error": str(e)[:100]}, status_code=502)

@router.get("/api/v1/n8n/status")
async def status():
    conn = _db()
    total = conn.execute("SELECT COUNT(*) as c FROM workflows").fetchone()["c"]
    stats = {"total": total}
    for r in conn.execute("SELECT active,COUNT(*) as c FROM workflows GROUP BY active"):
        k = "active" if r["active"] else "inactive"
        stats[k] = r["c"]
    triggers = {}
    for r in conn.execute("SELECT trigger,COUNT(*) as c FROM workflows GROUP BY trigger"):
        t = r["trigger"].split(".")[-1] if r["trigger"] else "Manual"
        triggers[t] = triggers.get(t, 0) + r["c"]
    stats["triggers"] = triggers
    conn.close()
    return stats

@router.get("/api/v1/n8n/search")
async def search(q: str = Query(""), page: int = Query(1, ge=1), limit: int = Query(20)):
    conn = _db()
    where = []
    params = []
    if q:
        where.append("(name LIKE ? OR filename LIKE ?)")
        params.extend(["%" + q + "%", "%" + q + "%"])
    w = " AND ".join(where) if where else "1=1"
    total = conn.execute(f"SELECT COUNT(*) as c FROM workflows WHERE {w}", params).fetchone()["c"]
    ofs = (page - 1) * limit
    rows = conn.execute(f"SELECT id,filename,name FROM workflows WHERE {w} ORDER BY nodes DESC LIMIT ? OFFSET ?", params + [limit, ofs]).fetchall()
    res = [{"id": r["id"], "filename": r["filename"], "name": r["name"][:80] if r["name"] else ""} for r in rows]
    conn.close()
    return {"success": True, "total": total, "results": res, "page": page}

@router.get("/api/v1/n8n/categories")
async def categories():
    conn = _db()
    cats = set()
    for r in conn.execute("SELECT integrations FROM workflows"):
        try:
            for i in json.loads(r["integrations"]):
                if i and i not in ("I", "IError"):
                    cats.add(i)
        except: pass
    conn.close()
    return {"success": True, "categories": sorted(cats)}

@router.get("/api/v1/n8n/integrations")
async def integrations():
    conn = _db()
    tags = {}
    for r in conn.execute("SELECT integrations,COUNT(*) as c FROM workflows GROUP BY integrations ORDER BY c DESC LIMIT 50"):
        try:
            for i in json.loads(r["integrations"]):
                if i and i not in ("I", "IError"):
                    tags[i] = tags.get(i, 0) + r["c"]
        except: pass
    conn.close()
    return {"success": True, "integrations": sorted(tags.items(), key=lambda x: -x[1])[:50]}

@router.get("/api/v1/n8n/workflow/{wid}")
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
        "integrations": json.loads(r["integrations"]) if r["integrations"] else [],
        "raw": raw,
    }
