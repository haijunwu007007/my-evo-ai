# -*- coding: utf-8 -*-
from fastapi import APIRouter, Query
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..",".."))
from modules.desktop_agent import DesktopAgent

router = APIRouter(tags=["desktop"])
_agent = DesktopAgent()

@router.get("/api/v1/desktop/status")
async def get_status():
    return {"status": "ok", "cmds_allowed": _agent._allowed_cmds}

@router.post("/api/v1/desktop/exec")
async def exec_cmd(cmd: str, cwd: str = ""):
    return _agent.execute(cmd, cwd)

@router.post("/api/v1/desktop/read")
async def read_file(path: str):
    return _agent.read_file(path)

@router.post("/api/v1/desktop/write")
async def write_file(path: str, content: str):
    return _agent.write_file(path, content)

@router.post("/api/v1/desktop/ls")
async def list_dir(path: str = "."):
    return _agent.list_dir(path)
