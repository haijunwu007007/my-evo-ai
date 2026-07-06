"""任务编排路由 — 将用户需求分解为可执行步骤"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger("evo.api.task_orchestrate")
router = APIRouter()


class TaskReq(BaseModel):
    task: str
    context: Optional[dict] = None


@router.post("/api/v1/task/orchestrate")
async def orchestrate_task(req: TaskReq):
    """解析用户任务并拆解为步骤（前端兜底用，实际由 /api/v1/smart 的 agent 分支处理）"""
    msg = (req.task or "").strip()
    if not msg:
        return {"success": False, "error": "empty_task", "message": "任务不能为空"}

    # 返回 success=false 让前端自动降级到 /api/v1/smart
    logger.info(f"[ORCHESTRATE] fallback to smart: {msg[:60]}")
    return {"success": False, "detail": "已转交智能引擎处理"}
