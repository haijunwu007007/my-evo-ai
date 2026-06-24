"""AUTO-EVO-AI V0.1 — Site Cloner API"""
from fastapi import APIRouter; from modules.site_cloner_pipeline import SiteClonerPipeline
router = APIRouter(prefix="/api/v1/cloner", tags=["cloner"])
_mod = SiteClonerPipeline()
@router.get("/status")
def status(): p = _mod.get_status(); return {"success": True, "available": True, "total_pipelines": p["total"]}
@router.post("/run")
def run_pipeline(spec: str = ""): return _mod.run_pipeline(spec)
@router.get("/pipeline/{pid}")
def get_pipeline(pid: str): return _mod.get_status(pid)
