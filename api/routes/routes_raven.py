"""RAVEN 集成路由 — 连接 RAVEN 自我进化智能体框架"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from core.logging_config import get_logger

logger = get_logger("evo.routes.raven")
router = APIRouter(tags=["raven"])

from api.agents.agent_raven import (
    is_installed, install, search_skills,
    full_cycle, auto_fix_all, get_status,
    apply_evolution, get_memory,
)


@router.get("/api/v1/raven/status")
async def raven_status():
    """RAVEN 集成状态"""
    return {"success": True, **get_status()}


@router.post("/api/v1/raven/install")
async def raven_install():
    """一键安装 RAVEN + EverOS"""
    result = install()
    return {"success": result.get("success", False), **result}


@router.get("/api/v1/raven/skills/search")
async def raven_search_skills(q: str = "", limit: int = 20):
    """搜索 RAVEN 的 10 万技能"""
    if not is_installed():
        return {"success": False, "error": "RAVEN 未安装", "skills": []}
    results = search_skills(q, limit)
    return {"success": True, "query": q, "skills": results, "count": len(results)}


@router.post("/api/v1/raven/evolve")
async def raven_evolve(target: str = "system"):
    """触发 RAVEN 自我进化"""
    result = apply_evolution(target)
    return {"success": True, **result}


@router.post("/api/v1/raven/full-cycle")
async def raven_full_cycle():
    """全栈自进化循环（RAVEN 优先 → 降级到本地）"""
    result = full_cycle()
    return {"success": True, **result}


@router.post("/api/v1/raven/fix")
async def raven_fix():
    """自动修复（RAVEN 修复引擎 → 降级到本地）"""
    result = auto_fix_all()
    return {"success": True, **result}


@router.get("/api/v1/raven/memory")
async def raven_memory(q: str = ""):
    """检索 RAVEN/EverOS 记忆"""
    result = get_memory(q)
    return {"success": True, **result}
