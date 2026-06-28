"""
AUTO-EVO-AI V0.1 — Docling Processor API 路由
"""
import logging
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("docling_processor")
router = APIRouter(prefix="/api/v1/docling-processor", tags=["docling_processor"])

try:
    from modules.docling_processor import ModuleImpl as DoclingProcessorModule
    _module = DoclingProcessorModule()
    _available = True
except Exception as e:
    _module = None
    _available = False
    logger.warning(f"Docling Processor 加载失败: {e}")

class ActionRequest(BaseModel):
    action: str = "status"
    params: dict = {}

@router.get("/status")
def get_status():
    if _module:
        return _module.get_status()
    return {"success": False, "error": "模块未加载"}

@router.post("/execute")
def execute_action(req: ActionRequest):
    if not _module:
        return {"success": False, "error": "模块未加载"}
    return _module.execute(req.action, req.params)
