"""AUTO-EVO-AI V0.1 — Meilisearch 搜索引擎桥接路由"""
from fastapi import APIRouter, Query
import urllib.request, json as _json

router = APIRouter()
B = "/api/v1/tools/meili"

MEILI_HOST = os.environ.get("MEILI_HOST", "http://127.0.0.1:7700")
MEILI_KEY = os.environ.get("MEILI_MASTER_KEY", "")

def _req(method, path, body=None):
    try:
        url = f"{MEILI_HOST}{path}"
        headers = {"Content-Type": "application/json"}
        if MEILI_KEY:
            headers["Authorization"] = f"Bearer {MEILI_KEY}"
        data = _json.dumps(body).encode() if body else None
        r = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(r, timeout=5) as resp:
            return _json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)[:200]}

@router.get(B)
async def meili_status():
    health = _req("GET", "/health")
    if "error" in health:
        return {"success": True, "available": False, "error": health["error"]}
    ver = _req("GET", "/version")
    indexes = _req("GET", "/indexes")
    return {
        "success": True, "available": True,
        "version": ver.get("pkgVersion", "?"),
        "indexes": [i["uid"] for i in indexes.get("results", [])],
    }

@router.get(B + "/search")
async def meili_search(
    q: str = Query("", description="搜索关键词"),
    index: str = Query("modules", description="索引名称"),
    limit: int = Query(10, le=50),
):
    result = _req("POST", f"/indexes/{index}/search", {"q": q, "limit": limit, "attributesToHighlight": ["name", "description", "content"]})
    if "error" in result:
        return {"success": False, "error": result["error"]}
    hits = []
    for h in result.get("hits", []):
        hits.append({
            "id": h.get("id", ""),
            "name": h.get("name", ""),
            "description": h.get("description", "")[:200],
            "group": h.get("group", ""),
            "grade": h.get("grade", ""),
            "score": h.get("_rankingScore", 0),
        })
    return {"success": True, "hits": hits, "total": result.get("estimatedTotalHits", 0)}

@router.post(B + "/index")
async def meili_create_index():
    """创建模块索引（将模块元数据写入 Meilisearch）"""
    from api.infra import registry
    names = set(registry.modules.keys()) | set(registry._pending_modules.keys()) | set(registry.classes.keys())
    docs = []
    from api.infra import BASE_DIR, classify_module
    for name in sorted(names):
        mod_file = BASE_DIR / "modules" / f"{name}.py"
        size = mod_file.stat().st_size if mod_file.exists() else 0
        grade = registry.health.get(name, {}).get("grade", "?")
        docs.append({
            "id": name, "name": name.replace("_", " ").title(),
            "description": registry.health.get(name, {}).get("error", "") or f"{name} module",
            "group": classify_module(name),
            "grade": grade, "size_bytes": size,
            "content": (mod_file.read_text(encoding="utf-8", errors="ignore")[:500] if mod_file.exists() else ""),
        })
    # 先删后建
    _req("DELETE", f"/indexes/modules")
    _req("POST", "/indexes", {"uid": "modules", "primaryKey": "id"})
    # 设置可搜索字段
    _req("PATCH", "/indexes/modules/settings", {"searchableAttributes": ["name", "description", "content", "group"]})
    # 批量写入
    r = _req("POST", "/indexes/modules/documents", docs)
    return {"success": True, "indexed": len(docs), "result": r}
