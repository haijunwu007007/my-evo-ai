import logging
from fastapi import APIRouter
logger = logging.getLogger("home_assistant")
router = APIRouter(prefix="/api/v1/home-assistant", tags=["home_assistant"])
try:
    from modules.home_assistant import HomeAssistantModule
    _mod = HomeAssistantModule()
    _avail = True
except Exception as e:
    _mod = None; _avail = False
    logger.warning(f"HomeAssistant 加载失败: {e}")

@router.get("/status")
def get_status():
    if _mod: return _mod.get_status()
    return {"success": False, "error": "模块未加载"}
