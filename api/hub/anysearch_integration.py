"""AnySearch 集成 — AI Agent 统一实时搜索"""
import logging
logger = logging.getLogger("evo.anysearch_integration")

import json, os, time, hashlib
from typing import Optional

API_BASE = "https://api.anysearch.com"
API_KEY = os.environ.get("ANYSEARCH_API_KEY", "")

def anysearch_search(query: str, domain: str = "general", max_results: int = 10) -> dict:
    """通用搜索"""
    if not API_KEY:
        return {"ok": False, "data": "请配置 ANYSEARCH_API_KEY 环境变量"}
    try:
        import httpx
        r = httpx.post(f"{API_BASE}/v1/search", json={
            "query": query, "domain": domain, "max_results": max_results,
            "structured": True
        }, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=15)
        return {"ok": r.is_success, "data": r.json() if r.is_success else r.text[:200],
                "source": "anysearch"}
    except Exception as e:
        return {"ok": False, "data": f"AnySearch 搜索失败: {e}"}

def anysearch_batch(queries: list) -> dict:
    """批量并行搜索"""
    if not API_KEY:
        return {"ok": False, "data": "请配置 ANYSEARCH_API_KEY"}
    try:
        import httpx, asyncio
        async def _batch():
            async with httpx.AsyncClient() as c:
                tasks = [c.post(f"{API_BASE}/v1/search", json={"query": q, "structured": True},
                                headers={"Authorization": f"Bearer {API_KEY}"}, timeout=10) for q in queries]
                return await asyncio.gather(*tasks)
        results = asyncio.run(_batch())
        data = [r.json() for r in results if r.is_success]
        return {"ok": True, "data": data, "count": len(data)}
    except Exception as e:
        return {"ok": False, "data": f"批量搜索失败: {e}"}

def anysearch_extract(url: str) -> dict:
    """提取网页全文"""
    if not API_KEY:
        return {"ok": False, "data": "请配置 ANYSEARCH_API_KEY"}
    try:
        import httpx
        r = httpx.post(f"{API_BASE}/v1/extract", json={"url": url},
                       headers={"Authorization": f"Bearer {API_KEY}"}, timeout=20)
        return {"ok": r.is_success, "data": r.json() if r.is_success else r.text[:200]}
    except Exception as e:
        return {"ok": False, "data": f"提取失败: {e}"}
