import logging
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("astro_site")
router = APIRouter(prefix="/api/v1/astro-site", tags=["astro_site"])

try:
    from modules.astro_site import ModuleImpl as AstroSite
    _mod = AstroSite()
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