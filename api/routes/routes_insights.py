from __future__ import annotations
"""
AUTO-EVO-AI V0.1 — 进化洞察 API
上市公司级: 趋势报告查询+自我进化记录
"""

from core.logging_config import get_logger
import os
from typing import Any, Dict

from fastapi import APIRouter, Query

logger = get_logger("evo.api.insights")
router = APIRouter()

INSIGHTS_DIR = os.path.join(os.path.dirname(__file__), "..", ".evo_data", "insights")


@router.get("/api/v1/insights/reports")
async def list_reports(limit: int = Query(7, ge=1, le=30)):
    """获取进化报告列表"""
    if not os.path.exists(INSIGHTS_DIR):
        return {"success": True, "reports": [], "count": 0}
    files = sorted(
        [f for f in os.listdir(INSIGHTS_DIR) if f.startswith("evolution_") and f.endswith(".md")],
        reverse=True,
    )[:limit]
    reports = []
    for fname in files:
        path = os.path.join(INSIGHTS_DIR, fname)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        reports.append({
            "date": fname.replace("evolution_", "").replace(".md", ""),
            "content": content[:1000],
            "length": len(content),
        })
    return {"success": True, "reports": reports, "count": len(reports)}


@router.get("/api/v1/insights/evolution")
async def get_latest_evolution():
    """获取最新进化报告"""
    if not os.path.exists(INSIGHTS_DIR):
        return {"success": False, "error": "暂无进化记录"}
    files = [f for f in os.listdir(INSIGHTS_DIR) if f.startswith("evolution_") and f.endswith(".md")]
    if not files:
        return {"success": False, "error": "暂无进化记录"}
    latest = sorted(files, reverse=True)[0]
    path = os.path.join(INSIGHTS_DIR, latest)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    return {
        "success": True,
        "date": latest.replace("evolution_", "").replace(".md", ""),
        "content": content[:2000],
        "full_path": path,
    }
