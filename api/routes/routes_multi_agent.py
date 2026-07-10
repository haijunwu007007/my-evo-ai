import logging
logger = logging.getLogger("evo.routes_multi_agent")
# -*- coding: utf-8 -*-
from fastapi import APIRouter
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..",".."))
from modules.multi_agent_coord import MultiAgentCoordinator

router = APIRouter(tags=["multi-agent"])
_coord = None
def _get():
    global _coord
    if _coord is None: _coord = MultiAgentCoordinator()
    return _coord

@router.get("/api/v1/multi-agent/status")
async def get_status():
    try:
        return {"success": True, "teams": 0, "roles": ["planner","coder","reviewer","operator","analyst","researcher"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/v1/multi-agent/team")
async def create_team(team_id: str, name: str, members: list):
    try:
        return {"success": True, "result": _get().create_team(team_id, name, members)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/v1/multi-agent/run")
async def run_session(team_id: str, task: str):
    try:
        return {"success": True, "result": _get().run_session(team_id, task)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/api/v1/multi-agent/sessions")
async def get_sessions(limit: int = 10):
    try:
        return {"success": True, "sessions": _get().get_sessions(limit)}
    except Exception as e:
        return {"success": False, "error": str(e)}
