"""
AUTO-EVO-AI V0.1 — Skill 标准化接口
标准化可执行能力单元：注册/发现/执行/管理
"""

r"""AUTO-EVO-AI Standardized Skill Interface."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
from core.logging_config import get_logger
import os, json, time, importlib, inspect, hashlib
from pathlib import Path

logger = get_logger(__name__)
router = APIRouter()

# ─── 数据模型 ──────────────────────────

class SkillDefinition(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = "auto-evo-ai"
    category: str = "通用"
    icon: str = "🔧"
    tags: list[str] = []
    input_schema: dict = {}
    output_schema: dict = {}
    handler: str = ""  # "module.function" or Python path
    endpoint: str = ""  # API endpoint if external

class SkillExecuteRequest(BaseModel):
    params: dict = {}
    context: Optional[dict] = {}

class SkillExecuteResponse(BaseModel):
    success: bool
    result: Any = None
    output: dict = {}
    execution_time: float = 0.0

# ─── 注册表 ──────────────────────────

_SKILL_REGISTRY: dict[str, SkillDefinition] = {}
_SKILL_HANDLERS: dict[str, callable] = {}
_SKILL_EXECUTION_LOG: list[dict] = []

def _load_builtin_skills():
    """从 skills/builtin/ 目录加载内置技能"""
    builtin_dir = Path(__file__).resolve().parent.parent / "skills" / "builtin"
    if not builtin_dir.exists():
        builtin_dir.mkdir(parents=True, exist_ok=True)
        return
    for f in sorted(builtin_dir.glob("*.py")):
        if f.name.startswith("_"):
            continue
        mod_name = f"skills.builtin.{f.stem}"
        try:
            mod = importlib.import_module(mod_name)
            if hasattr(mod, "skill_def"):
                sd = getattr(mod, "skill_def")
                if isinstance(sd, dict):
                    skill = SkillDefinition(**sd)
                    _SKILL_REGISTRY[skill.name] = skill
                    if hasattr(mod, "execute"):
                        _SKILL_HANDLERS[skill.name] = getattr(mod, "execute")
                        logger.info(f"  ✅ Skill loaded: {skill.name} v{skill.version} [{skill.category}]")
        except Exception as e:
            logger.warning(f"  ⚠️  Skill load failed: {f.name}: {e}")

    # 也从 skill 描述 json 加载
    for f in sorted(builtin_dir.glob("*.json")):
        try:
            data = json.load(open(f, encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    skill = SkillDefinition(**item)
                    _SKILL_REGISTRY[skill.name] = skill
            else:
                skill = SkillDefinition(**data)
                _SKILL_REGISTRY[skill.name] = skill
        except Exception as e:
            logger.warning(f"  ⚠️  Skill json load failed: {f.name}: {e}")

    # 自定义 skill 从 skills/custom/ 加载
    custom_dir = Path(__file__).resolve().parent.parent / "skills" / "custom"
    if custom_dir.exists():
        for f in sorted(custom_dir.glob("*.py")):
            if f.name.startswith("_"):
                continue
            mod_name = f"skills.custom.{f.stem}"
            try:
                mod = importlib.import_module(mod_name)
                if hasattr(mod, "skill_def"):
                    data = getattr(mod, "skill_def")
                    if isinstance(data, dict):
                        skill = SkillDefinition(**data)
                        _SKILL_REGISTRY[skill.name] = skill
                        if hasattr(mod, "execute"):
                            _SKILL_HANDLERS[skill.name] = getattr(mod, "execute")
            except Exception as e:
                logger.warning(f"  ⚠️  Custom skill load failed: {f.name}: {e}")

# 加载内置技能
_load_builtin_skills()


# ─── API 端点 ──────────────────────────

@router.get("/api/v1/skills")
async def list_skills(category: str = ""):
    """列出所有 Skill，可按分类过滤"""
    skills = list(_SKILL_REGISTRY.values())
    if category:
        skills = [s for s in skills if s.category == category]
    return {"success": True, "skills": [s.model_dump() for s in skills], "total": len(skills)}


@router.get("/api/v1/skills/search")
async def search_skills(q: str = ""):
    """搜索 Skill（按名称/描述/标签）"""
    if not q:
        return await list_skills()
    ql = q.lower()
    results = []
    for s in _SKILL_REGISTRY.values():
        if (ql in s.name.lower() or
            ql in s.description.lower() or
            any(ql in t.lower() for t in s.tags)):
            results.append(s)
    return {"success": True, "skills": [s.model_dump() for s in results], "total": len(results)}


@router.get("/api/v1/skills/{name}")
async def get_skill(name: str):
    """获取单个 Skill 详情"""
    if name not in _SKILL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")
    return {"success": True, "skill": _SKILL_REGISTRY[name].model_dump()}


@router.post("/api/v1/skills/register")
async def register_skill(skill: SkillDefinition):
    """注册自定义 Skill"""
    if skill.name in _SKILL_REGISTRY:
        return {"success": False, "detail": f"Skill already exists: {skill.name}"}
    _SKILL_REGISTRY[skill.name] = skill
    logger.info(f"  ✅ Skill registered: {skill.name} v{skill.version}")
    return {"success": True, "result": f"Skill registered: {skill.name} v{skill.version}"}


@router.post("/api/v1/skills/{name}/execute")
async def execute_skill(name: str, req: SkillExecuteRequest):
    """执行 Skill"""
    if name not in _SKILL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")

    skill = _SKILL_REGISTRY[name]
    start = time.time()

    try:
        # 有 Python handler 优先
        if name in _SKILL_HANDLERS:
            handler = _SKILL_HANDLERS[name]
            result = handler(req.params, req.context)
            elapsed = time.time() - start
            _log_execution(name, True, elapsed)
            return {"success": True, "result": result, "execution_time": round(elapsed, 3)}

        # 有 endpoint 则调用外部接口
        if skill.endpoint:
            import httpx
            with httpx.Client(timeout=30) as client:
                resp = client.post(skill.endpoint, json=req.params)
                elapsed = time.time() - start
                _log_execution(name, resp.is_success, elapsed)
                return {"success": resp.is_success, "result": resp.json(), "execution_time": round(elapsed, 3)}

        # 降级：返回 skill 描述（帮助模式）
        elapsed = time.time() - start
        return {"success": True, "result": {
            "message": f"Skill '{name}' 已就绪，但没有注册执行器。",
            "help": f"描述: {skill.description}",
            "input_schema": skill.input_schema
        }, "execution_time": round(elapsed, 3)}

    except Exception as e:
        elapsed = time.time() - start
        _log_execution(name, False, elapsed)
        return {"success": False, "detail": str(e), "execution_time": round(elapsed, 3)}


@router.get("/api/v1/skills/stats/log")
async def skill_execution_log(limit: int = 20):
    """获取最近 Skill 执行日志"""
    return {"success": True, "logs": _SKILL_EXECUTION_LOG[-limit:]}


def _log_execution(name: str, ok: bool, elapsed: float):
    _SKILL_EXECUTION_LOG.append({
        "skill": name,
        "success": ok,
        "time": round(time.time(), 3),
        "elapsed": round(elapsed, 3)
    })
    if len(_SKILL_EXECUTION_LOG) > 1000:
        _SKILL_EXECUTION_LOG[:] = _SKILL_EXECUTION_LOG[-500:]


def get_skill_by_name(name: str) -> Optional[SkillDefinition]:
    """供外部模块使用的查找方法"""
    return _SKILL_REGISTRY.get(name)


def execute_skill_internal(name: str, params: dict = None, context: dict = None) -> dict:
    """供外部模块（如 Workflow）直接调用的执行方法"""
    if name not in _SKILL_REGISTRY:
        return {"success": False, "detail": f"Unknown skill: {name}"}
    handler = _SKILL_HANDLERS.get(name)
    if not handler:
        return {"success": False, "detail": f"No handler for skill: {name}"}
    try:
        result = handler(params or {}, context or {})
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "detail": str(e)}
