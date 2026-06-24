import logging
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("temporal_workflow")
router = APIRouter(prefix="/api/v1/temporal-workflow", tags=["temporal_workflow"])

try:
    from modules.temporal_workflow import TemporalWorkflow
    _mod = TemporalWorkflow()
except Exception as e:
    _mod = None
    logger.error(str(e))

class Req(BaseModel):
    action: str = "status"
    params: dict = {}

@router.get("/status")
def status():
    if _mod:
        return _mod.get_status()
    return {"success": False, "error": "unavailable"}

@router.post("/execute")
def execute(req: Req):
    if not _mod:
        return {"success": False, "error": "unavailable"}
    return _mod.execute(req.action, req.params)