import logging
from fastapi import APIRouter
logger = logging.getLogger("video_intelligence")
router = APIRouter(prefix="/api/v1/video-intelligence", tags=["video_intelligence"])
try:
    from modules.video_intelligence import VideoIntelligenceModule
    _mod = VideoIntelligenceModule()
    _avail = True
except Exception as e:
    _mod = None; _avail = False
    logger.warning(f"VideoIntelligence 加载失败: {e}")

@router.get("/status")
def get_status():
    if _mod: return _mod.get_status()
    return {"success": False, "error": "模块未加载"}
