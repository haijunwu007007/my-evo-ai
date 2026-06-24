import logging
from fastapi import APIRouter
logger = logging.getLogger("freqtrade_agent")
router = APIRouter(prefix="/api/v1/freqtrade-agent", tags=["freqtrade_agent"])
try:
    from modules.freqtrade_agent import FreqtradeModule
    _mod = FreqtradeModule()
    _avail = True
except Exception as e:
    _mod = None; _avail = False
    logger.warning(f"Freqtrade 加载失败: {e}")

@router.get("/status")
def get_status():
    if _mod: return _mod.get_status()
    return {"success": False, "error": "模块未加载"}
