# -*- coding: utf-8 -*-
from fastapi import APIRouter, Query
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..",".."))
from modules.desktop_agent import DesktopAgent

router = APIRouter(tags=["desktop"])
_agent = DesktopAgent()

@router.get("/api/v1/desktop/status")
async def get_status():
    try:
        return {"success": True, "cmds_allowed": _agent._allowed_cmds}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/v1/desktop/exec")
async def exec_cmd(cmd: str, cwd: str = ""):
    try:
        return {"success": True, "result": _agent.execute(cmd, cwd)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/v1/desktop/read")
async def read_file(path: str):
    try:
        return {"success": True, "result": _agent.read_file(path)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/v1/desktop/write")
async def write_file(path: str, content: str):
    try:
        return {"success": True, "result": _agent.write_file(path, content)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/v1/desktop/ls")
async def list_dir(path: str = "."):
    try:
        return {"success": True, "result": _agent.list_dir(path)}
    except Exception as e:
        return {"success": False, "error": str(e)}
