"""
Smithery CLI集成 — 一行命令安装7300+外部MCP服务器
"""
import os, json, logging, subprocess
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("smithery")
router = APIRouter(prefix="/api/v1/smithery", tags=["smithery"])

SMITHERY_REGISTRY = "https://registry.smithery.ai/servers"
_installed = []

class InstallReq(BaseModel):
    package: str
    client: str = "claude"

@router.get("/status")
def status():
    return {"success": True, "platform": "Smithery", "total_tools": "7300+", "installed": len(_installed), "tools": _installed}

@router.post("/install")
def install(req: InstallReq):
    try:
        result = subprocess.run(
            ["npx", "-y", "@smithery/cli@latest", "install", req.package, "--client", req.client],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            _installed.append(req.package)
            return {"success": True, "package": req.package}
        return {"success": False, "error": result.stderr[-300:]}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}

@router.post("/uninstall/{package}")
def uninstall(package: str):
    try:
        subprocess.run(["npx", "@smithery/cli@latest", "uninstall", package], capture_output=True, timeout=30)
        if package in _installed: _installed.remove(package)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}
