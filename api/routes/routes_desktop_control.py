"""桌面原生控制 — 本地文件/App操作API（借鉴 WorkBuddy）
通过服务端指令控制桌面：打开文件、执行命令、文件操作等。
注意：实际桌面控制需搭配本地客户端，此处提供服务端调度层。
"""
from fastapi import APIRouter
from pydantic import BaseModel
from core.logging_config import get_logger
import os, subprocess, json, platform
from pathlib import Path

logger = get_logger("evo.api.desktop_control")
router = APIRouter()

class DesktopAction(BaseModel):
    action: str  # open_file / run_cmd / list_dir / file_info
    target: str = ""

# 以下路由已由 routes_desktop.py 的完整桌面 API 接管
# @router.post("/api/v1/desktop/exec")
async def desktop_exec(req: DesktopAction):
    system = platform.system()
    if req.action == "list_dir":
        p = Path(req.target) if req.target else Path.home()
        if not p.exists(): return {"success": False, "error": "路径不存在"}
        items = []
        for f in p.iterdir():
            try:
                items.append({"name": f.name, "is_dir": f.is_dir(), "size": f.stat().st_size if f.is_file() else 0})
            except: pass
        return {"success": True, "path": str(p), "items": items[:50], "total": len(items)}
    elif req.action == "file_info":
        p = Path(req.target)
        if not p.exists(): return {"success": False, "error": "文件不存在"}
        s = p.stat()
        return {"success": True, "name": p.name, "size": s.st_size, "is_dir": p.is_dir(),
                "modified": s.st_mtime, "extension": p.suffix}
    elif req.action == "run_cmd":
        try:
            if system == "Windows":
                r = subprocess.run(["cmd", "/c", req.target], capture_output=True, text=True, timeout=15)
            else:
                r = subprocess.run(["bash", "-c", req.target], capture_output=True, text=True, timeout=15)
            return {"success": r.returncode == 0, "stdout": r.stdout[:2000], "stderr": r.stderr[:500], "code": r.returncode}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "命令超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    elif req.action == "open_file":
        try:
            if system == "Windows": os.startfile(req.target)
            elif system == "Darwin": subprocess.run(["open", req.target])
            else: subprocess.run(["xdg-open", req.target])
            return {"success": True, "message": f"已打开: {req.target}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    return {"success": False, "error": f"未知操作: {req.action}"}
