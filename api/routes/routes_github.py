"""
AUTO-EVO-AI V0.1 — GitHub Trending API 路由
提供 GitHub 热门项目扫描和趋势分析的 REST API
"""
import logging
logger = logging.getLogger("evo.routes_github")

import os
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class TrendingRequest(BaseModel):
    language: str = ""
    period: str = "daily"
    limit: int = 25
    ai_filter: bool = False

@router.post("/api/v1/github/trending")
async def github_trending(req: TrendingRequest):
    """获取 GitHub Trending 热门项目"""
    try:
        from modules.githubtrending import GithubTrending
        scanner = GithubTrending()
        result = scanner.fetch_trending(
            language=req.language,
            period=req.period,
            limit=req.limit,
            ai_filter=req.ai_filter,
        )
        return {"success": True, "result": result}
    except ImportError:
        try:
            from core.github_scanner import GithubScanner
            scanner = GithubScanner()
            repos = scanner.scan_trending(language=req.language, limit=req.limit)
            return {"success": True, "result": repos}
        except Exception as e:
            return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/api/v1/github/trending")
async def github_trending_get(
    language: str = Query("", description="编程语言过滤"),
    period: str = Query("daily", description="周期: daily/weekly/monthly"),
    limit: int = Query(25, description="返回数量"),
    ai_filter: bool = Query(False, description="仅AI项目"),
):
    """获取 GitHub Trending 热门项目（GET 版本）"""
    try:
        from modules.githubtrending import GithubTrending
        scanner = GithubTrending()
        result = scanner.fetch_trending(
            language=language, period=period, limit=limit, ai_filter=ai_filter,
        )
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
