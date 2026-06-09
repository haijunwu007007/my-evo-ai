"""Gitea Issue 同步 API 路由"""

from fastapi import APIRouter, Query
from modules.gitea_issue_sync import sync_to_coordinator, get_sync_status

router = APIRouter()

@router.get("/api/v1/gitea-sync/status")
async def gitea_sync_status():
    """Gitea 同步状态"""
    return await get_sync_status()

@router.post("/api/v1/gitea-sync/sync")
async def gitea_sync_now(owner: str = Query("", description="仓库所有者"), repo: str = Query("", description="仓库名")):
    """手动触发 Gitea Issue 同步"""
    return await sync_to_coordinator(owner, repo)
