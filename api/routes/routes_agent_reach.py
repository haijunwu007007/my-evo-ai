"""Agent-Reach 集成路由 — 多平台互联网搜索"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import subprocess, json, os

router = APIRouter(tags=["agent_reach"])

def _run_reach(cmd: list[str]) -> dict:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return {"success": r.returncode == 0, "output": r.stdout[:2000], "error": r.stderr[:500]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/api/v1/agent-reach/status")
async def reach_status():
    r = subprocess.run(["which", "agent-reach"], capture_output=True, text=True, timeout=10)
    installed = r.returncode == 0
    return {"installed": installed, "path": r.stdout.strip() if installed else ""}

@router.get("/api/v1/agent-reach/search")
async def reach_search(platform: str = "web", query: str = ""):
    """搜索指定平台内容"""
    if not query:
        return {"success": False, "error": "需要 query 参数"}
    return _run_reach(["agent-reach", platform, query])

@router.get("/api/v1/agent-reach/read")
async def reach_read(url: str = ""):
    """读取网页内容"""
    if not url:
        return {"success": False, "error": "需要 url 参数"}
    return _run_reach(["agent-reach", "read", url])

@router.get("/api/v1/agent-reach/platforms")
async def reach_platforms():
    """列出支持的平台"""
    r = _run_reach(["agent-reach", "--help"])
    return r
