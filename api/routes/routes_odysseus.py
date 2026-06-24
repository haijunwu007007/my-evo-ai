"""AUTO-EVO-AI V0.1 — Odysseus Agent API"""
from fastapi import APIRouter; from modules.odysseus_agent import OdysseusAgent
router = APIRouter(prefix="/api/v1/odysseus", tags=["odysseus"])
_mod = OdysseusAgent()
@router.get("/status") def status(): return _mod.get_stats()
@router.post("/mission") def create_mission(goal: str = ""): return _mod.create_mission(goal)
@router.get("/mission/{mid}") def get_mission(mid: str): return _mod.get_progress(mid)
@router.post("/mission/{mid}/step") def step_mission(mid: str): return _mod.execute_step(mid)
@router.post("/mission/{mid}/pause") def pause_mission(mid: str): return _mod.pause(mid)
@router.post("/mission/{mid}/resume") def resume_mission(mid: str): return _mod.resume(mid)
@router.get("/stats") def stats(): return _mod.get_stats()
