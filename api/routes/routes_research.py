"""AUTO-EVO-AI V0.1 — Auto Research API"""
from fastapi import APIRouter; from modules.auto_research_loop import AutoResearchLoop
router = APIRouter(prefix="/api/v1/research", tags=["research"])
_mod = AutoResearchLoop()
@router.get("/status")
def status(): return _mod.get_stats()
@router.post("/start")
def start_research(topic: str = "", depth: int = 3): return _mod.start_research(topic, depth)
@router.get("/{rid}")
def get_research(rid: str): return _mod.get_progress(rid)
@router.get("/{rid}/report")
def get_report(rid: str): return _mod.get_report(rid)
