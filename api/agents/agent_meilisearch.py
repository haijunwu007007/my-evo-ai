"""MeiliSearch - AUTO-EVO-AI集成 (localhost:7700)"""
import json, httpx, os

MEILI_URL = os.environ.get("MEILI_URL", "http://localhost:7700")
MEILI_KEY = os.environ.get("MEILI_KEY", "")

def meilisearch_search(**kwargs):
    """MeiliSearch全文搜索"""
    try:
        query = kwargs.get("query", kwargs.get("q", ""))
        index = kwargs.get("index", kwargs.get("idx", "documents"))
        limit = int(kwargs.get("limit", 20))
        if not query: return {"ok": False, "data": None, "message": "请输入搜索关键词"}
        headers = {"Authorization": f"Bearer {MEILI_KEY}"}
        url = f"{MEILI_URL}/indexes/{index}/search"
        resp = httpx.post(url, json={"q": query, "limit": limit, "attributesToHighlight": ["*"]}, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            hits = data.get("hits", [])
            return {"ok": True, "data": {"hits": hits[:10], "total": data.get("estimatedTotalHits", 0), "query": query}, "message": f"找到{len(hits)}条结果"}
        return {"ok": False, "data": None, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except httpx.ConnectError:
        return {"ok": False, "data": None, "message": "无法连接MeiliSearch (localhost:7700)，请确认Docker容器已启动"}
    except Exception as e:
        return {"ok": False, "data": None, "message": f"MeiliSearch失败: {e}"}

def meilisearch_index(**kwargs):
    """列出MeiliSearch索引"""
    try:
        headers = {"Authorization": f"Bearer {MEILI_KEY}"}
        resp = httpx.get(f"{MEILI_URL}/indexes", headers=headers, timeout=10)
        if resp.status_code == 200:
            return {"ok": True, "data": resp.json(), "message": "ok"}
        return {"ok": False, "data": None, "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"ok": False, "data": None, "message": f"获取索引失败: {e}"}
