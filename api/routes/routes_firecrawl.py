"""Firecrawl (30k⭐) — AI 网页爬虫桥接"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os, json, urllib.request
from core.logging_config import get_logger

logger = get_logger("evo.routes_firecrawl")
router = APIRouter(prefix="/api/v1/tools/firecrawl", tags=["tools"])

FIRECRAWL_URL = os.environ.get("FIRECRAWL_URL", "http://localhost:3002")
FIRECRAWL_KEY = os.environ.get("FIRECRAWL_API_KEY", "")


class CrawlRequest(BaseModel):
    url: str
    limit: int = 10
    scrape_options: dict | None = None


@router.get("")
async def get_status():
    return {
        "available": True,
        "url": FIRECRAWL_URL,
        "configured": bool(FIRECRAWL_KEY),
        "name": "Firecrawl",
        "description": "AI 网页爬虫 (30k⭐) — 为 RAG 知识库抓取网页数据",
    }


@router.get("/health")
async def health_check():
    try:
        req = urllib.request.Request(
            f"{FIRECRAWL_URL}/v1/health", method="GET",
            headers={"Authorization": f"Bearer {FIRECRAWL_KEY}"} if FIRECRAWL_KEY else {},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            return {"healthy": True, "status": resp.status}
    except Exception as e:
        return {"healthy": False, "error": str(e)[:60]}


@router.post("/crawl")
async def crawl(req: CrawlRequest):
    try:
        body = json.dumps({"url": req.url, "limit": req.limit}).encode()
        headers = {"Content-Type": "application/json"}
        if FIRECRAWL_KEY:
            headers["Authorization"] = f"Bearer {FIRECRAWL_KEY}"
        request = urllib.request.Request(
            f"{FIRECRAWL_URL}/v1/crawl", data=body, headers=headers, method="POST"
        )
        with urllib.request.urlopen(request, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:120])
