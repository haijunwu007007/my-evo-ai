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
