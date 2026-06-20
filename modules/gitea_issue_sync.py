from modules._base.enterprise_module import EnterpriseModule
"""
Grade: A
Gitea Issue ↔ 协调中心双向同步 Plugin
"""

__module_meta__ = {
    "id": "gitea-issue-sync",
    "name": "Gitea Issue Sync",
    "version": "V0.1",
    "group": "devops",
}

import os, json, hashlib, datetime
from typing import Optional
import httpx
from core.logging_config import get_logger

logger = get_logger("evo.plugin.gitea-sync")

GITEA_URL = os.getenv("GITEA_URL", "http://localhost:3000")
GITEA_TOKEN = os.getenv("GITEA_TOKEN", "")
SYNC_INTERVAL = int(os.getenv("GITEA_SYNC_INTERVAL", "60"))  # 秒

_issues_cache: dict = {}
_last_sync: Optional[datetime.datetime] = None

async def get_issues(owner: str = "", repo: str = "") -> list:
    """获取 Gitea Issue 列表"""
    try:
        url = f"{GITEA_URL}/api/v1/repos/{owner}/{repo}/issues?state=open&sort=updated"
        headers = {"Authorization": f"token {GITEA_TOKEN}"} if GITEA_TOKEN else {}
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, headers=headers)
            if r.status_code == 200:
                return r.json()
            logger.warning(f"[Gitea Sync] API error: {r.status_code}")
    except Exception as e:
        logger.error(f"[Gitea Sync] Request failed: {e}")
    return []

def issues_to_tasks(issues: list) -> list:
    """Gitea Issue → 协调中心任务格式"""
    tasks = []
    for issue in issues:
        task = {
            "title": issue.get("title", ""),
            "source": "gitea",
            "source_id": str(issue.get("id", "")),
            "url": issue.get("html_url", ""),
            "status": "pending",
            "priority": "medium",
            "labels": [l.get("name", "") for l in issue.get("labels", [])],
            "assignee": issue.get("assignee", {}).get("login", "") if issue.get("assignee") else "",
            "created": issue.get("created_at", ""),
            "updated": issue.get("updated_at", ""),
        }
        tasks.append(task)
    return tasks

async def sync_to_coordinator(owner: str = "", repo: str = "") -> dict:
    """同步 Issue 到协调中心"""
    global _last_sync
    issues = await get_issues(owner, repo)
    tasks = issues_to_tasks(issues)
    
    # 去重: 只返回新的/更新的
    new_tasks = []
    for t in tasks:
        key = t["source_id"]
        old_hash = _issues_cache.get(key, "")
        new_hash = hashlib.md5(json.dumps(t, sort_keys=True).encode()).hexdigest()
        if new_hash != old_hash:
            _issues_cache[key] = new_hash
            new_tasks.append(t)
    
    _last_sync = datetime.datetime.now()
    return {
        "success": True,
        "total": len(tasks),
        "new_or_updated": len(new_tasks),
        "tasks": new_tasks[:10],  # 只返回前10条
        "last_sync": str(_last_sync),
    }

async def get_sync_status() -> dict:
    """获取同步状态"""
    return {
        "success": True,
        "last_sync": str(_last_sync) if _last_sync else "never",
        "cached_issues": len(_issues_cache),
        "gitea_url": GITEA_URL,
        "configured": bool(GITEA_TOKEN),
    }


class GiteaIssueSync(EnterpriseModule):
    """Gitea Issue同步模块"""
    def __init__(self): pass
    def execute(self, action: str = "", params: dict = None) -> dict:
        if action == "status": return get_sync_status()
        p = params or {}
        repo = p.get("repo", "owner/repo")
        if action in ("sync", "sync_issues"):
            import asyncio; loop = asyncio.new_event_loop()
            r = loop.run_until_complete(sync_gitea_issues(repo))
            loop.close(); return r
        return {"success": True, "status": "ready", "version": "0.1"}

module_class = GiteaIssueSync
