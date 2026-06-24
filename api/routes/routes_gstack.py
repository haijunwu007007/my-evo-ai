"""AUTO-EVO-AI V0.1 — GStack Team API"""
from fastapi import APIRouter; from modules.gstack_team import GStackTeam
router = APIRouter(prefix="/api/v1/gstack", tags=["gstack"])
_mod = GStackTeam()
@router.get("/status") def status(): s = _mod.get_team_status(); return {"success": True, **s}
@router.get("/team") def team(): return _mod.get_team_status()
@router.post("/task") def assign_task(task: str = ""): return _mod.assign_task(task)
@router.get("/report") def report(cid: str = ""): return _mod.get_cycle_report(cid)
