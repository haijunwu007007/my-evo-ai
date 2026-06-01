"""AUTO-EVO-AI V0.1 — Agent-S GUI Agent API Routes"""
from __future__ import annotations
import base64, json
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.logging_config import get_logger
from api.infra import registry

from modules.agent_s_bridge import (
    check_available, execute_instruction, get_screenshot,
    get_mouse_position as get_mouse, get_status
)

logger = get_logger("evo.api.agent-s")
router = APIRouter()


class ExecuteRequest(BaseModel):
    instruction: str = ""
    task: str = ""
    model: str = "gpt-4o"
    engine: str = "openai"
    timeout: int = 120


@router.get("/api/v1/agent-s/status")
@router.get("/api/v1/agent-s/available")
async def agent_s_status():
    """Agent-S 模块状态"""
    return await get_status()


@router.get("/api/v1/agent-s/check")
async def agent_s_check():
    """环境检测"""
    return await check_available()


@router.post("/api/v1/agent-s/execute")
async def agent_s_execute(req: ExecuteRequest):
    """执行GUI自动化指令"""
    instruction = req.instruction or req.task
    if not instruction:
        raise HTTPException(400, detail="请提供 instruction 或 task")
    try:
        result = await execute_instruction(
            instruction, model=req.model, engine_type=req.engine, timeout=req.timeout
        )
        return result
    except Exception as e:
        logger.error("[AgentS] 执行失败: %s", e)
        return {"success": False, "error": f"执行异常: {e}"}


@router.post("/api/v1/agent-s/screenshot")
async def agent_s_screenshot():
    """获取屏幕截图"""
    return await get_screenshot()


@router.get("/api/v1/agent-s/mouse")
async def agent_s_mouse():
    """获取鼠标位置"""
    return get_mouse()


@router.get("/api/v1/agent-s/history")
async def agent_s_history(limit: int = Query(20, ge=1, le=200)):
    """执行历史"""
    from modules.agent_s_bridge import _TASK_HISTORY
    return {"success": True, "history": _TASK_HISTORY[-limit:]}


# 注册到模块注册表
async def _register():
    if "agent_s_bridge" not in registry.modules:
        mod = __import__("modules.agent_s_bridge", fromlist=["agent_s_bridge"])
        registry.modules["agent_s_bridge"] = mod
        registry.health["agent_s_bridge"] = {
            "status": "ok", "grade": "A",
            "last_beat": datetime.now().isoformat(),
        }
        logger.info("[AgentS] 路由模块注册完成")
