"""AUTO-EVO-AI V0.1 — browser-use (93k⭐) API路由"""
from fastapi import APIRouter
from pydantic import BaseModel
router = APIRouter()
B = "/api/tools/browser-use"

class TaskRequest(BaseModel):
    task: str = ""
    instruction: str = ""
    headless: bool = True
    max_steps: int = 20

_mod = None
def _get():
    global _mod
    if _mod is None:
        import importlib, asyncio
        spec = importlib.util.spec_from_file_location("browser_use_mod", "modules/browser_use.py")
        _mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_mod)
    return _mod

@router.get(B)
async def status():
    m = _get()
    r = await m.execute("status")
    return {"success": True, "available": r.get("available", False), "installed": r.get("installed", False), "version": "0.12.6"}

@router.post(B + "/run")
async def run(req: TaskRequest):
    m = _get()
    task = req.task or req.instruction
    if not task:
        return {"success": False, "error": "task required"}
    r = await m.execute("execute", {"task": task, "headless": req.headless, "max_steps": req.max_steps})
    return r

@router.get(B + "/history")
async def history():
    m = _get()
    r = await m.execute("history")
    return {"success": True, "history": r.get("history", [])}
