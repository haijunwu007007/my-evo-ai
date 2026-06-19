# -*- coding: utf-8 -*-
from fastapi import APIRouter
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..",".."))
from modules.role_rbac import RoleRBAC

router = APIRouter(tags=["rbac"])
_rbac = None
def _get():
    global _rbac
    if _rbac is None:
        _rbac = RoleRBAC()
        _rbac.add_role("admin", ["*"], "管理员")
        _rbac.add_role("dev", ["read","write","deploy"], "开发者")
        _rbac.add_role("viewer", ["read"], "只读用户")
    return _rbac

@router.get("/api/v1/rbac/status")
async def get_status():
    return {"status": "ok", "roles": _get().get_roles()}

@router.post("/api/v1/rbac/check")
async def check_perm(username: str, permission: str):
    return _get().check(username, permission)

@router.post("/api/v1/rbac/assign")
async def assign_role(username: str, role: str):
    _get().assign(username, role)
    return {"ok": True}
