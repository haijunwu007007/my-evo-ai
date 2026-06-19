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


# ===== Merged from routes_browseract.py =====
"""BrowserAct 桥接路由 — 反爬浏览器自动化"""
import subprocess, json, shutil
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["tools"])

class BrowserActRequest(BaseModel):
    action: str  # open, click, input, extract, state, captcha, assist
    url: str = ""
    session: str = "default"
    index: int = 0
    text: str = ""

def _check_installed():
    return shutil.which("browser-act") is not None

@router.post("/api/v1/browseract/exec")
async def browseract_exec(req: BrowserActRequest):
    """执行 BrowserAct 命令"""
    if not _check_installed():
        return {"success": False, "error": "browser-act 未安装", "fix": "pip install browser-act-skills"}
    try:
        cmd = ["browser-act", "--session", req.session]
        if req.action == "open":
            cmd += ["browser", "open", req.url]
        elif req.action == "extract":
            cmd = ["browser-act", "stealth-extract", req.url]
        elif req.action == "state":
            cmd += ["state"]
        elif req.action == "click":
            cmd += ["click", str(req.index)]
        elif req.action == "input":
            cmd += ["input", str(req.index), req.text]
        elif req.action == "captcha":
            cmd += ["solve-captcha"]
        elif req.action == "assist":
            cmd += ["remote-assist"]
        else:
            return {"success": False, "error": f"未知动作: {req.action}"}
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return {"success": r.returncode == 0, "result": r.stdout[:2000], "error": r.stderr[:500]}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "执行超时(120s)"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/api/v1/browseract/status")
async def browseract_status():
    """检查 BrowserAct 安装状态"""
    return {"installed": _check_installed()}
