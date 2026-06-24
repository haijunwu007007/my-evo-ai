"""AUTO-EVO-AI V0.1 — 全自动工作流路由"""
import logging
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("workflow")
router = APIRouter(prefix="/api/v1/workflow", tags=["workflow"])

try:
    from modules.workflow_engine import WorkflowEngine
    _engine = WorkflowEngine()
except Exception as e:
    _engine = None
    logger.warning(f"工作流引擎加载失败: {e}")

class RunRequest(BaseModel):
    workflow: str = ""
    text: str = ""
    inputs: dict = {}

@router.get("/status")
def get_status():
    if _engine: return _engine.get_status()
    return {"success": False, "error": "未加载"}

@router.get("/list")
def list_workflows():
    if _engine: return {"success": True, "workflows": _engine.list_workflows()}
    return {"success": False}

@router.post("/run")
def run_workflow(req: RunRequest):
    if not _engine: return {"success": False, "error": "未加载"}
    return _engine.run_workflow(req.workflow, req.inputs)

@router.post("/auto")
def auto_trigger(req: RunRequest):
    if not _engine: return {"success": False, "error": "未加载"}
    return _engine.execute("auto", {"text": req.text or req.workflow, "inputs": req.inputs})
