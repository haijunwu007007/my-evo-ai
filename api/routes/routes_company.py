"""虚拟公司 — API路由"""
from fastapi import APIRouter
import json
from core.logging_config import get_logger
from api.hub.company import get_status, assign_task, execute_tasks, get_stats

logger = get_logger("evo.api.company")
router = APIRouter(prefix="/api/v1/company")

@router.get("/status")
async def company_status():
    return {"success": True, **get_status()}

@router.get("/stats")
async def company_stats():
    return {"success": True, **get_stats()}

@router.post("/task")
async def company_task(data: dict):
    dept = data.get("department", "")
    task = data.get("task", "")
    return await assign_task(dept, task)

@router.post("/execute")
async def company_execute(data: dict = {}):
    dept = data.get("department", "")
    return await execute_tasks(dept)
