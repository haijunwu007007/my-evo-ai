"""
AUTO-EVO-AI V0.1 — JoyAI-VL-Interaction API 路由
京东开源实时视频视觉语言交互模型
"""
import logging
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("joyai_vl")
router = APIRouter(prefix="/api/v1/joyai-vl", tags=["joyai_vl"])

try:
    from modules.joyai_vl_interaction import JoyAIVLInteractionModule
    _module = JoyAIVLInteractionModule()
    _available = True
except Exception as e:
    _module = None
    _available = False
    logger.warning(f"JoyAI VL 加载失败: {e}")

class ActionRequest(BaseModel):
    action: str = "status"
    params: dict = {}

@router.get("/status")
def get_status():
    if _module: return _module.get_status()
    return {"success": False, "error": "模块未加载"}

@router.post("/execute")
def execute_action(req: ActionRequest):
    if not _module: return {"success": False, "error": "模块未加载"}
    return _module.execute(req.action, req.params)
