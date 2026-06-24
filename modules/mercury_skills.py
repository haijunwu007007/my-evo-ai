"""
AUTO-EVO-AI V0.1 — Mercury Skill系统模块
集成自 Cosmic Stack Labs 的 Mercury Agent 设计：
- 40+ 权限加固工具
- Skill 系统管理
- Token 预算控制
- 多渠道访问
"""

import time
import json
import hashlib
import logging
from typing import Any
from datetime import datetime

logger = logging.getLogger("mercury_skills")

__module_meta__ = {
    "id": "mercury-skills",
    "name": "Mercury Skill 系统",
    "version": "V0.1",
    "group": "agent",
    "grade": "A",
    "description": "Mercury风格Skill系统：权限加固、Token预算、Skill管理、多渠道访问控制",
}

# Skill 注册表
_skill_registry = {}
_permission_cache = {}
_token_budgets = {}
_ACCESS_LEVELS = {"public": 0, "user": 1, "power": 2, "admin": 3, "system": 4}


class MercurySkill:
    """Mercury风格Skill定义"""
    def __init__(self, name: str, description: str, handler: callable = None,
                 min_access_level: str = "user", token_cost: int = 10,
                 requires_confirmation: bool = False):
        self.id = hashlib.md5(f"{name}:{time.time_ns()}".encode()).hexdigest()[:8]
        self.name = name
        self.description = description
        self.handler = handler
        self.min_access_level = min_access_level
        self.token_cost = token_cost
        self.requires_confirmation = requires_confirmation
        self.created_at = datetime.now().isoformat()
        self.call_count = 0
        self.last_called = None


def register_skill(name: str, description: str, handler: callable = None,
                   min_access_level: str = "user", token_cost: int = 10,
                   requires_confirmation: bool = False) -> dict:
    """注册一个Skill到系统"""
    if name in _skill_registry:
        return {"success": False, "error": f"Skill '{name}' 已存在"}
    skill = MercurySkill(name, description, handler, min_access_level, token_cost, requires_confirmation)
    _skill_registry[name] = skill
    return {"success": True, "skill_id": skill.id, "name": name}

def get_skill(name: str) -> dict:
    """获取Skill详情"""
    skill = _skill_registry.get(name)
    if not skill:
        return {"success": False, "error": f"Skill '{name}' 不存在"}
    return {
        "success": True, "id": skill.id, "name": skill.name,
        "description": skill.description,
        "min_access_level": skill.min_access_level,
        "token_cost": skill.token_cost,
        "requires_confirmation": skill.requires_confirmation,
        "call_count": skill.call_count,
    }

def list_skills(access_level: str = "user") -> list[dict]:
    """列出用户可用的Skills（按权限过滤）"""
    user_level = _ACCESS_LEVELS.get(access_level, 1)
    result = []
    for name, skill in sorted(_skill_registry.items()):
        if _ACCESS_LEVELS.get(skill.min_access_level, 1) <= user_level:
            result.append(get_skill(name))
    return result

def execute_skill(name: str, params: dict = None, access_level: str = "user",
                  token_budget: int = None) -> dict:
    """执行Skill：权限检查 + Token预算 + 执行"""
    if params is None:
        params = {}
    skill = _skill_registry.get(name)
    if not skill:
        return {"success": False, "error": f"Skill '{name}' 不存在"}

    # 权限检查
    user_level = _ACCESS_LEVELS.get(access_level, 1)
    required_level = _ACCESS_LEVELS.get(skill.min_access_level, 1)
    if user_level < required_level:
        return {"success": False, "error": f"权限不足：需要 {skill.min_access_level}, 当前 {access_level}"}

    # Token预算检查
    if token_budget is not None and token_budget < skill.token_cost:
        return {"success": False, "error": f"Token预算不足：需要 {skill.token_cost}, 剩余 {token_budget}"}

    # 需要确认
    if skill.requires_confirmation:
        return {"success": False, "requires_confirmation": True, "skill": name,
                "message": f"执行 '{name}' 需要确认：{skill.description}"}

    # 执行
    try:
        if skill.handler:
            result = skill.handler(params)
        else:
            # 模拟执行（用于占位Skill）
            result = {"status": "executed", "params": params}
        skill.call_count += 1
        skill.last_called = datetime.now().isoformat()
        return {"success": True, "name": name, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

def set_token_budget(user_id: str, budget: int) -> dict:
    """设置用户Token预算"""
    _token_budgets[user_id] = {"budget": budget, "used": 0, "reset_at": datetime.now().isoformat()}
    return {"success": True}

def get_token_usage(user_id: str) -> dict:
    """查询Token使用情况"""
    info = _token_budgets.get(user_id, {"budget": 1000, "used": 0})
    return {
        "success": True, "user_id": user_id,
        "budget": info["budget"], "used": info["used"],
        "remaining": info["budget"] - info["used"],
    }


# 默认Skill注册
_default_skills = [
    ("file_search", "搜索文件系统中的文件", None, "user", 5),
    ("code_analyze", "分析代码结构质量", None, "user", 15),
    ("web_search", "搜索互联网信息", None, "power", 10),
    ("data_query", "查询系统数据库", None, "power", 20),
    ("system_execute", "执行系统命令（需确认）", None, "admin", 50),
    ("config_edit", "修改系统配置（需确认）", None, "admin", 30),
    ("user_manage", "管理用户账号", None, "system", 40),
]

for name, desc, handler, level, cost in _default_skills:
    register_skill(name, desc, handler, level, cost)


def get_status() -> dict:
    return {
        "success": True,
        "module": "Mercury Skill System",
        "skills_count": len(_skill_registry),
        "active_budgets": len(_token_budgets),
        "default_skills": [s[0] for s in _default_skills],
    }


async def execute(action: str = "status", params: dict = None) -> dict:
    if params is None:
        params = {}
    handlers = {
        "status": lambda p: get_status(),
        "register": lambda p: register_skill(p.get("name", ""), p.get("description", ""),
                                              None, p.get("min_access_level", "user"),
                                              p.get("token_cost", 10)),
        "get": lambda p: get_skill(p.get("name", "")),
        "list": lambda p: {"skills": list_skills(p.get("access_level", "user"))},
        "execute": lambda p: execute_skill(p.get("name", ""), p.get("params"),
                                           p.get("access_level", "user"),
                                           p.get("token_budget")),
        "set_budget": lambda p: set_token_budget(p.get("user_id", ""), p.get("budget", 1000)),
        "get_usage": lambda p: get_token_usage(p.get("user_id", "")),
    }
    handler = handlers.get(action)
    if handler:
        try:
            return handler(params)
        except Exception as e:
            return {"success": False, "error": str(e)}
    return get_status()

module_class = type("MercurySkillsModule", (), {"execute": staticmethod(execute), "get_status": staticmethod(get_status)})
