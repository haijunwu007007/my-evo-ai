"""routes_apps.py — 生成APP列表与管理

API端点:
  GET /api/v1/apps/list  — 列出所有已生成APP
"""
from __future__ import annotations
import os, json
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

APPS_DIR = Path(__file__).resolve().parent.parent.parent / "output" / "apps"


@router.get("/api/v1/apps/list")
async def list_apps():
    """列出 /output/apps/ 下所有已生成APP文件"""
    if not APPS_DIR.exists():
        return {"success": True, "apps": [], "total": 0}
    apps = []
    for f in sorted(APPS_DIR.iterdir()):
        if f.is_file() and f.suffix == ".html":
            stat = f.stat()
            apps.append({
                "name": f.name,
                "file": f.name,
                "size": f"{stat.st_size / 1024:.1f}KB",
                "mtime": f.stat().st_mtime,
            })
    return {"success": True, "apps": apps, "total": len(apps)}
