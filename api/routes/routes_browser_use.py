"""AUTO-EVO-AI V0.1 — browser-use (93k⭐) API路由"""
from fastapi import APIRouter
from pydantic import BaseModel
router = APIRouter()
B = "/api/v1/tools/browser-use"

class TaskRequest(BaseModel):
    task: str = ""
    instruction: str = ""
    headless: bool = True
    max_steps: int = 20

_AVAILABLE = None

def _check():
    global _AVAILABLE
    if _AVAILABLE is not None:
        return _AVAILABLE
    try:
        import browser_use
        _AVAILABLE = True
    except ImportError:
        _AVAILABLE = False
    return _AVAILABLE

@router.get(B)
async def status():
    ok = _check()
    return {"success": True, "available": ok, "name": "browser-use (93k⭐) AI浏览器自动化", "version": "0.12.6"}

@router.post(B + "/run")
async def run(req: TaskRequest):
    if not _check():
        return {"success": False, "error": "browser-use not installed"}
    task = req.task or req.instruction
    if not task:
        return {"success": False, "error": "task required"}
    try:
        from browser_use import Agent
        import os
        os.environ["ANONYMIZED_TELEMETRY"] = "false"
        agent = Agent(task=task, headless=req.headless, max_steps=req.max_steps)
        result = await agent.run()
        return {"success": True, "result": result[:2000] if result else "done"}
    except Exception as e:
        return {"success": False, "error": str(e)[:500]}

@router.get(B + "/history")
async def history():
    return {"success": True, "history": []}
