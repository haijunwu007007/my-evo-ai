"""工作流编排 API"""

from fastapi import APIRouter
from modules.workflow_orchestrator import run_workflow, list_workflows, get_executions

router = APIRouter()

@router.get("/api/v1/workflows")
async def workflows_list():
    """列出所有工作流"""
    return {"success": True, "workflows": list_workflows()}

@router.post("/api/v1/workflow/run/{workflow_id}")
async def workflow_run(workflow_id: str):
    """运行指定工作流"""
    result = await run_workflow(workflow_id)
    return result

@router.get("/api/v1/workflow/executions")
async def workflow_executions():
    """获取执行历史"""
    return {"success": True, "executions": get_executions()}
