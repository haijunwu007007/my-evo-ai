# -*- coding: utf-8 -*-
from fastapi import APIRouter
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..",".."))
from modules.permission_sandbox import PermissionSandbox

router = APIRouter(tags=["permission"])
_sandbox = None

def _get():
    global _sandbox
    if _sandbox is None:
        _sandbox = PermissionSandbox()
        _sandbox.register_tool("file_write", 2, "写文件", "*")
        _sandbox.register_tool("file_delete", 2, "删文件", "*")
        _sandbox.register_tool("cmd_exec", 2, "命令执行", "*")
        _sandbox.register_tool("deploy", 1, "部署项目", "*")
        _sandbox.register_tool("chat_send", 0, "发送消息", "*")
    return _sandbox

@router.get("/api/v1/permission/status")
async def get_status():
    return {"status": "ok", "tools": 5, "levels": {"safe": 0, "ask": 1, "danger": 2}}

@router.post("/api/v1/permission/check")
async def check_tool(user: str, tool: str, action: str = "execute"):
    sb = _get()
    r = sb.check(user, tool)
    sb.log(user, tool, action, 1 if r["allowed"] else 0)
    return {"allowed": r["allowed"], "level": r["level"], "reason": r["reason"]}

@router.get("/api/v1/permission/audit")
async def get_audit(limit: int = 50):
    return {"logs": _get().get_audit_log(limit)}

# ===== RBAC（从 routes_rbac.py 合并） =====
from modules.role_rbac import RoleRBAC
_rbac = None
def _get_rbac():
    global _rbac
    if _rbac is None:
        _rbac = RoleRBAC()
        _rbac.add_role("admin", ["*"], "管理员")
        _rbac.add_role("dev", ["read","write","deploy"], "开发者")
        _rbac.add_role("viewer", ["read"], "只读用户")
    return _rbac

@router.get("/api/v1/rbac/status")
async def rbac_status():
    return {"status": "ok", "roles": _get_rbac().get_roles()}

@router.post("/api/v1/rbac/check")
async def rbac_check(username: str, permission: str):
    return _get_rbac().check(username, permission)

@router.post("/api/v1/rbac/assign")
async def rbac_assign(username: str, role: str):
    _get_rbac().assign(username, role)
    return {"ok": True}
