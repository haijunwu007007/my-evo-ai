"""自进化 V2 API — 全栈自进化闭环外部接口"""
from fastapi import APIRouter
from pathlib import Path
from core.logging_config import get_logger

logger = get_logger("evo.api.evo_v2")
router = APIRouter()

BASE = Path(__file__).resolve().parent.parent.parent


@router.get("/api/v1/evo/status")
async def evo_v2_status():
    """自进化系统状态"""
    try:
        from api.agents.yoyo_evolve import get_status
        return {"success": True, **get_status()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/v1/evo/scan")
async def evo_v2_scan():
    """触发一次代码扫描"""
    try:
        from api.agents.yoyo_evolve import auto_scan
        result = auto_scan()
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/v1/evo/fix")
async def evo_v2_fix():
    """触发自动修复"""
    try:
        from api.agents.yoyo_evolve import auto_fix_all
        result = auto_fix_all()
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/v1/evo/full-cycle")
async def evo_v2_full_cycle():
    """全栈进化闭环：扫描→修复→发现"""
    try:
        from api.agents.yoyo_evolve import auto_evolve
        from api.agents.agent_memos import get_memory
        memos = None
        try: memos = get_memory()
        except: pass
        result = auto_evolve(memos=memos)
        return {"success": result.get("status") == "completed", **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/api/v1/evo/history")
async def evo_v2_history(limit: int = 20):
    """自进化历史"""
    try:
        from api.agents.yoyo_evolve import get_evolution_history
        return {"success": True, "history": get_evolution_history(limit)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/api/v1/evo/autofixes")
async def evo_v2_autofixes(limit: int = 20):
    """自动修复历史"""
    try:
        from api.agents.yoyo_evolve import get_autofix_history
        return {"success": True, "fixes": get_autofix_history(limit)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/v1/evo/discover-skills")
async def evo_v2_discover_skills():
    """触发技能自动发现"""
    try:
        from api.agents.yoyo_evolve import auto_discover_skills
        result = auto_discover_skills()
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}
