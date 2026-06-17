"""RBAC 权限系统 — admin/editor/viewer 三级"""
from functools import wraps
from fastapi import Request

ROLES = {
    "admin": {"priority": 100, "tools": "*"},
    "editor": {"priority": 50, "tools": ["code_review", "chart_create", "deep_research", "bi_report", "web_scrape", "generate_test", "fix_issue"]},
    "viewer": {"priority": 10, "tools": ["code_review", "chart_create", "web_search"]},
}

def get_user_role(request: Request) -> str:
    return getattr(request.state, "role", "viewer")

def check_tool_access(tool_name: str, role: str) -> bool:
    if role not in ROLES:
        return False
    role_config = ROLES[role]
    if role_config["tools"] == "*":
        return True
    return tool_name in role_config["tools"]

def require_role(min_role: str = "viewer"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if hasattr(arg, "state"):
                    request = arg
                    break
            if request:
                role = get_user_role(request)
                if ROLES.get(role, {}).get("priority", 0) < ROLES.get(min_role, {}).get("priority", 0):
                    from api._response import unauthorized
                    return unauthorized("权限不足，需要 " + min_role + " 角色")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
