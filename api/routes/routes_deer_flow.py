"""AUTO-EVO-AI V0.1 — Deer Flow API"""
from fastapi import APIRouter; from modules.deer_flow_engine import DeerFlowEngine
router = APIRouter(prefix="/api/v1/deer-flow", tags=["deer-flow"])
_mod = DeerFlowEngine()
@router.get("/status") def status(): return _mod.get_stats()
@router.post("/create") def create(name: str = ""): return _mod.create_flow(name)
@router.get("/list") def list_flows(): return _mod.list_flows()
@router.post("/{fid}/step") def step_flow(fid: str): return _mod.step_flow(fid)
@router.post("/{fid}/pause") def pause_flow(fid: str): return _mod.pause_flow(fid)
@router.post("/{fid}/resume") def resume_flow(fid: str): return _mod.resume_flow(fid)
