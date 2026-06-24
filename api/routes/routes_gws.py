"""
AUTO-EVO-AI V0.1 — Google Workspace CLI (gws) 桥接路由
通过 subprocess 调用 gws 命令行工具管理 Gmail/Drive/Calendar
"""
import logging, subprocess, json, shutil
from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger("routes_gws")
router = APIRouter(prefix="/api/v1/gws", tags=["gws"])

GWS_AVAILABLE = shutil.which("gws") is not None

@router.get("/status")
def gws_status():
    return {"success": True, "available": GWS_AVAILABLE, "tool": "gws"}

@router.get("/execute")
def gws_execute(cmd: str = Query("", description="gws 命令参数，如 'drive list --limit 5'")):
    if not GWS_AVAILABLE:
        return {"success": False, "error": "gws CLI not installed. Run: npm install -g @googleworkspace/cli"}
    try:
        result = subprocess.run(f"gws {cmd}", shell=True, capture_output=True, text=True, timeout=30)
        out = result.stdout[:2000]
        try:
            data = json.loads(out)
            return {"success": True, "result": data, "raw": out[:500]}
        except json.JSONDecodeError:
            return {"success": True, "result": out}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}

@router.get("/help")
def gws_help():
    if not GWS_AVAILABLE:
        return {"success": False, "error": "gws not installed"}
    try:
        r = subprocess.run("gws --help", shell=True, capture_output=True, text=True, timeout=10)
        return {"success": True, "help": r.stdout[:2000]}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}
